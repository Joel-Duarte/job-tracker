import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.applications import ActionItemModel
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

    staging_res = await db.scalar(staging_stmt)
    action_items_res = await db.scalar(action_items_stmt)
    active_tasks_res = await db.scalar(active_tasks_stmt)

    return BadgeCountsResponse(
        staging_count=staging_res or 0,
        pending_action_items_count=action_items_res or 0,
        active_queue_tasks_count=active_tasks_res or 0,
    )
