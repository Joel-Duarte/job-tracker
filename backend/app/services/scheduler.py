import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models.applications import ActionItemModel, ApplicationModel
from app.services.llm import generate_nudge_email

logger = logging.getLogger(__name__)


async def monitor_stale_applications(async_session_maker: sessionmaker):
    """
    Background worker that checks for stale applications once a day
    and creates 'Follow-up' action items with generated draft emails.
    """
    from app.core.config_manager import get_setting

    logger.info("Scheduler for stale applications started.")
    while True:
        try:
            if not get_setting("ENABLE_AUTO_NUDGE", True):
                logger.info(
                    "Auto nudge is disabled. Skipping stale applications check."
                )
                await asyncio.sleep(24 * 60 * 60)
                continue

            async with async_session_maker() as session:
                threshold_date = datetime.now(UTC) - timedelta(days=7)

                stmt = (
                    select(ApplicationModel)
                    .where(
                        ApplicationModel.status.in_(["APPLIED", "TECHNICAL_INTERVIEW"])
                    )
                    .where(ApplicationModel.last_activity_at <= threshold_date)
                )
                res = await session.execute(stmt)
                stale_apps = res.scalars().all()

                for app in stale_apps:
                    # Check if there's already a pending follow-up action item
                    existing_stmt = (
                        select(ActionItemModel)
                        .where(ActionItemModel.application_id == app.id)
                        .where(ActionItemModel.status == "PENDING")
                        .where(ActionItemModel.title.like("%Follow-up%"))
                    )
                    existing_res = await session.execute(existing_stmt)
                    if existing_res.scalars().first():
                        continue

                    # Generate draft nudge email
                    try:
                        draft_text = await generate_nudge_email(session, app.id)
                    except Exception as e:
                        logger.error(
                            f"Error generating nudge email for app {app.id}: {e}"
                        )
                        draft_text = None

                    action_title = f"Follow-up required for {app.company.name if app.company else 'company'} ({app.position})"

                    # Create Action Item
                    action_item = ActionItemModel(
                        application_id=app.id,
                        title=action_title,
                        urgency="MEDIUM",
                        draft_email=draft_text,
                    )
                    session.add(action_item)

                await session.commit()
                logger.info(
                    f"Stale applications check completed. Processed {len(stale_apps)} items."
                )
        except Exception as e:
            logger.error(f"Error in monitor_stale_applications: {e}", exc_info=True)

        # Run every 24 hours
        await asyncio.sleep(24 * 60 * 60)
