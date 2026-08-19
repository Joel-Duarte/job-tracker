import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.email_accounts import EmailAccountModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.processed_email import ProcessedEmailModel
from app.schemas.intake import (
    AssessJobRequest,
    BulkTaskActionRequest,
    BulkTaskActionResult,
    ConfirmAssessmentRequest,
    DirectEmailIntakeRequest,
    EmailPayload,
    EnqueueAssessmentRequest,
    IntakeResultResponse,
    PasteIntakeRequest,
)
from app.schemas.llm import JobAssessmentResult
from app.services.domain_resolver import resolve_company_domain
from app.services.email_fetcher import fetch_emails_from_account
from app.services.evaluation_worker import process_evaluation_task
from app.services.file_parser import parse_uploaded_file
from app.services.intake import (
    process_email_batch_sequential,
    process_single_email_graph,
)
from app.services.job_saver import persist_or_stage_job_assessment
from app.services.llm import assess_job_posting, extract_job_spec
from app.services.matcher import compute_programmatic_skill_match
from app.services.scraper import scrape_job_url
from app.services.task_tracker import task_tracker
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)

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


class IntakeService:
    """Service class encapsulating intake operations, DB persistence, and workflow orchestration."""

    @staticmethod
    async def intake_extension_url(
        url: str,
        title: str | None,
        db: AsyncSession,
    ) -> Any:
        try:
            assess_req = AssessJobRequest(url=url, text=title)
            return await IntakeService.assess_job_lead(assess_req, db=db)
        except Exception as err:
            logger.warning(
                "Direct extension URL scrape failed for %s: %s. Routing to staging queue.",
                url,
                err,
            )
            from app.models.staging import StagingItemModel

            staging_item = StagingItemModel(
                email_subject=title or f"Extension URL Lead: {url[:60]}",
                email_raw_body=f"URL: {url}\nTitle: {title or 'N/A'}",
                extracted_data={"job_url": url, "title": title},
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
                "message": f"Automated scrape was protected or unavailable for '{url}'. Saved to Staging Queue for review.",
                "url": url,
            }

    @staticmethod
    async def intake_pasted_text(
        payload: PasteIntakeRequest,
        db: AsyncSession,
    ) -> IntakeResultResponse:
        raw_text = payload.text.strip()
        if not raw_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pasted text content cannot be empty.",
            )

        subject = payload.subject
        if not subject:
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            subject = lines[0][:100] if lines else "Pasted Job Update"

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
        msg_id = payload.message_id or f"paste-{content_hash}"
        conv_id = payload.conversation_id or f"conv-{content_hash}"
        received_at = payload.received_at or datetime.now(UTC)

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

    @staticmethod
    async def intake_uploaded_files(
        files: list[UploadFile],
        db: AsyncSession,
    ) -> list[IntakeResultResponse]:
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
                    "Failed processing uploaded file '%s': %s",
                    filename,
                    err,
                    exc_info=True,
                )
                results.append(
                    IntakeResultResponse(
                        status="error",
                        route="error",
                        message=f"Failed to parse file '{filename}': {err!s}",
                    )
                )

        return results

    @staticmethod
    async def assess_job_lead(
        payload: AssessJobRequest,
        db: AsyncSession,
    ) -> JobAssessmentResult:
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

        spec_dict = None
        try:
            extracted_spec_obj = await extract_job_spec(db, content)
            spec_dict = extracted_spec_obj.model_dump() if extracted_spec_obj else None
        except Exception as spec_err:
            logger.warning("Optional job spec extraction skipped/failed: %s", spec_err)

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

        await persist_or_stage_job_assessment(
            db=db,
            assessment=assessment,
            raw_text=content,
            job_url=payload.url,
            force_new=False,
            target_status="ASSESSMENT",
            structured_spec=spec_dict,
        )

        return assessment

    @staticmethod
    async def confirm_job_assessment(
        payload: ConfirmAssessmentRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> IntakeResultResponse:
        comp_norm = payload.company.strip().lower()
        position_norm = payload.position.strip().lower()
        now = datetime.now(UTC)

        resolved_domain = await resolve_company_domain(
            company_name=payload.company.strip(),
            source_url=payload.job_url,
        )
        stmt = select(CompanyModel).where(CompanyModel.name_normalized == comp_norm)
        res = await db.execute(stmt)
        company = res.scalar_one_or_none()

        if not company:
            company = CompanyModel(
                name=payload.company.strip(),
                name_normalized=comp_norm,
                domain=resolved_domain,
            )
            db.add(company)
            await db.flush()
        elif not company.domain and resolved_domain:
            company.domain = resolved_domain
            await db.flush()

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
                match_analysis_payload=payload.match_analysis_payload,
            )
            db.add(app_record)
            await db.flush()
        else:
            if payload.status:
                app_record.status = payload.status
            if payload.job_url and not app_record.job_url:
                app_record.job_url = payload.job_url
            app_record.last_activity_at = now
            if payload.match_analysis_payload:
                app_record.match_analysis_payload = payload.match_analysis_payload

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
                structured_spec=payload.structured_spec
                if hasattr(payload, "structured_spec")
                else None,
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
            if hasattr(payload, "structured_spec") and payload.structured_spec:
                job_posting.structured_spec = payload.structured_spec

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

        if app_record.status != "ASSESSMENT":
            from app.services.llm import async_enqueue_application_embedding

            background_tasks.add_task(
                async_enqueue_application_embedding,
                app_record.id,
                skip_llm_summary=True,
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

    @staticmethod
    async def sync_email_account(
        account_id: int,
        folder: str | None,
        since_date: datetime | None,
        keyword_filter: list[str],
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ):
        stmt = select(EmailAccountModel).where(EmailAccountModel.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email account ID {account_id} not found.",
            )

        raw_emails, next_cursor = await fetch_emails_from_account(
            account, since_date=since_date
        )
        scanned_count = len(raw_emails)

        if next_cursor:
            account.sync_cursor = next_cursor
            account.last_synced_at = datetime.now(UTC)
            await db.commit()

        if scanned_count == 0:
            task_id = task_tracker.create_task(total_emails=0, account_id=account_id)
            task_tracker.complete_task(task_id)
            return {
                "task_id": task_id,
                "message": "No new emails found to process.",
                "scanned_count": 0,
                "matched_count": 0,
                "skipped_duplicates": 0,
                "filtered_out_count": 0,
            }

        all_keywords = BUILT_IN_JOB_KEYWORDS + [
            kw.strip().lower() for kw in keyword_filter if kw.strip()
        ]
        skipped_duplicates = 0
        filtered_out_count = 0
        to_process: list = []

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

            if mid and mid in existing_mids:
                skipped_duplicates += 1
                continue

            haystack = f"{email.subject or ''} {(email.body or '')[:500]}".lower()
            if not any(kw in haystack for kw in all_keywords):
                filtered_out_count += 1
                if mid:
                    try:
                        db.add(
                            ProcessedEmailModel(
                                message_id=mid,
                                account_id=account_id,
                                status="filtered_out",
                                subject=(email.subject or "")[:500],
                            )
                        )
                        await db.commit()
                    except Exception:
                        await db.rollback()
                continue

            to_process.append(email)

        matched_count = len(to_process)
        task_id = task_tracker.create_task(
            total_emails=matched_count, account_id=account_id
        )

        if matched_count == 0:
            task_tracker.complete_task(task_id)
            return {
                "task_id": task_id,
                "message": "All emails were already processed or did not match job keywords.",
                "scanned_count": scanned_count,
                "matched_count": 0,
                "skipped_duplicates": skipped_duplicates,
                "filtered_out_count": filtered_out_count,
            }

        background_tasks.add_task(
            process_email_batch_sequential,
            db=db,
            emails=to_process,
            task_id=task_id,
        )

        return {
            "task_id": task_id,
            "message": (
                f"Sync started: {matched_count} email(s) queued for AI extraction. "
                f"{skipped_duplicates} duplicate(s) skipped, {filtered_out_count} filtered out. "
                f"Track progress: GET /api/v1/intake/tasks/{task_id}"
            ),
            "scanned_count": scanned_count,
            "matched_count": matched_count,
            "skipped_duplicates": skipped_duplicates,
            "filtered_out_count": filtered_out_count,
        }

    @staticmethod
    async def intake_direct_raw_email(
        payload: DirectEmailIntakeRequest,
        db: AsyncSession,
    ):
        now = datetime.now(UTC)
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

    @staticmethod
    async def enqueue_job_assessment(
        payload: EnqueueAssessmentRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> IntakeEvaluationTaskModel:
        url_clean = payload.url.strip() if payload.url else None
        text_clean = payload.text.strip() if payload.text else None

        if not url_clean and not text_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide a valid job URL or job description text.",
            )

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

        background_tasks.add_task(process_evaluation_task, task_id=task_record.id)

        return task_record

    @staticmethod
    async def list_evaluation_tasks(
        db: AsyncSession,
        limit: int = 50,
    ) -> list[IntakeEvaluationTaskModel]:
        stmt = (
            select(IntakeEvaluationTaskModel)
            .order_by(IntakeEvaluationTaskModel.id.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def delete_evaluation_task(
        task_id: int,
        db: AsyncSession,
    ):
        task = await db.get(IntakeEvaluationTaskModel, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evaluation task {task_id} not found.",
            )

        await db.delete(task)
        await db.commit()
        return {"status": "success", "message": f"Evaluation task {task_id} deleted."}

    @staticmethod
    async def clear_completed_evaluations(
        db: AsyncSession,
    ):
        stmt = delete(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.status.in_(["COMPLETED", "FAILED", "CANCELLED"])
        )
        result = await db.execute(stmt)
        await db.commit()
        return {"status": "success", "cleared_count": result.rowcount}

    @staticmethod
    async def retry_evaluation_task(
        task_id: int,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> IntakeEvaluationTaskModel:
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
        task.created_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(task)

        background_tasks.add_task(process_evaluation_task, task_id=task.id)
        return task

    @staticmethod
    async def bulk_retry_evaluation_tasks(
        payload: BulkTaskActionRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession,
    ) -> BulkTaskActionResult:
        async with trace_operation(
            "worker",
            "bulk_retry_evaluation_tasks",
            inputs={"task_ids": payload.task_ids},
            db=db,
        ) as ctx:
            parsed_ids = []
            for tid in payload.task_ids:
                try:
                    parsed_ids.append(int(tid))
                except (ValueError, TypeError):
                    pass

            if not parsed_ids:
                return BulkTaskActionResult(
                    affected_count=0,
                    skipped_count=len(payload.task_ids),
                    unhandled_ids=payload.task_ids,
                )

            stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.id.in_(parsed_ids)
            )
            res = await db.execute(stmt)
            found_tasks = {t.id: t for t in res.scalars().all()}

            retried_tasks = []
            unhandled_ids = []
            skipped_count = 0

            for raw_id in payload.task_ids:
                try:
                    int_id = int(raw_id)
                    task = found_tasks.get(int_id)
                except (ValueError, TypeError):
                    task = None

                if not task:
                    unhandled_ids.append(raw_id)
                    skipped_count += 1
                    continue

                if task.status not in ["FAILED", "CANCELLED"]:
                    skipped_count += 1
                    continue

                task.status = "QUEUED"
                task.stage = (
                    "FETCHING" if task.task_type != "CV_EXTRACTION" else "SCRUBBING"
                )
                task.error_message = None
                task.result_json = None
                task.completed_at = None
                task.created_at = datetime.now(UTC)

                retried_tasks.append(task)
                background_tasks.add_task(process_evaluation_task, task_id=task.id)

            await db.commit()
            for task in retried_tasks:
                await db.refresh(task)

            result = BulkTaskActionResult(
                affected_count=len(retried_tasks),
                skipped_count=skipped_count,
                unhandled_ids=unhandled_ids,
                updated_tasks=retried_tasks,
            )
            ctx["outputs"] = {
                "affected_count": result.affected_count,
                "skipped_count": result.skipped_count,
            }
            return result

    @staticmethod
    async def bulk_delete_evaluation_tasks(
        payload: BulkTaskActionRequest,
        db: AsyncSession,
    ) -> BulkTaskActionResult:
        async with trace_operation(
            "worker",
            "bulk_delete_evaluation_tasks",
            inputs={"task_ids": payload.task_ids},
            db=db,
        ) as ctx:
            parsed_ids = []
            for tid in payload.task_ids:
                try:
                    parsed_ids.append(int(tid))
                except (ValueError, TypeError):
                    pass

            if not parsed_ids:
                return BulkTaskActionResult(
                    deleted_count=0,
                    skipped_count=len(payload.task_ids),
                    unhandled_ids=payload.task_ids,
                )

            stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.id.in_(parsed_ids)
            )
            res = await db.execute(stmt)
            found_tasks = {t.id: t for t in res.scalars().all()}

            deleted_count = 0
            skipped_count = 0
            unhandled_ids = []

            for raw_id in payload.task_ids:
                try:
                    int_id = int(raw_id)
                    task = found_tasks.get(int_id)
                except (ValueError, TypeError):
                    task = None

                if not task:
                    unhandled_ids.append(raw_id)
                    skipped_count += 1
                    continue

                if task.status in ["PROCESSING", "IN_PROGRESS"]:
                    unhandled_ids.append(raw_id)
                    skipped_count += 1
                    continue

                await db.delete(task)
                deleted_count += 1

            await db.commit()

            result = BulkTaskActionResult(
                deleted_count=deleted_count,
                skipped_count=skipped_count,
                unhandled_ids=unhandled_ids,
            )
            ctx["outputs"] = {
                "deleted_count": result.deleted_count,
                "skipped_count": result.skipped_count,
            }
            return result
