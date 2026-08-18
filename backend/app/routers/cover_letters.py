import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.applications import ApplicationModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.cover_letter import (
    CoverLetterGenerateRequest,
    CoverLetterResponse,
    CoverLetterUpdateRequest,
)
from app.services.evaluation_worker import process_evaluation_task

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Cover Letters"])


def _to_cover_letter_response(app: ApplicationModel) -> CoverLetterResponse:
    content = app.cover_letter_markdown
    status_val = app.cover_letter_status or "PENDING"
    skills = app.cover_letter_highlighted_skills or []
    return CoverLetterResponse(
        application_id=app.id,
        cover_letter_markdown=content,
        content=content,
        cover_letter_status=status_val,
        status=status_val,
        highlighted_skills=skills,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.post(
    "/applications/{application_id}/cover-letter/generate",
    response_model=CoverLetterResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_cover_letter_endpoint(
    application_id: int,
    payload: CoverLetterGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> CoverLetterResponse:
    """Queues an async on-demand cover letter generation background task."""
    stmt = (
        select(ApplicationModel)
        .options(joinedload(ApplicationModel.company))
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID {application_id} not found.",
        )

    # Set application cover_letter_status to PENDING
    app.cover_letter_status = "PENDING"
    app.updated_at = datetime.now(UTC)

    company_name = app.company.name if app.company else f"App {application_id}"
    custom_inst = payload.custom_instructions if payload else None
    tone_val = payload.tone if payload else None

    # Queue background task
    task = IntakeEvaluationTaskModel(
        task_type="COVER_LETTER_GENERATION",
        status="QUEUED",
        stage="QUEUED",
        title_hint=f"Cover Letter - {company_name}",
        result_json={
            "application_id": application_id,
            "custom_instructions": custom_inst,
            "tone": tone_val,
        },
    )
    db.add(task)
    await db.commit()
    await db.refresh(app)

    # Trigger async evaluation worker
    asyncio.create_task(process_evaluation_task(task.id))

    return _to_cover_letter_response(app)


@router.get(
    "/applications/{application_id}/cover-letter",
    response_model=CoverLetterResponse,
)
async def get_cover_letter_endpoint(
    application_id: int,
    db: AsyncSession = Depends(get_db),
) -> CoverLetterResponse:
    """Retrieves existing cover letter content and status for an application."""
    stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID {application_id} not found.",
        )

    return _to_cover_letter_response(app)


@router.put(
    "/applications/{application_id}/cover-letter",
    response_model=CoverLetterResponse,
)
async def update_cover_letter_endpoint(
    application_id: int,
    payload: CoverLetterUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> CoverLetterResponse:
    """Saves user-edited cover letter markdown text directly."""
    stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID {application_id} not found.",
        )

    app.cover_letter_markdown = payload.content
    app.cover_letter_status = "COMPLETED"
    app.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(app)

    return _to_cover_letter_response(app)
