from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)
from app.models.staging import StagingItemModel
from app.schemas.applications import ApplicationEventDetail
from app.schemas.events import ActionItemSummary, OtherEventDetail, ResolveActionRequest

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "/applications/{application_id}",
    response_model=list[ApplicationEventDetail],
    summary="Get all email events for a specific application",
)
async def list_application_events(
    application_id: int, db: AsyncSession = Depends(get_db)
):
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
    response_model=list[ActionItemSummary],
    summary="Get all pending action items across application and other events",
)
async def list_action_required_events(db: AsyncSession = Depends(get_db)):
    """Aggregates all events where action_required is TRUE for dashboard alerts."""
    action_items = []

    # 1. Fetch pending application events
    app_stmt = (
        select(ApplicationEventModel, ApplicationModel, CompanyModel)
        .join(
            ApplicationModel,
            ApplicationEventModel.email_application_id == ApplicationModel.id,
        )
        .join(CompanyModel, ApplicationModel.company_id == CompanyModel.id)
        .where(ApplicationEventModel.email_action_required)
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
        .where(OtherEventModel.action_required)
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
    response_model=list[OtherEventDetail],
    summary="List non-application related email events",
)
async def list_other_events(
    email_type: str | None = Query(
        None, description="Filter by non-application email type"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Returns stored logs of non-job recruitment emails (e.g. newsletters, automated promos)."""
    stmt = select(OtherEventModel)
    if email_type:
        stmt = stmt.where(OtherEventModel.email_type == email_type)

    stmt = (
        stmt.order_by(OtherEventModel.email_received_at.desc())
        .limit(limit)
        .offset(offset)
    )
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
    return {
        "status": "success",
        "event_id": event_id,
        "action_required": payload.action_required,
    }


@router.delete(
    "/{event_id}",
    summary="Delete a timeline event",
)
async def delete_event(
    event_id: int,
    source: str = Query("application", pattern="^(application|other)$"),
    db: AsyncSession = Depends(get_db),
):
    """Deletes an application timeline event or other event."""
    if source == "application":
        stmt = select(ApplicationEventModel).where(ApplicationEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalars().first()
        if not event:
            raise HTTPException(status_code=404, detail="Application event not found")
        await db.delete(event)
    else:
        stmt = select(OtherEventModel).where(OtherEventModel.id == event_id)
        result = await db.execute(stmt)
        event = result.scalars().first()
        if not event:
            raise HTTPException(status_code=404, detail="Other event not found")
        await db.delete(event)

    await db.commit()
    return {"status": "success", "event_id": event_id}


@router.post(
    "/{event_id}/move-to-staging",
    summary="Unlink an application email event and move it to the Staging Queue",
)
async def move_event_to_staging(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Unlinks an email event from its application, removes associated action items,
    and moves/restores it into the Staging queue with status PENDING for re-triaging.
    """
    stmt = (
        select(ApplicationEventModel)
        .where(ApplicationEventModel.id == event_id)
        .options(
            selectinload(ApplicationEventModel.application).selectinload(
                ApplicationModel.company
            )
        )
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Application event not found")

    app_id = event.email_application_id
    app = event.application

    # Check if a staging item already exists for this email
    staged_item = None
    if event.email_message_id:
        st_stmt = select(StagingItemModel).where(
            StagingItemModel.email_message_id == event.email_message_id
        )
        st_res = await db.execute(st_stmt)
        staged_item = st_res.scalars().first()

    if staged_item:
        staged_item.status = "PENDING"
        staged_item.match_reason = "UNLINKED_MANUALLY"
    else:
        extracted = event.raw_payload or {}
        if app and app.company:
            extracted.setdefault("company", app.company.name)
        if app and app.position:
            extracted.setdefault("position", app.position)
        if event.email_summary:
            extracted.setdefault("summary", event.email_summary)

        staged_item = StagingItemModel(
            email_message_id=event.email_message_id,
            email_internet_message_id=event.email_internet_message_id,
            email_conversation_id=event.email_conversation_id,
            email_sender=event.email_sender,
            email_sender_name=event.email_sender_name,
            email_subject=event.email_subject,
            email_received_at=event.email_received_at,
            email_raw_body=event.email_raw_body,
            extracted_data=extracted,
            match_reason="UNLINKED_MANUALLY",
            status="PENDING",
        )
        db.add(staged_item)

    # Delete any pending action items associated with this event
    act_stmt = select(ActionItemModel).where(ActionItemModel.event_id == event.id)
    act_res = await db.execute(act_stmt)
    for act in act_res.scalars().all():
        await db.delete(act)

    # Delete the event from application
    await db.delete(event)
    await db.flush()

    # Recalculate application last_activity_at
    if app:
        rem_stmt = (
            select(ApplicationEventModel.email_received_at)
            .where(ApplicationEventModel.email_application_id == app_id)
            .order_by(ApplicationEventModel.email_received_at.desc())
        )
        rem_res = await db.execute(rem_stmt)
        latest_date = rem_res.scalars().first()
        app.last_activity_at = latest_date or app.created_at

    await db.commit()
    await db.refresh(staged_item)

    return {
        "status": "success",
        "message": "Event unlinked and moved to Staging Queue.",
        "staging_item_id": staged_item.id,
        "application_id": app_id,
    }
