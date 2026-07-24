from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust imports based on your database session setup
from app.core.database import get_db
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.models.staging import StagingItemModel
from app.schemas.staging import (
    StagingItemRead,
    StagingItemResolve,
    StagingPaginationResponse,
)
from app.services.llm import generate_and_save_application_embedding

router = APIRouter(prefix="/staging", tags=["staging"])


@router.get("", response_model=StagingPaginationResponse)
async def list_staging_items(
    status_filter: Optional[str] = Query(default="PENDING", alias="status"),
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
        query.order_by(StagingItemModel.created_at.desc())
        .offset(offset)
        .limit(limit)
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

        # Option A: User provided explicit application_id
        if payload.application_id:
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
            company_norm = payload.company_name.strip().lower()
            comp_stmt = select(CompanyModel).where(
                CompanyModel.name_normalized == company_norm
            )
            comp_res = await db.execute(comp_stmt)
            company = comp_res.scalar_one_or_none()

            if not company:
                company = CompanyModel(
                    name=payload.company_name,
                    name_normalized=company_norm,
                )
                db.add(company)
                await db.flush()

            position_norm = payload.position.strip().lower()
            app_stmt = select(ApplicationModel).where(
                ApplicationModel.company_id == company.id,
                ApplicationModel.position_normalized == position_norm,
            )
            app_res = await db.execute(app_stmt)
            application = app_res.scalar_one_or_none()

            if not application:
                application = ApplicationModel(
                    company_id=company.id,
                    position=payload.position,
                    position_normalized=position_norm,
                    external_job_id=payload.external_job_id,
                    job_url=payload.job_url,
                    status=payload.status or "APPLIED",
                )
                db.add(application)
                await db.flush()

        # Update application status if modified
        if payload.status:
            application.status = payload.status

        # Create Timeline Event
        event = ApplicationEventModel(
            email_application_id=application.id,
            email_message_id=staged_item.email_message_id,
            email_conversation_id=staged_item.email_conversation_id,
            email_sender=staged_item.email_sender,
            email_sender_name=staged_item.email_sender_name,
            email_subject=staged_item.email_subject,
            email_received_at=staged_item.email_received_at,
            email_event_type=payload.event_type or "UPDATED",
            email_summary=payload.summary or staged_item.extracted_data.get("summary"),
            email_action_required=payload.action_required,
            email_action=payload.action,
            email_raw_body=staged_item.email_raw_body,
        )
        db.add(event)

        # Mark item as PROCESSED
        staged_item.status = "PROCESSED"
        await db.commit()

        await generate_and_save_application_embedding(db, application.id)

        return {
            "status": "success",
            "message": "Staged item resolved and committed to database.",
            "application_id": application.id,
            "event_id": event.id,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve staging item: {str(e)}",
        )


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