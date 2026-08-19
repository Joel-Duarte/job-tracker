import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import load_settings
from app.models.agent_chat import AgentChatModel
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
)

logger = logging.getLogger(__name__)

ACTIVE_STAGES = ("APPLIED", "ONLINE_ASSESSMENT", "TECHNICAL_INTERVIEW", "OFFER")


async def archive_stale_applications(
    db: AsyncSession,
    threshold_days: int = 30,
    target_status: str = "ARCHIVED",
) -> dict[str, Any]:
    """
    Finds all applications in active stages where last_activity_at
    (or application_date or created_at) is older than threshold_days.
    Transitions them to target_status (default ARCHIVED), logs a timeline event,
    and dismisses pending action items.
    Terminal statuses (HIRED, ARCHIVED, WITHDRAWN, REJECTED) are never touched.
    """
    cutoff_date = datetime.now(UTC) - timedelta(days=threshold_days)

    query = select(ApplicationModel).where(
        ApplicationModel.status.in_(ACTIVE_STAGES),
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
        app.status = target_status
        app.last_activity_at = datetime.now(UTC)

        event = ApplicationEventModel(
            email_application_id=app.id,
            email_event_type="STATUS_CHANGE",
            email_status_after_event=target_status,
            email_summary=f"Application automatically archived — no activity for {threshold_days}+ days.",
            source_channel="SYSTEM",
            raw_payload={
                "archive_reason": f"Ghosted / Inactive for {threshold_days}+ days (Auto-Archived)"
            },
        )
        db.add(event)

        action_items_query = select(ActionItemModel).where(
            ActionItemModel.application_id == app.id,
            ActionItemModel.status == "PENDING",
        )
        action_items_result = await db.execute(action_items_query)
        for item in action_items_result.scalars().all():
            item.status = "DISMISSED"

        archived_ids.append(app.id)

    await db.commit()

    return {"archived_count": len(archived_ids), "archived_ids": archived_ids}


async def delete_stale_agent_chats(db: AsyncSession) -> int:
    settings = await load_settings(db)
    retention_days = settings.get("AGENT_CHAT_RETENTION_DAYS", 0)
    if retention_days <= 0:
        return 0

    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
    stmt = delete(AgentChatModel).where(AgentChatModel.updated_at < cutoff_date)
    result = await db.execute(stmt)
    await db.commit()
    return getattr(result, "rowcount", 0) or 0


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

                deleted_chats = await delete_stale_agent_chats(session)
                if deleted_chats > 0:
                    logger.info(
                        f"Auto-archiver executed. Deleted {deleted_chats} stale agent chats."
                    )

        except asyncio.CancelledError:
            logger.info("Staleness archiver worker cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in staleness archiver worker: {e}")

        await asyncio.sleep(interval_seconds)
