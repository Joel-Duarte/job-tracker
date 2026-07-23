from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)
from app.schemas.applications import ApplicationEventDetail
from app.schemas.events import ActionItemSummary, OtherEventDetail, ResolveActionRequest

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "/applications/{application_id}",
    response_model=List[ApplicationEventDetail],
    summary="Get all email events for a specific application",
)
async def list_application_events(application_id: int, db: AsyncSession = Depends(get_db)):
    """Returns chronologically ordered email events associated with a job application."""
    stmt = (
        select(ApplicationEventModel)
        .where(ApplicationEventModel.email_application_id == application_id)
        .order_by(ApplicationEventModel.email_received_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/action-required",
    response_model=List[ActionItemSummary],
    summary="Get all pending action items across application and other events",
)
async def list_action_required_events(db: AsyncSession = Depends(get_db)):
    """Aggregates all events where action_required is TRUE for dashboard alerts."""
    action_items = []

    # 1. Fetch pending application events
    app_stmt = (
        select(ApplicationEventModel, ApplicationModel, CompanyModel)
        .join(ApplicationModel, ApplicationEventModel.email_application_id == ApplicationModel.id)
        .join(CompanyModel, ApplicationModel.company_id == CompanyModel.id)
        .where(ApplicationEventModel.email_action_required == True)
        .order_by(ApplicationEventModel.email_received_at.desc())
    )
    app_result = await db.execute(app_stmt)
    for event, app, company in app_result.all():
        action_items.append(
            ActionItemSummary(
                id=event.id,
                source="application_event",
                application_id=app.id,
                company_name=company.name,
                subject=event.email_subject,
                sender=event.email_sender_name or event.email_sender,
                action=event.email_action,
                received_at=event.email_received_at,
            )
        )

    # 2. Fetch pending other events
    other_stmt = (
        select(OtherEventModel)
        .where(OtherEventModel.action_required == True)
        .order_by(OtherEventModel.email_received_at.desc())
    )
    other_result = await db.execute(other_stmt)
    for event in other_result.scalars().all():
        action_items.append(
            ActionItemSummary(
                id=event.id,
                source="other_event",
                application_id=None,
                company_name=event.company,
                subject=event.email_subject,
                sender=event.email_sender_name or event.email_sender,
                action=event.action,
                received_at=event.email_received_at,
            )
        )

    return action_items


@router.get(
    "/other",
    response_model=List[OtherEventDetail],
    summary="List non-application related email events",
)
async def list_other_events(
    email_type: Optional[str] = Query(None, description="Filter by non-application email type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Returns stored logs of non-job recruitment emails (e.g. newsletters, automated promos)."""
    stmt = select(OtherEventModel)
    if email_type:
        stmt = stmt.where(OtherEventModel.email_type == email_type)

    stmt = stmt.order_by(OtherEventModel.email_received_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch(
    "/{event_id}/action",
    summary="Resolve or update action status for an event",
)
async def resolve_event_action(
    event_id: int,
    payload: ResolveActionRequest,
    source: str = Query("application", pattern="^(application|other)$"),
    db: AsyncSession = Depends(get_db),
):
    """Marks an event's action item requirement as handled or active."""
    if source == "application":
        stmt = select(ApplicationEventModel).where(ApplicationEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalars().first()
        if not event:
            raise HTTPException(status_code=404, detail="Application event not found")
        event.email_action_required = payload.action_required
    else:
        stmt = select(OtherEventModel).where(OtherEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalars().first()
        if not event:
            raise HTTPException(status_code=404, detail="Other event not found")
        event.action_required = payload.action_required

    await db.commit()
    return {"status": "success", "event_id": event_id, "action_required": payload.action_required}