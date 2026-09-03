import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.url_utils import normalize_job_url
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    JobPostingModel,
)
from app.schemas.extension import ClipJobRequest, ClipUrlRequest, ExtensionClipResponse
from app.schemas.intake import EmailPayload
from app.services.company_resolver import resolve_or_create_company
from app.services.intake import process_single_email_graph
from app.services.llm import generate_and_save_application_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension", tags=["Browser Extension"])


def _extract_text_from_html(html_content: str) -> str:
    """Strips HTML tags, removes scripts/styles/nav/forms, and cleans visible text content."""
    if not html_content or not html_content.strip():
        return ""

    from bs4 import BeautifulSoup

    from app.services.scraper import clean_extracted_text

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "header",
            "iframe",
            "form",
            "aside",
            "template",
            "canvas",
        ]
    ):
        tag.decompose()

    for el in soup.find_all(
        class_=re.compile(
            r"wpcf7|cookie|consent|navbar|site-header|site-footer|menu",
            re.IGNORECASE,
        )
    ):
        el.decompose()

    main_el = soup.find(
        ["main", "article", "div"],
        class_=re.compile(r"job|posting|description|detail", re.IGNORECASE),
    )
    raw_text = (
        main_el.get_text(separator="\n")
        if main_el and len(main_el.get_text(strip=True)) > 150
        else soup.get_text(separator="\n")
    )
    return clean_extracted_text(raw_text)


@router.post(
    "/clip-url", response_model=ExtensionClipResponse, status_code=status.HTTP_200_OK
)
async def clip_job_url(
    payload: ClipUrlRequest,
    db: AsyncSession = Depends(get_db),
) -> ExtensionClipResponse:
    """
    Receives a job posting URL, scrapes page text (or uses pre-captured HTML),
    and routes through the LangGraph extraction and ingestion pipeline.
    """
    clean_url = normalize_job_url(payload.url) or payload.url
    page_text = ""

    if payload.raw_html:
        page_text = _extract_text_from_html(payload.raw_html)
    else:
        from app.services.scraper import scrape_job_url

        scraped = await scrape_job_url(clean_url)
        page_text = scraped.text or f"Job Posting URL: {clean_url}"

    if not page_text:
        page_text = f"Job URL: {clean_url}\nNotes: {payload.notes or ''}"

    content_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]
    msg_id = f"ext-url-{content_hash}"
    conv_id = f"conv-ext-{content_hash}"

    email_payload = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=datetime.now(UTC),
        subject=f"Job Clip: {clean_url}",
        body=page_text[:15000],  # Guard token length
    )

    # For ad-hoc extension submissions, generate a simple uuid task_id
    task_id = str(uuid.uuid4())

    graph_res = await process_single_email_graph(db, email_payload, task_id)

    if graph_res.get("staging_item_id"):
        return ExtensionClipResponse(
            status="staged",
            staging_item_id=graph_res.get("staging_item_id"),
            company=graph_res.get("company_name"),
            position=graph_res.get("position_name"),
            message="Job posting clipped and routed to staging queue for confirmation.",
            details=graph_res.get("extracted_data"),
        )

    return ExtensionClipResponse(
        status="success",
        application_id=graph_res.get("application_id"),
        company=graph_res.get("company_name"),
        position=graph_res.get("position_name"),
        event_id=graph_res.get("event_id"),
        message="Job posting clipped and application recorded successfully.",
        details=graph_res.get("extracted_data"),
    )


@router.post(
    "/clip-job", response_model=ExtensionClipResponse, status_code=status.HTTP_200_OK
)
async def clip_job_pre_extracted(
    payload: ClipJobRequest,
    db: AsyncSession = Depends(get_db),
) -> ExtensionClipResponse:
    """
    Directly accepts pre-extracted DOM metadata (company, title, description, url)
    from active browser tab and creates or updates application records.
    """
    position_norm = payload.position.strip().lower()
    clean_url = normalize_job_url(payload.url)

    # Find or create Company
    company, _ = await resolve_or_create_company(
        db=db,
        company_name=payload.company,
    )

    # Find or create Application
    app_stmt = select(ApplicationModel).where(
        ApplicationModel.company_id == company.id,
        ApplicationModel.position_normalized == position_norm,
    )
    app_res = await db.execute(app_stmt)
    application = app_res.scalar_one_or_none()

    now = datetime.now(UTC)
    if not application:
        application = ApplicationModel(
            company_id=company.id,
            position=payload.position.strip(),
            position_normalized=position_norm,
            external_job_id=payload.external_job_id,
            job_url=clean_url,
            status=payload.status or "APPLIED",
        )
        db.add(application)
        await db.flush()
    else:
        if payload.status:
            application.status = payload.status
        if clean_url and not application.job_url:
            application.job_url = clean_url

    # Upsert Job Posting
    jp_stmt = select(JobPostingModel).where(
        JobPostingModel.application_id == application.id
    )
    jp_res = await db.execute(jp_stmt)
    job_posting = jp_res.scalar_one_or_none()

    if not job_posting:
        job_posting = JobPostingModel(
            application_id=application.id,
            job_url=clean_url or f"clip-{application.id}",
            description_markdown=payload.description,
            location=payload.location,
            work_model=payload.work_model if hasattr(payload, "work_model") else None,
        )
        db.add(job_posting)
    else:
        if payload.description:
            job_posting.description_markdown = payload.description
        if payload.location:
            job_posting.location = payload.location

    # Create timeline event
    conv_id = f"ext-clip-{uuid.uuid4().hex[:12]}"
    summary_text = (
        f"Clipped job posting from browser: {payload.position} at {payload.company}."
    )
    if payload.location:
        summary_text += f" Location: {payload.location}."
    if payload.salary:
        summary_text += f" Salary: {payload.salary}."

    event = ApplicationEventModel(
        email_application_id=application.id,
        email_message_id=f"msg-{uuid.uuid4().hex[:12]}",
        email_conversation_id=conv_id,
        email_received_at=now,
        email_event_type="BROWSER_EXTENSION_CLIP",
        email_subject=f"Captured Job: {payload.position} at {payload.company}",
        email_summary=summary_text,
        email_action_required=False,
        email_raw_body=payload.description or summary_text,
    )
    db.add(event)
    await db.commit()
    await db.refresh(application)
    await db.refresh(event)

    # Synthesize embedding
    try:
        await generate_and_save_application_embedding(db, application.id)
    except Exception as err:
        logger.warning(
            "Embedding deferred for clipped application %s: %s", application.id, err
        )

    return ExtensionClipResponse(
        status="success",
        application_id=application.id,
        company=company.name,
        position=application.position,
        event_id=event.id,
        message="Job posting successfully captured and linked to application.",
        details={
            "company": company.name,
            "position": application.position,
            "status": application.status,
            "job_url": application.job_url,
        },
    )
