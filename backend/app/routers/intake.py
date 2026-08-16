from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Optional
import uuid
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.email_accounts import EmailAccountModel
from app.models.processed_email import ProcessedEmailModel
from app.schemas.intake import (
    AssessJobRequest,
    ConfirmAssessmentRequest,
    DirectEmailIntakeRequest,
    EmailPayload,
    IntakeResultResponse,
    PasteIntakeRequest,
)
from app.schemas.llm import JobAssessmentResult
from app.services.email_fetcher import fetch_emails_from_account
from app.services.file_parser import parse_uploaded_file
from app.services.intake import (
    process_email_batch_sequential,
    process_single_email_graph,
)
from app.services.llm import assess_job_posting
from app.services.scraper import scrape_job_url
from app.services.task_tracker import task_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["Intake"])


@router.get("/extension-config")
async def get_extension_config(request: Request):
    """Programmatically returns the exact exposed backend endpoint URL for browser extensions."""
    if settings.PUBLIC_API_URL:
        base_url = settings.PUBLIC_API_URL.rstrip("/")
    else:
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        forwarded_host = (
            request.headers.get("x-forwarded-host")
            or request.headers.get("host")
            or f"{request.url.hostname}:{request.url.port}"
        )
        base_url = f"{forwarded_proto}://{forwarded_host}"

    return {
        "url_endpoint": f"{base_url}/api/v1/intake/url",
        "jd_endpoint": f"{base_url}/api/v1/intake/jd",
        "extension_ingest_url": f"{base_url}/api/v1/intake/assess-job",
        "api_base_url": f"{base_url}/api/v1",
    }


class ExtensionUrlDirectPayload(BaseModel):
    type: Optional[str] = "URL_DIRECT_SEND"
    url: str
    title: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("/url", status_code=status.HTTP_200_OK)
async def intake_extension_url(
    payload: ExtensionUrlDirectPayload,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Receives URL directly from browser extension send-url button and triggers AI assessment with fallback to Staging."""
    try:
        assess_req = AssessJobRequest(url=payload.url, text=payload.title)
        return await assess_job_lead(assess_req, db=db)
    except Exception as err:
        logger.warning(
            "Direct extension URL scrape failed for %s: %s. Routing to staging queue.",
            payload.url,
            err,
        )
        from app.models.staging import StagingItemModel

        staging_item = StagingItemModel(
            email_subject=payload.title or f"Extension URL Lead: {payload.url[:60]}",
            email_raw_body=f"URL: {payload.url}\nTitle: {payload.title or 'N/A'}",
            extracted_data={"job_url": payload.url, "title": payload.title},
            match_score=0.0,
            match_reason="SCRAPE_FAILED",
            status="PENDING",
        )
        db.add(staging_item)
        await db.commit()
        await db.refresh(staging_item)
        return {
            "status": "staged",
            "staging_item_id": staging_item.id,
            "message": f"Automated scrape was protected or unavailable for '{payload.url}'. Saved to Staging Queue for review.",
            "url": payload.url,
        }


@router.post("/jd", response_model=JobAssessmentResult, status_code=status.HTTP_200_OK)
async def intake_extension_jd_elements(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> JobAssessmentResult:
    """
    Receives selected DOM elements / group cards from browser extension,
    extracts all text/html recursively, and triggers AI assessment.
    """
    from app.routers.extension import _extract_text_from_html

    def _extract_all_text(data: Any) -> list[str]:
        snippets = []
        if isinstance(data, dict):
            if data.get("title") and data.get("title") != "New Group":
                snippets.append(str(data["title"]))
            if data.get("text"):
                snippets.append(str(data["text"]))
            if data.get("html"):
                snippets.append(_extract_text_from_html(str(data["html"])))
            if data.get("children") and isinstance(data["children"], list):
                for child in data["children"]:
                    snippets.extend(_extract_all_text(child))
            if data.get("payload"):
                snippets.extend(_extract_all_text(data["payload"]))
        elif isinstance(data, list):
            for item in data:
                snippets.extend(_extract_all_text(item))
        elif isinstance(data, str):
            snippets.append(data)
        return snippets

    extracted_lines = _extract_all_text(payload)
    combined_text = "\n".join(
        [line.strip() for line in extracted_lines if line.strip()]
    )

    if not combined_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text or HTML content found in the extension selection payload.",
        )

    assess_req = AssessJobRequest(text=combined_text)
    return await assess_job_lead(assess_req, db=db)


# Built-in job-signal keywords always applied as a subject/body pre-filter before any LLM call.
# User-supplied keywords in SyncFolderRequest.keyword_filter are merged on top of these.
BUILT_IN_JOB_KEYWORDS: list[str] = [
    "application",
    "interview",
    "offer",
    "position",
    "role",
    "recruiter",
    "hiring",
    "rejected",
    "opportunity",
    "assessment",
    "screening",
    "shortlisted",
    "candidate",
    "apply",
    "applied",
    "job",
    "vacancy",
    "invitation",
    "congratulations",
]


class SyncFolderRequest(BaseModel):
    account_id: int = Field(
        description="ID of the configured EmailAccountModel to sync"
    )
    folder: Optional[str] = Field(default=None)
    since_date: Optional[datetime] = Field(default=None)
    keyword_filter: list[str] = Field(
        default_factory=list,
        description="Extra keywords merged with built-in job keywords for subject/body pre-filter. "
        "An email must match at least one keyword to be sent to the AI pipeline.",
    )


class TaskResponse(BaseModel):
    task_id: str
    message: str
    scanned_count: int = 0
    matched_count: int = 0
    skipped_duplicates: int = 0
    filtered_out_count: int = 0


def _format_graph_result(result: dict[str, Any]) -> IntakeResultResponse:
    if result.get("is_duplicate"):
        return IntakeResultResponse(
            status="skipped",
            route="skip",
            is_duplicate=True,
            message="Email was already ingested previously (duplicate skipped).",
        )
    if result.get("staging_item_id"):
        return IntakeResultResponse(
            status="staged",
            route="staging",
            is_application=False,
            company=result.get("company_name"),
            position=result.get("position_name"),
            staging_item_id=result.get("staging_item_id"),
            extracted_data=result.get("extracted_data"),
            message="Email routed to human-in-the-loop staging queue for review.",
        )
    if result.get("is_application"):
        return IntakeResultResponse(
            status="success",
            route="commit",
            is_application=True,
            company=result.get("company_name"),
            position=result.get("position_name"),
            application_id=result.get("application_id"),
            event_id=result.get("event_id"),
            extracted_data=result.get("extracted_data"),
            message="Job application and timeline event committed successfully.",
        )
    return IntakeResultResponse(
        status="success",
        route="other_event",
        is_application=False,
        event_id=result.get("event_id"),
        extracted_data=result.get("extracted_data"),
        message="Non-application email event logged successfully.",
    )


@router.post(
    "/paste", response_model=IntakeResultResponse, status_code=status.HTTP_200_OK
)
async def intake_pasted_text(
    payload: PasteIntakeRequest,
    db: AsyncSession = Depends(get_db),
) -> IntakeResultResponse:
    """Ingests raw pasted email text, thread, or job communication directly."""
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pasted text content cannot be empty.",
        )

    # Derive subject from first non-empty line if not provided
    subject = payload.subject
    if not subject:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        subject = lines[0][:100] if lines else "Pasted Job Update"

    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    msg_id = payload.message_id or f"paste-{content_hash}"
    conv_id = payload.conversation_id or f"conv-{content_hash}"
    received_at = payload.received_at or datetime.now(timezone.utc)

    email_payload = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=received_at,
        subject=subject,
        body=raw_text,
    )

    task_id = str(uuid.uuid4())
    result = await process_single_email_graph(db, email_payload, task_id)
    return _format_graph_result(result)


@router.post(
    "/upload", response_model=list[IntakeResultResponse], status_code=status.HTTP_200_OK
)
async def intake_uploaded_files(
    files: list[UploadFile] = File(
        ..., description="Uploaded .eml, .msg, or .txt files"
    ),
    db: AsyncSession = Depends(get_db),
) -> list[IntakeResultResponse]:
    """Ingests drag-and-drop uploaded email files (.eml, .msg, .txt)."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload.",
        )

    results: list[IntakeResultResponse] = []

    for file in files:
        filename = file.filename or "uploaded_file.txt"
        try:
            content = await file.read()
            if not content:
                continue

            email_payload = parse_uploaded_file(filename, content)
            task_id = str(uuid.uuid4())
            graph_res = await process_single_email_graph(db, email_payload, task_id)
            results.append(_format_graph_result(graph_res))
        except Exception as err:
            logger.error(
                "Failed processing uploaded file '%s': %s", filename, err, exc_info=True
            )
            results.append(
                IntakeResultResponse(
                    status="error",
                    route="error",
                    message=f"Failed to parse file '{filename}': {str(err)}",
                )
            )

    return results


@router.post(
    "/assess-job", response_model=JobAssessmentResult, status_code=status.HTTP_200_OK
)
async def assess_job_lead(
    payload: AssessJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobAssessmentResult:
    """Pre-screens a job lead (via URL or pasted JD text) using AI assessment."""
    content = payload.text
    if not content and payload.raw_html:
        from app.routers.extension import _extract_text_from_html

        content = _extract_text_from_html(payload.raw_html)

    if not content and payload.url:
        scraped = await scrape_job_url(payload.url)
        if scraped.text:
            content = scraped.text

    if not content or not content.strip():
        if payload.url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SCRAPE_FAILED: Unable to automatically extract job details from this URL (protected or dynamic portal). Please paste the job description text.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid job description text, raw HTML DOM, or reachable URL.",
        )

    # 1. Fetch candidate's active CV skills if available
    from app.models.candidate_profile import CandidateCVModel
    from app.services.matcher import compute_programmatic_skill_match

    cv_stmt = select(CandidateCVModel).limit(1)
    cv_res = await db.execute(cv_stmt)
    active_cv = cv_res.scalars().first()

    candidate_skills = active_cv.extracted_skills if active_cv else []
    match_info = compute_programmatic_skill_match(candidate_skills, content)

    active_domains_str = None
    if active_cv and active_cv.domain_experience:
        active_list = [
            f"{item['domain']} ({item['years']} yrs)"
            for item in active_cv.domain_experience
            if item.get("is_active", True)
        ]
        if active_list:
            active_domains_str = ", ".join(active_list)
    elif active_cv and active_cv.domain_expertise:
        active_domains_str = ", ".join(active_cv.domain_expertise)

    assessment = await assess_job_posting(
        db,
        content,
        candidate_skills=candidate_skills,
        candidate_cv=active_cv.anonymized_text or active_cv.raw_text
        if active_cv
        else None,
        candidate_domain_breakdown=active_domains_str,
        programmatic_baseline=match_info.get("programmatic_score", 0),
    )

    # Automatically persist to database or stage if duplicate
    from app.services.job_saver import persist_or_stage_job_assessment

    await persist_or_stage_job_assessment(
        db=db,
        assessment=assessment,
        raw_text=content,
        job_url=payload.url,
        force_new=False,
        target_status="ASSESSMENT",
    )

    return assessment


@router.post(
    "/confirm-assessment",
    response_model=IntakeResultResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_job_assessment(
    payload: ConfirmAssessmentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IntakeResultResponse:
    """Commits an assessed job lead to the application pipeline in ASSESSMENT or APPLIED status."""
    comp_norm = payload.company.strip().lower()
    position_norm = payload.position.strip().lower()
    now = datetime.now(timezone.utc)

    # 1. Company
    stmt = select(CompanyModel).where(CompanyModel.name_normalized == comp_norm)
    res = await db.execute(stmt)
    company = res.scalar_one_or_none()

    if not company:
        company = CompanyModel(name=payload.company.strip(), name_normalized=comp_norm)
        db.add(company)
        await db.flush()

    # 2. Application resolution
    app_record = None
    if payload.application_id:
        app_record = await db.get(ApplicationModel, payload.application_id)

    if not app_record and not payload.force_new:
        app_stmt = select(ApplicationModel).where(
            ApplicationModel.company_id == company.id,
            ApplicationModel.position_normalized == position_norm,
        )
        app_res = await db.execute(app_stmt)
        app_record = app_res.scalar_one_or_none()

    if not app_record:
        app_record = ApplicationModel(
            company_id=company.id,
            position=payload.position.strip(),
            position_normalized=position_norm,
            status=payload.status or "ASSESSMENT",
            job_url=payload.job_url,
            application_date=now,
            last_activity_at=now,
        )
        db.add(app_record)
        await db.flush()
    else:
        if payload.status:
            app_record.status = payload.status
        if payload.job_url and not app_record.job_url:
            app_record.job_url = payload.job_url
        app_record.last_activity_at = now

    # 3. Job Posting Record
    jp_stmt = select(JobPostingModel).where(
        JobPostingModel.application_id == app_record.id
    )
    jp_res = await db.execute(jp_stmt)
    job_posting = jp_res.scalar_one_or_none()

    if not job_posting:
        job_posting = JobPostingModel(
            application_id=app_record.id,
            job_url=payload.job_url or f"lead-{uuid.uuid4().hex[:8]}",
            description_markdown=payload.description_markdown,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
            currency=payload.currency or "USD",
            location=payload.location,
            work_model=payload.work_model,
            required_skills=payload.required_skills or [],
        )
        db.add(job_posting)
    else:
        if payload.description_markdown:
            job_posting.description_markdown = payload.description_markdown
        if payload.salary_min is not None:
            job_posting.salary_min = payload.salary_min
        if payload.salary_max is not None:
            job_posting.salary_max = payload.salary_max
        if payload.location:
            job_posting.location = payload.location
        if payload.work_model:
            job_posting.work_model = payload.work_model
        if payload.required_skills:
            job_posting.required_skills = payload.required_skills

    # 4. Initial/Update Event
    event = ApplicationEventModel(
        email_application_id=app_record.id,
        email_conversation_id=f"lead-conv-{app_record.id}",
        email_event_type="PRE_APPLICATION_ASSESSMENT",
        email_status_after_event=app_record.status,
        email_summary=f"Pre-application AI assessment recorded for {payload.position} at {payload.company}.",
        email_received_at=now,
        source_channel="INTAKE",
        email_raw_body=payload.description_markdown,
    )
    db.add(event)
    await db.commit()
    await db.refresh(app_record)
    await db.refresh(event)

    # 5. Generate Vector Embedding in isolated background task (Deferred if still in ASSESSMENT stage)
    if app_record.status != "ASSESSMENT":
        from app.services.llm import async_enqueue_application_embedding

        background_tasks.add_task(
            async_enqueue_application_embedding, app_record.id, skip_llm_summary=True
        )

    return IntakeResultResponse(
        status="success",
        route="commit",
        is_application=True,
        company=company.name,
        position=app_record.position,
        application_id=app_record.id,
        event_id=event.id,
        message=f"Job lead saved to pipeline under status '{app_record.status}'.",
    )


@router.post(
    "/sync-account", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED
)
async def sync_email_account(
    payload: SyncFolderRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Triggers asynchronous email sync for a date window with keyword pre-filtering.

    Pipeline (all pre-LLM):
    1. Fetch emails from provider filtered by folder + since_date.
    2. Skip any message_id already in processed_email_ids (unified dedup table).
    3. Keyword pre-filter: reject emails whose subject+body[0:500] contain none of
       BUILT_IN_JOB_KEYWORDS + payload.keyword_filter.  Write filtered_out record.
    4. Dispatch the surviving emails to process_email_batch_sequential (background).
    """
    stmt = select(EmailAccountModel).where(EmailAccountModel.id == payload.account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account ID {payload.account_id} not found.",
        )

    # --- Step 1: Fetch from provider ---
    raw_emails, next_cursor = await fetch_emails_from_account(
        account, since_date=payload.since_date
    )
    scanned_count = len(raw_emails)
    logger.info(
        "sync_email_account: account_id=%s fetched %d emails from provider",
        payload.account_id,
        scanned_count,
    )

    if next_cursor:
        account.sync_cursor = next_cursor
        account.last_synced_at = datetime.now(timezone.utc)
        await db.commit()

    if scanned_count == 0:
        task_id = task_tracker.create_task(
            total_emails=0, account_id=payload.account_id
        )
        task_tracker.complete_task(task_id)
        return TaskResponse(
            task_id=task_id,
            message="No new emails found to process.",
            scanned_count=0,
        )

    # --- Step 2 + 3: Unified dedup + keyword pre-filter ---
    all_keywords = BUILT_IN_JOB_KEYWORDS + [
        kw.strip().lower() for kw in payload.keyword_filter if kw.strip()
    ]
    skipped_duplicates = 0
    filtered_out_count = 0
    to_process: list = []

    # Batch deduplication query
    mids = [email.message_id for email in raw_emails if email.message_id]
    existing_mids = set()
    if mids:
        existing_rows = await db.execute(
            select(ProcessedEmailModel.message_id).where(
                ProcessedEmailModel.message_id.in_(mids)
            )
        )
        existing_mids = set(existing_rows.scalars().all())

    for email in raw_emails:
        mid = email.message_id

        # Dedup: skip any message_id already seen (any status)
        if mid and mid in existing_mids:
            skipped_duplicates += 1
            logger.debug("sync dedup skip: message_id=%s", mid)
            continue

        # Keyword pre-filter: check subject + first 500 chars of body
        haystack = f"{email.subject or ''} {(email.body or '')[:500]}".lower()
        if not any(kw in haystack for kw in all_keywords):
            filtered_out_count += 1
            logger.debug(
                "sync keyword filter: message_id=%s subject=%r skipped (no job keyword match)",
                mid,
                email.subject,
            )
            # Persist filtered_out so this ID is never re-evaluated
            if mid:
                try:
                    db.add(
                        ProcessedEmailModel(
                            message_id=mid,
                            account_id=payload.account_id,
                            status="filtered_out",
                            subject=(email.subject or "")[:500],
                        )
                    )
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.warning(
                        "Failed to persist filtered_out record for message_id=%s", mid
                    )
            continue

        to_process.append(email)

    matched_count = len(to_process)
    logger.info(
        "sync_email_account: account_id=%s scanned=%d duplicates=%d filtered_out=%d to_process=%d",
        payload.account_id,
        scanned_count,
        skipped_duplicates,
        filtered_out_count,
        matched_count,
    )

    task_id = task_tracker.create_task(
        total_emails=matched_count, account_id=payload.account_id
    )

    if matched_count == 0:
        task_tracker.complete_task(task_id)
        return TaskResponse(
            task_id=task_id,
            message="All emails were already processed or did not match job keywords.",
            scanned_count=scanned_count,
            matched_count=0,
            skipped_duplicates=skipped_duplicates,
            filtered_out_count=filtered_out_count,
        )

    # --- Step 4: Background processing ---
    background_tasks.add_task(
        process_email_batch_sequential,
        db=db,
        emails=to_process,
        task_id=task_id,
    )

    return TaskResponse(
        task_id=task_id,
        message=(
            f"Sync started: {matched_count} email(s) queued for AI extraction. "
            f"{skipped_duplicates} duplicate(s) skipped, {filtered_out_count} filtered out. "
            f"Track progress: GET /api/v1/intake/tasks/{task_id}"
        ),
        scanned_count=scanned_count,
        matched_count=matched_count,
        skipped_duplicates=skipped_duplicates,
        filtered_out_count=filtered_out_count,
    )


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Retrieves live progress for an ongoing or completed email intake task."""
    task_info = task_tracker.get_task(task_id)
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found.",
        )
    return task_info


@router.post("/test-direct", status_code=status.HTTP_200_OK)
async def intake_direct_raw_email(
    payload: DirectEmailIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Directly ingests a raw email payload for immediate testing."""
    now = datetime.now(timezone.utc)
    conv_id = payload.conversation_id or f"test-conv-{uuid.uuid4().hex[:8]}"
    msg_id = payload.message_id or f"test-msg-{uuid.uuid4().hex[:8]}"
    received_at = payload.received_at or now

    email_item = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=received_at,
        subject=payload.subject,
        body=payload.body,
    )

    task_id = task_tracker.create_task(total_emails=1)

    await process_email_batch_sequential(
        db=db,
        emails=[email_item],
        task_id=task_id,
    )

    task_summary = task_tracker.get_task(task_id)

    return {
        "status": "success",
        "message": "Direct email processed successfully.",
        "task_id": task_id,
        "details": task_summary,
    }


# =========================================================================
# ASYNC INTAKE EVALUATION QUEUE & PERSISTENCE ENDPOINTS
# =========================================================================

from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.intake import EnqueueAssessmentRequest, IntakeEvaluationTaskResponse
from app.services.evaluation_worker import process_evaluation_task


@router.post(
    "/enqueue-assessment",
    response_model=IntakeEvaluationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_job_assessment(
    payload: EnqueueAssessmentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IntakeEvaluationTaskResponse:
    """
    Enqueues a job lead evaluation task into PostgreSQL for continuous intake UX.
    The background worker executes the 4-stage pipeline respecting provider concurrency limits.
    """
    url_clean = payload.url.strip() if payload.url else None
    text_clean = payload.text.strip() if payload.text else None

    if not url_clean and not text_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid job URL or job description text.",
        )

    # Derive title hint from payload
    if payload.title_hint:
        title_hint = payload.title_hint.strip()
    elif url_clean:
        title_hint = f"Lead: {url_clean.split('/')[-1] or url_clean[:50]}"
    else:
        first_line = text_clean.splitlines()[0] if text_clean else "Job Lead"
        title_hint = first_line[:50]

    task_record = IntakeEvaluationTaskModel(
        job_url=url_clean,
        raw_text=text_clean,
        title_hint=title_hint,
        status="QUEUED",
        stage="FETCHING",
    )
    db.add(task_record)
    await db.commit()
    await db.refresh(task_record)

    # Hand off to background worker
    background_tasks.add_task(process_evaluation_task, task_id=task_record.id)

    return task_record


@router.get(
    "/evaluations",
    response_model=list[IntakeEvaluationTaskResponse],
    status_code=status.HTTP_200_OK,
)
async def list_evaluation_tasks(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[IntakeEvaluationTaskResponse]:
    """Retrieves all queued, processing, and recent evaluation tasks from PostgreSQL."""
    stmt = (
        select(IntakeEvaluationTaskModel)
        .order_by(IntakeEvaluationTaskModel.id.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.delete("/evaluations/{task_id}", status_code=status.HTTP_200_OK)
async def delete_evaluation_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancels an ongoing evaluation or dismisses a completed/failed evaluation task."""
    task = await db.get(IntakeEvaluationTaskModel, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation task {task_id} not found.",
        )

    await db.delete(task)
    await db.commit()
    return {"status": "success", "message": f"Evaluation task {task_id} deleted."}


@router.post("/evaluations/clear-completed", status_code=status.HTTP_200_OK)
async def clear_completed_evaluations(
    db: AsyncSession = Depends(get_db),
):
    """Clears all completed or failed evaluation tasks from the queue history."""
    from sqlalchemy import delete

    stmt = delete(IntakeEvaluationTaskModel).where(
        IntakeEvaluationTaskModel.status.in_(["COMPLETED", "FAILED", "CANCELLED"])
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"status": "success", "cleared_count": result.rowcount}


@router.post(
    "/evaluations/{task_id}/retry",
    response_model=IntakeEvaluationTaskResponse,
    status_code=status.HTTP_200_OK,
)
async def retry_evaluation_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IntakeEvaluationTaskResponse:
    """
    Retries a failed or cancelled evaluation task by resetting its state
    and re-dispatching to the background worker.
    """
    task = await db.get(IntakeEvaluationTaskModel, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation task {task_id} not found.",
        )

    task.status = "QUEUED"
    task.stage = "FETCHING" if task.task_type != "CV_EXTRACTION" else "SCRUBBING"
    task.error_message = None
    task.result_json = None
    task.completed_at = None
    task.created_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(process_evaluation_task, task_id=task.id)
    return task
