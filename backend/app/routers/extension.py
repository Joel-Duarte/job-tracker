from datetime import datetime, timezone
import hashlib
import logging
import re
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.applications import ApplicationEventModel, ApplicationModel, CompanyModel
from app.schemas.extension import ClipJobRequest, ClipUrlRequest, ExtensionClipResponse
from app.schemas.intake import EmailPayload
from app.services.intake import process_single_email_graph
from app.services.llm import generate_and_save_application_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension", tags=["Browser Extension"])


def _extract_text_from_html(html_content: str) -> str:
    """Strips HTML tags and extracts visible text content."""
    # Remove script and style elements
    cleaned = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", html_content, flags=re.IGNORECASE)
    # Replace block tags with newlines
    cleaned = re.sub(r"<(p|div|br|h[1-6]|li|tr)[^>]*>", "\n", cleaned, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Normalize whitespace
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)


@router.post("/clip-url", response_model=ExtensionClipResponse, status_code=status.HTTP_200_OK)
async def clip_job_url(
    payload: ClipUrlRequest,
    db: AsyncSession = Depends(get_db),
) -> ExtensionClipResponse:
    """
    Receives a job posting URL, scrapes page text (or uses pre-captured HTML),
    and routes through the LangGraph extraction and ingestion pipeline.
    """
    page_text = ""

    if payload.raw_html:
        page_text = _extract_text_from_html(payload.raw_html)
    else:
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as client:
                resp = await client.get(payload.url)
                if resp.status_code == 200:
                    page_text = _extract_text_from_html(resp.text)
        except Exception as err:
            logger.warning("Static fetch failed for '%s': %s", payload.url, err)
            page_text = f"Job Posting URL: {payload.url}"

    if not page_text:
        page_text = f"Job URL: {payload.url}\nNotes: {payload.notes or ''}"

    content_hash = hashlib.sha256(payload.url.encode("utf-8")).hexdigest()[:16]
    msg_id = f"ext-url-{content_hash}"
    conv_id = f"conv-ext-{content_hash}"

    email_payload = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=datetime.now(timezone.utc),
        subject=f"Job Clip: {payload.url}",
        body=page_text[:15000],  # Guard token length
    )

    graph_res = await process_single_email_graph(db, email_payload)

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


@router.post("/clip-job", response_model=ExtensionClipResponse, status_code=status.HTTP_200_OK)
async def clip_job_pre_extracted(
    payload: ClipJobRequest,
    db: AsyncSession = Depends(get_db),
) -> ExtensionClipResponse:
    """
    Directly accepts pre-extracted DOM metadata (company, title, description, url)
    from active browser tab and creates or updates application records.
    """
    company_norm = payload.company.strip().lower()
    position_norm = payload.position.strip().lower()

    # Find or create Company
    comp_stmt = select(CompanyModel).where(CompanyModel.name_normalized == company_norm)
    comp_res = await db.execute(comp_stmt)
    company = comp_res.scalar_one_or_none()

    if not company:
        company = CompanyModel(
            name=payload.company.strip(),
            name_normalized=company_norm,
        )
        db.add(company)
        await db.flush()

    # Find or create Application
    app_stmt = select(ApplicationModel).where(
        ApplicationModel.company_id == company.id,
        ApplicationModel.position_normalized == position_norm,
    )
    app_res = await db.execute(app_stmt)
    application = app_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not application:
        application = ApplicationModel(
            company_id=company.id,
            position=payload.position.strip(),
            position_normalized=position_norm,
            external_job_id=payload.external_job_id,
            job_url=payload.url,
            status=payload.status or "APPLIED",
        )
        db.add(application)
        await db.flush()
    else:
        if payload.status:
            application.status = payload.status
        if payload.url and not application.job_url:
            application.job_url = payload.url

    # Create timeline event
    conv_id = f"ext-clip-{uuid.uuid4().hex[:12]}"
    summary_text = f"Clipped job posting from browser: {payload.position} at {payload.company}."
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
        logger.warning("Embedding deferred for clipped application %s: %s", application.id, err)

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
