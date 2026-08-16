import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust imports based on your database session setup
from app.core.database import get_db
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.staging import StagingItemModel
from app.schemas.staging import (
    StagingItemRead,
    StagingItemResolve,
    StagingPaginationResponse,
)
from app.services.llm import generate_and_save_application_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staging", tags=["staging"])


@router.get("", response_model=StagingPaginationResponse)
async def list_staging_items(
    status_filter: str | None = Query(default="PENDING", alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(StagingItemModel)
    count_query = select(func.count()).select_from(StagingItemModel)

    if status_filter:
        query = query.where(StagingItemModel.status == status_filter)
        count_query = count_query.where(StagingItemModel.status == status_filter)

    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    query = (
        query.order_by(StagingItemModel.created_at.desc()).offset(offset).limit(limit)
    )
    result = await db.execute(query)
    db_items = result.scalars().all()

    # Convert ORM models explicitly to StagingItemRead Pydantic instances
    items = [StagingItemRead.model_validate(item) for item in db_items]

    return StagingPaginationResponse(total=total, items=items)


@router.get("/{item_id}", response_model=StagingItemRead)
async def get_staging_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetches full details for a single staged item."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    return item


@router.post("/{item_id}/resolve", response_model=dict)
async def resolve_staging_item(
    item_id: int,
    payload: StagingItemResolve,
    db: AsyncSession = Depends(get_db),
):
    """Accepts user fixes, applies them to DB records, and marks the staged item PROCESSED."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    staged_item = res.scalar_one_or_none()

    if not staged_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    if staged_item.status == "PROCESSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item has already been processed.",
        )

    try:
        application = None
        effective_company = (
            payload.company_name or payload.company or "Unknown Company"
        ).strip()
        company_norm = effective_company.lower()
        position_norm = payload.position.strip().lower()

        # Option A: User provided explicit application_id
        if payload.application_id and not payload.create_new:
            app_stmt = select(ApplicationModel).where(
                ApplicationModel.id == payload.application_id
            )
            app_res = await db.execute(app_stmt)
            application = app_res.scalar_one_or_none()

            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target Application ID {payload.application_id} not found.",
                )

        # Option B: Match or create company and application
        if not application:
            comp_stmt = select(CompanyModel).where(
                CompanyModel.name_normalized == company_norm
            )
            comp_res = await db.execute(comp_stmt)
            company = comp_res.scalar_one_or_none()

            if not company:
                company = CompanyModel(
                    name=effective_company,
                    name_normalized=company_norm,
                )
                db.add(company)
                await db.flush()

            if not payload.create_new:
                app_stmt = select(ApplicationModel).where(
                    ApplicationModel.company_id == company.id,
                    ApplicationModel.position_normalized == position_norm,
                )
                app_res = await db.execute(app_stmt)
                application = app_res.scalar_one_or_none()

            if not application:
                application = ApplicationModel(
                    company_id=company.id,
                    position=payload.position.strip(),
                    position_normalized=position_norm,
                    external_job_id=payload.external_job_id,
                    job_url=payload.job_url,
                    status=payload.status or "ASSESSMENT",
                )
                db.add(application)
                await db.flush()

        # Update application status if modified
        if payload.status:
            application.status = payload.status
        if payload.job_url and not application.job_url:
            application.job_url = payload.job_url

        # Extract specs from payload or staged item
        extracted = (
            staged_item.extracted_data
            if isinstance(staged_item.extracted_data, dict)
            else (
                staged_item.extracted_data.model_dump()
                if hasattr(staged_item.extracted_data, "model_dump")
                else {}
            )
        )

        desc_md = payload.description_markdown or staged_item.email_raw_body
        salary_min = (
            payload.salary_min
            if payload.salary_min is not None
            else extracted.get("salary_min")
        )
        salary_max = (
            payload.salary_max
            if payload.salary_max is not None
            else extracted.get("salary_max")
        )
        currency = payload.currency or extracted.get("currency", "USD")
        location = payload.location or extracted.get("location")
        work_model = payload.work_model or extracted.get("work_model")
        skills = (
            payload.required_skills
            or extracted.get("required_skills")
            or list(
                dict.fromkeys(
                    (extracted.get("matching_skills") or [])
                    + (extracted.get("missing_skills") or [])
                )
            )
        )

        # Upsert JobPostingModel
        jp_stmt = select(JobPostingModel).where(
            JobPostingModel.application_id == application.id
        )
        jp_res = await db.execute(jp_stmt)
        job_posting = jp_res.scalar_one_or_none()

        if not job_posting:
            job_posting = JobPostingModel(
                application_id=application.id,
                job_url=payload.job_url or f"lead-{application.id}",
                description_markdown=desc_md,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                location=location,
                work_model=work_model,
                required_skills=skills,
            )
            db.add(job_posting)
        else:
            if desc_md:
                job_posting.description_markdown = desc_md
            if salary_min is not None:
                job_posting.salary_min = salary_min
            if salary_max is not None:
                job_posting.salary_max = salary_max
            if location:
                job_posting.location = location
            if work_model:
                job_posting.work_model = work_model
            if skills:
                job_posting.required_skills = skills

        # Create Timeline Event
        summary_val = (
            payload.summary
            or extracted.get("summary")
            or staged_item.email_subject
            or f"Staged item resolved for {payload.position} at {effective_company}."
        )
        event = ApplicationEventModel(
            email_application_id=application.id,
            email_message_id=staged_item.email_message_id,
            email_conversation_id=staged_item.email_conversation_id
            or f"stage-conv-{staged_item.id}",
            email_sender=staged_item.email_sender,
            email_sender_name=staged_item.email_sender_name,
            email_subject=staged_item.email_subject,
            email_received_at=staged_item.email_received_at or datetime.now(UTC),
            email_event_type=payload.event_type or "PRE_APPLICATION_ASSESSMENT",
            email_status_after_event=application.status,
            email_summary=summary_val,
            email_action_required=payload.action_required,
            email_action=payload.action,
            email_raw_body=staged_item.email_raw_body,
            raw_payload=extracted if isinstance(extracted, dict) else None,
            source_channel="STAGING",
        )
        db.add(event)
        await db.flush()

        # Check if Action Item should be generated
        action_text = (
            payload.action
            or extracted.get("action_text")
            or (staged_item.email_subject if payload.action_required else None)
        )
        if (
            payload.action_required or extracted.get("action_required")
        ) and action_text:
            action_item = ActionItemModel(
                application_id=application.id,
                event_id=event.id,
                title=str(action_text)[:250],
                status="PENDING",
                urgency="HIGH"
                if any(
                    w in str(action_text).lower()
                    for w in ["urgent", "deadline", "schedule", "asap"]
                )
                else "MEDIUM",
            )
            db.add(action_item)

        # Save IDs to variables before committing so we don't access expired ORM attributes
        target_app_id = application.id

        # Mark item as PROCESSED and save records to DB
        staged_item.status = "PROCESSED"
        await db.flush()
        target_event_id = event.id
        await db.commit()

    except Exception as e:
        logger.error("Failed to resolve staging item %d: %s", item_id, e, exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve staging item: {e!s}",
        )

    # Isolated embedding block after successful commit
    try:
        await generate_and_save_application_embedding(db, target_app_id)
    except Exception as e:
        logger.warning(
            "Failed to generate embedding for Application ID %d: %s", target_app_id, e
        )

    return {
        "status": "success",
        "message": "Staged item resolved and committed to database.",
        "application_id": target_app_id,
        "event_id": target_event_id,
    }


@router.delete("/{item_id}", response_model=dict)
async def reject_staging_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Marks a staged item as REJECTED if it is a false positive or non-job email."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    staged_item = res.scalar_one_or_none()

    if not staged_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    staged_item.status = "REJECTED"
    await db.commit()

    return {
        "status": "success",
        "message": f"Staging item {item_id} marked as REJECTED.",
    }
