import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
)

logger = logging.getLogger(__name__)


async def archive_stale_applications(
    db: AsyncSession,
    threshold_days: int = 30,
    target_status: str = "REJECTED",
) -> dict[str, Any]:
    """
    Finds all applications in 'APPLIED' status where last_activity_at
    (or application_date) is older than threshold_days.
    Transitions them to target_status, logs a timeline event, and dismisses pending action items.
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=threshold_days)

    query = select(ApplicationModel).where(
        ApplicationModel.status == "APPLIED",
        func.coalesce(
            ApplicationModel.last_activity_at,
            ApplicationModel.application_date,
            ApplicationModel.created_at,
        )
        < cutoff_date,
    )
    result = await db.execute(query)
    applications = result.scalars().all()

    archived_ids = []

    for app in applications:
        # Update app.status = 'REJECTED'.
        app.status = target_status
        # Set app.last_activity_at = now().
        app.last_activity_at = datetime.now(UTC)

        # Create an ApplicationEventModel
        event = ApplicationEventModel(
            email_application_id=app.id,
            email_event_type="STATUS_CHANGE",
            email_status_after_event=target_status,
            email_summary=f"Application automatically archived due to {threshold_days} days of inactivity.",
            source_channel="SYSTEM",
            raw_payload={
                "rejection_reason": f"Ghosted / Inactive for {threshold_days}+ days (Auto-Archived)"
            },
        )
        db.add(event)

        # Dismiss any pending action items (ActionItemModel.status = 'DISMISSED').
        # Using select to find pending action items
        action_items_query = select(ActionItemModel).where(
            ActionItemModel.application_id == app.id,
            ActionItemModel.status == "PENDING",
        )
        action_items_result = await db.execute(action_items_query)
        pending_items = action_items_result.scalars().all()
        for item in pending_items:
            item.status = "DISMISSED"

        archived_ids.append(app.id)

    await db.commit()

    return {"archived_count": len(archived_ids), "archived_ids": archived_ids}


async def staleness_archiver_worker(session_factory, interval_seconds: int = 86400):
    """
    Background worker that runs once every interval_seconds.
    """
    logger.info("Staleness archiver worker started.")
    while True:
        try:
            async with session_factory() as session:
                stats = await archive_stale_applications(session)
                logger.info(
                    f"Auto-archiver executed. Archived {stats['archived_count']} applications."
                )
        except asyncio.CancelledError:
            logger.info("Staleness archiver worker cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in staleness archiver worker: {e}")

        await asyncio.sleep(interval_seconds)
