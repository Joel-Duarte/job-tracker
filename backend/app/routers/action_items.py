import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.applications import ActionItemModel, ApplicationModel, CompanyModel
from app.schemas.action_items import (
    ActionItemCreate,
    ActionItemListResponse,
    ActionItemResponse,
    ActionItemUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/action-items", tags=["Action Items"])


@router.get("", response_model=ActionItemListResponse, summary="List action items with filters and metrics")
async def list_action_items(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, COMPLETED, DISMISSED)"),
    urgency: Optional[str] = Query(None, description="Filter by urgency (HIGH, MEDIUM, LOW)"),
    application_id: Optional[int] = Query(None, description="Filter by specific application ID"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """Fetches action items ordered by urgency and due date, joined with application and company metadata."""
    # Metrics query across all items (or scoped to application if filtered)
    metrics_stmt = select(
        func.count().label("total"),
        func.count(case((ActionItemModel.status == "PENDING", 1))).label("pending"),
        func.count(case(((ActionItemModel.status == "PENDING") & (ActionItemModel.urgency == "HIGH"), 1))).label("high_urgency"),
        func.count(case((ActionItemModel.status == "COMPLETED", 1))).label("completed"),
    )
    if application_id:
        metrics_stmt = metrics_stmt.where(ActionItemModel.application_id == application_id)

    metrics_res = await db.execute(metrics_stmt)
    metrics_row = metrics_res.one()

    # Query with joined relations
    stmt = (
        select(ActionItemModel)
        .outerjoin(ActionItemModel.application)
        .outerjoin(ApplicationModel.company)
        .options(
            joinedload(ActionItemModel.application).joinedload(ApplicationModel.company),
        )
    )

    if status_filter:
        stmt = stmt.where(ActionItemModel.status == status_filter.upper())
    if urgency:
        stmt = stmt.where(ActionItemModel.urgency == urgency.upper())
    if application_id:
        stmt = stmt.where(ActionItemModel.application_id == application_id)

    # Order: PENDING first, then HIGH urgency, then nearest due date, then newest
    stmt = stmt.order_by(
        case((ActionItemModel.status == "PENDING", 0), else_=1),
        case((ActionItemModel.urgency == "HIGH", 0), (ActionItemModel.urgency == "MEDIUM", 1), else_=2),
        ActionItemModel.due_date.asc().nulls_last(),
        ActionItemModel.created_at.desc(),
    )
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    items = result.scalars().all()

    response_items = []
    for item in items:
        app = item.application
        company_name = app.company.name if app and app.company else None
        position = app.position if app else None
        app_status = app.status if app else None

        response_items.append(
            ActionItemResponse(
                id=item.id,
                application_id=item.application_id,
                event_id=item.event_id,
                title=item.title,
                due_date=item.due_date,
                status=item.status,
                action_url=item.action_url,
                urgency=item.urgency or "MEDIUM",
                created_at=item.created_at,
                updated_at=item.updated_at,
                company_name=company_name,
                position=position,
                application_status=app_status,
            )
        )

    return ActionItemListResponse(
        items=response_items,
        total=metrics_row.total or 0,
        pending_count=metrics_row.pending or 0,
        high_urgency_count=metrics_row.high_urgency or 0,
        completed_count=metrics_row.completed or 0,
    )


@router.post("", response_model=ActionItemResponse, status_code=status.HTTP_201_CREATED, summary="Create a new action item")
async def create_action_item(
    payload: ActionItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new action item for a job application or standalone task."""
    # Verify application exists if application_id provided
    company_name = None
    position = None
    app_status = None

    if payload.application_id:
        app_stmt = (
            select(ApplicationModel)
            .where(ApplicationModel.id == payload.application_id)
            .options(joinedload(ApplicationModel.company))
        )
        app_res = await db.execute(app_stmt)
        app = app_res.scalars().first()
        if not app:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        company_name = app.company.name if app.company else None
        position = app.position
        app_status = app.status

    action_item = ActionItemModel(
        application_id=payload.application_id,
        title=payload.title.strip(),
        due_date=payload.due_date,
        urgency=payload.urgency.upper() if payload.urgency else "MEDIUM",
        status=payload.status.upper() if payload.status else "PENDING",
        action_url=payload.action_url,
    )
    db.add(action_item)
    await db.commit()
    await db.refresh(action_item)

    return ActionItemResponse(
        id=action_item.id,
        application_id=action_item.application_id,
        event_id=action_item.event_id,
        title=action_item.title,
        due_date=action_item.due_date,
        status=action_item.status,
        action_url=action_item.action_url,
        urgency=action_item.urgency,
        created_at=action_item.created_at,
        updated_at=action_item.updated_at,
        company_name=company_name,
        position=position,
        application_status=app_status,
    )


@router.patch("/{action_item_id}", response_model=ActionItemResponse, summary="Partially update an action item")
async def update_action_item(
    action_item_id: int,
    payload: ActionItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Updates an action item's status, title, due date, or urgency."""
    stmt = (
        select(ActionItemModel)
        .where(ActionItemModel.id == action_item_id)
        .options(
            joinedload(ActionItemModel.application).joinedload(ApplicationModel.company),
        )
    )
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None and key in ["status", "urgency"]:
            setattr(item, key, value.upper())
        elif key in update_data:
            setattr(item, key, value)

    await db.commit()
    await db.refresh(item)

    app = item.application
    company_name = app.company.name if app and app.company else None
    position = app.position if app else None
    app_status = app.status if app else None

    return ActionItemResponse(
        id=item.id,
        application_id=item.application_id,
        event_id=item.event_id,
        title=item.title,
        due_date=item.due_date,
        status=item.status,
        action_url=item.action_url,
        urgency=item.urgency,
        created_at=item.created_at,
        updated_at=item.updated_at,
        company_name=company_name,
        position=position,
        application_status=app_status,
    )


@router.delete("/{action_item_id}", status_code=status.HTTP_200_OK, summary="Delete an action item")
async def delete_action_item(
    action_item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Permanently deletes an action item."""
    stmt = select(ActionItemModel).where(ActionItemModel.id == action_item_id)
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")

    await db.delete(item)
    await db.commit()

    return {
        "status": "success",
        "message": f"Action item {action_item_id} deleted successfully",
        "id": action_item_id,
    }
