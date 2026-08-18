import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
)
from app.schemas.action_items import (
    ActionItemCreate,
    ActionItemListResponse,
    ActionItemResponse,
    ActionItemUpdate,
    UrgencyOverrideUpdate,
)
from app.services.llm import async_enqueue_application_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/action-items", tags=["Action Items"])


def compute_live_urgency(item: ActionItemModel) -> str:
    """Computes dynamic urgency based on manual override or due_date proximity."""
    if item.manual_urgency_override:
        return item.manual_urgency_override.upper()

    if item.due_date:
        time_diff = item.due_date - datetime.now(UTC)
        hours_diff = time_diff.total_seconds() / 3600

        if hours_diff < 24:
            return "HIGH"
        elif hours_diff <= 72:
            return "MEDIUM"
        else:
            return "LOW"

    return item.urgency or "MEDIUM"


@router.get(
    "",
    response_model=ActionItemListResponse,
    summary="List action items with filters and metrics",
)
async def list_action_items(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (PENDING, COMPLETED, DISMISSED)",
    ),
    urgency: str | None = Query(
        None, description="Filter by urgency (HIGH, MEDIUM, LOW)"
    ),
    application_id: int | None = Query(
        None, description="Filter by specific application ID"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """Fetches action items ordered by urgency and due date, joined with application and company metadata."""
    # Dynamic urgency SQL expression
    # 1. manual_urgency_override if not null
    # 2. else if due_date < 24h -> HIGH
    # 3. else if due_date <= 72h -> MEDIUM
    # 4. else if due_date -> LOW
    # 5. else default urgency

    live_urgency_expr = func.coalesce(
        ActionItemModel.manual_urgency_override,
        case(
            (ActionItemModel.due_date.is_(None), ActionItemModel.urgency),
            (
                func.extract("epoch", ActionItemModel.due_date - func.now()) / 3600
                < 24,
                "HIGH",
            ),
            (
                func.extract("epoch", ActionItemModel.due_date - func.now()) / 3600
                <= 72,
                "MEDIUM",
            ),
            else_="LOW",
        ),
    )

    # Metrics query across all items (or scoped to application if filtered)
    metrics_stmt = select(
        func.count().label("total"),
        func.count(case((ActionItemModel.status == "PENDING", 1))).label("pending"),
        func.count(
            case(
                (
                    (ActionItemModel.status == "PENDING")
                    & (live_urgency_expr == "HIGH"),
                    1,
                )
            )
        ).label("high_urgency"),
        func.count(case((ActionItemModel.status == "COMPLETED", 1))).label("completed"),
    )
    if application_id:
        metrics_stmt = metrics_stmt.where(
            ActionItemModel.application_id == application_id
        )

    metrics_res = await db.execute(metrics_stmt)
    metrics_row = metrics_res.one()

    # Query with joined relations
    stmt = (
        select(ActionItemModel)
        .outerjoin(ActionItemModel.application)
        .outerjoin(ApplicationModel.company)
        .options(
            joinedload(ActionItemModel.application).joinedload(
                ApplicationModel.company
            ),
        )
    )

    if status_filter:
        stmt = stmt.where(ActionItemModel.status == status_filter.upper())
    if urgency:
        stmt = stmt.where(live_urgency_expr == urgency.upper())
    if application_id:
        stmt = stmt.where(ActionItemModel.application_id == application_id)

    # Order: PENDING first, then HIGH urgency, then nearest due date, then newest
    stmt = stmt.order_by(
        case((ActionItemModel.status == "PENDING", 0), else_=1),
        case(
            (live_urgency_expr == "HIGH", 0),
            (live_urgency_expr == "MEDIUM", 1),
            else_=2,
        ),
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
                urgency=compute_live_urgency(item),
                manual_urgency_override=item.manual_urgency_override,
                created_at=item.created_at,
                updated_at=item.updated_at,
                company_name=company_name,
                position=position,
                application_status=app_status,
                draft_email=item.draft_email,
            )
        )

    return ActionItemListResponse(
        items=response_items,
        total=metrics_row.total or 0,
        pending_count=metrics_row.pending or 0,
        high_urgency_count=metrics_row.high_urgency or 0,
        completed_count=metrics_row.completed or 0,
    )


@router.post(
    "",
    response_model=ActionItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new action item",
)
async def create_action_item(
    payload: ActionItemCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Creates a new action item for a job application or standalone task."""
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
            )
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

    # If linked to application, refresh embedding in background
    if payload.application_id:
        background_tasks.add_task(
            async_enqueue_application_embedding,
            payload.application_id,
            skip_llm_summary=True,
        )

    return ActionItemResponse(
        id=action_item.id,
        application_id=action_item.application_id,
        event_id=action_item.event_id,
        title=action_item.title,
        due_date=action_item.due_date,
        status=action_item.status,
        action_url=action_item.action_url,
        urgency=compute_live_urgency(action_item),
        manual_urgency_override=action_item.manual_urgency_override,
        created_at=action_item.created_at,
        updated_at=action_item.updated_at,
        company_name=company_name,
        position=position,
        application_status=app_status,
        draft_email=action_item.draft_email,
    )


@router.patch(
    "/{action_item_id}",
    response_model=ActionItemResponse,
    summary="Partially update an action item",
)
async def update_action_item(
    action_item_id: int,
    payload: ActionItemUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Updates an action item's status, title, due date, or urgency, and records a timeline event on completion."""
    stmt = (
        select(ActionItemModel)
        .where(ActionItemModel.id == action_item_id)
        .options(
            joinedload(ActionItemModel.application).joinedload(
                ApplicationModel.company
            ),
        )
    )
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found"
        )

    old_status = item.status
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None and key in ["status", "urgency"]:
            setattr(item, key, value.upper())
        elif key in update_data:
            setattr(item, key, value)

    new_status = item.status

    # If marked as COMPLETED and linked to an application, record timeline event
    if new_status == "COMPLETED" and old_status != "COMPLETED" and item.application_id:
        app = item.application
        payload_data = {
            "action_item_id": item.id,
            "title": item.title,
            "urgency": item.urgency,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        if app and app.status == "TECHNICAL_INTERVIEW":
            payload_data["interview_stage"] = "Task Completed / Awaiting Response"

        event = ApplicationEventModel(
            email_application_id=item.application_id,
            email_conversation_id=f"task-comp-{item.id}",
            email_event_type="ACTION_ITEM_COMPLETED",
            email_status_after_event=app.status if app else None,
            email_summary=f"Completed action item: {item.title}. Awaiting response.",
            email_received_at=datetime.now(UTC),
            source_channel="MANUAL",
            raw_payload=payload_data,
        )
        db.add(event)

    await db.commit()
    await db.refresh(item)

    # Refresh application vector embedding in background
    if item.application_id:
        background_tasks.add_task(
            async_enqueue_application_embedding,
            item.application_id,
            skip_llm_summary=True,
        )

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
        urgency=compute_live_urgency(item),
        manual_urgency_override=item.manual_urgency_override,
        created_at=item.created_at,
        updated_at=item.updated_at,
        company_name=company_name,
        position=position,
        application_status=app_status,
        draft_email=item.draft_email,
    )


@router.put(
    "/{action_item_id}/urgency",
    response_model=ActionItemResponse,
    summary="Set manual urgency override",
)
async def override_action_item_urgency(
    action_item_id: int,
    payload: UrgencyOverrideUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Sets or clears a manual urgency override on an action item."""
    stmt = (
        select(ActionItemModel)
        .where(ActionItemModel.id == action_item_id)
        .options(
            joinedload(ActionItemModel.application).joinedload(
                ApplicationModel.company
            ),
        )
    )
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found"
        )

    if payload.manual_urgency:
        item.manual_urgency_override = payload.manual_urgency.upper()
    else:
        item.manual_urgency_override = None

    await db.commit()
    await db.refresh(item)

    if item.application_id:
        background_tasks.add_task(
            async_enqueue_application_embedding,
            item.application_id,
            skip_llm_summary=True,
        )

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
        urgency=compute_live_urgency(item),
        manual_urgency_override=item.manual_urgency_override,
        created_at=item.created_at,
        updated_at=item.updated_at,
        company_name=company_name,
        position=position,
        application_status=app_status,
        draft_email=item.draft_email,
    )


@router.delete(
    "/{action_item_id}", status_code=status.HTTP_200_OK, summary="Delete an action item"
)
async def delete_action_item(
    action_item_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Permanently deletes an action item."""
    stmt = select(ActionItemModel).where(ActionItemModel.id == action_item_id)
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found"
        )

    app_id = item.application_id
    await db.delete(item)
    await db.commit()

    if app_id:
        background_tasks.add_task(
            async_enqueue_application_embedding, app_id, skip_llm_summary=True
        )

    return {
        "status": "success",
        "message": f"Action item {action_item_id} deleted successfully",
        "id": action_item_id,
    }


@router.post(
    "/{action_item_id}/draft-reply",
    response_model=ActionItemResponse,
    summary="Auto-draft an email reply using LLM",
)
async def draft_action_item_reply(
    action_item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generates an email reply draft for a specific action item if linked to an application and event."""
    from app.services.llm import generate_email_reply_draft

    stmt = (
        select(ActionItemModel)
        .where(ActionItemModel.id == action_item_id)
        .options(
            joinedload(ActionItemModel.application).joinedload(
                ApplicationModel.company
            ),
        )
    )
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found"
        )

    if not item.application_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action item is not linked to an application",
        )

    app_id = item.application_id

    event_stmt = (
        select(ApplicationEventModel)
        .where(ApplicationEventModel.email_application_id == app_id)
        .order_by(ApplicationEventModel.email_received_at.desc())
    )
    event_res = await db.execute(event_stmt)
    event_list = event_res.scalars().all()

    if not event_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No application events found for this application to draft a reply.",
        )

    event_text_list = []
    for e in event_list:
        if e.email_body_text:
            event_text_list.append(
                f"Date: {e.email_received_at}\nBody:\n{e.email_body_text}\n"
            )

    events_context = "\n---\n".join(event_text_list)

    draft = await generate_email_reply_draft(app_id, db, item.title, events_context)

    item.draft_email = draft
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
        urgency=compute_live_urgency(item),
        manual_urgency_override=item.manual_urgency_override,
        created_at=item.created_at,
        updated_at=item.updated_at,
        company_name=company_name,
        position=position,
        application_status=app_status,
        draft_email=item.draft_email,
    )
