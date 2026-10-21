import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel
from app.schemas.system import BadgeCountsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

ACTIVE_TASK_STATUSES = [
    "QUEUED",
    "PROCESSING",
    "FETCHING",
    "EXTRACTING",
    "MATCHING",
    "ASSESSING",
    "SAVING",
]


@router.get("/badges", response_model=BadgeCountsResponse)
async def get_badge_counts(db: AsyncSession = Depends(get_db)) -> BadgeCountsResponse:
    """
    Returns aggregated counts for Navbar and drawer badges in a single optimized DB round-trip:
    - Staging queue items pending review
    - Pending action items
    - Active background queue/intake tasks
    - Total application count
    - Latest activity timestamp across all applications, events, and action items
    """
    staging_stmt = select(func.count(StagingItemModel.id)).where(
        StagingItemModel.status == "PENDING"
    )
    action_items_stmt = select(func.count(ActionItemModel.id)).where(
        ActionItemModel.status == "PENDING"
    )
    active_tasks_stmt = select(func.count(IntakeEvaluationTaskModel.id)).where(
        IntakeEvaluationTaskModel.status.in_(ACTIVE_TASK_STATUSES)
    )
    total_apps_stmt = select(func.count(ApplicationModel.id))
    latest_app_activity_stmt = select(
        func.greatest(
            func.max(ApplicationModel.last_activity_at),
            func.max(ApplicationModel.updated_at),
        )
    )
    latest_action_activity_stmt = select(
        func.greatest(
            func.max(ActionItemModel.updated_at),
            func.max(ActionItemModel.created_at),
        )
    )
    latest_event_activity_stmt = select(func.max(ApplicationEventModel.created_at))

    staging_res = await db.scalar(staging_stmt)
    action_items_res = await db.scalar(action_items_stmt)
    active_tasks_res = await db.scalar(active_tasks_stmt)
    total_apps_res = await db.scalar(total_apps_stmt)
    latest_app_res = await db.scalar(latest_app_activity_stmt)
    latest_action_res = await db.scalar(latest_action_activity_stmt)
    latest_event_res = await db.scalar(latest_event_activity_stmt)

    candidates = [
        ts
        for ts in (latest_app_res, latest_action_res, latest_event_res)
        if ts is not None
    ]
    latest_activity_res = max(candidates) if candidates else None

    return BadgeCountsResponse(
        staging_count=staging_res or 0,
        pending_action_items_count=action_items_res or 0,
        active_queue_tasks_count=active_tasks_res or 0,
        total_applications_count=total_apps_res or 0,
        latest_activity_at=latest_activity_res,
    )
