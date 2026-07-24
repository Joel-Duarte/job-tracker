import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)
from app.schemas.intake import EmailPayload
from app.services.llm import extract_email_info
from app.services.task_tracker import task_tracker

logger = logging.getLogger(__name__)


async def process_email_batch_sequential(
    db: AsyncSession,
    emails: list[EmailPayload],
    task_id: str,
) -> None:
    """Processes emails sequentially one by one inside the background task.
    Safely avoids all database race conditions and minimizes local LLM VRAM usage.
    """
    total = len(emails)

    for index, email in enumerate(emails, start=1):
        # Update progress before processing
        task_tracker.update_progress_before_item(
            task_id=task_id,
            current_index=index,
            subject=email.subject,
        )

        try:
            # 1. LLM Extraction
            extracted = await extract_email_info(db, email.body)

            # 2. Check if email belongs to an application
            if extracted.company and extracted.position:
                company_name_norm = extracted.company.strip().lower()

                # Find or create company safely
                stmt = select(CompanyModel).where(
                    CompanyModel.name_normalized == company_name_norm
                )
                result = await db.execute(stmt)
                company = result.scalar_one_or_none()

                if not company:
                    company = CompanyModel(
                        name=extracted.company,
                        name_normalized=company_name_norm,
                    )
                    db.add(company)
                    await db.flush()

                # Find or create application safely
                position_norm = extracted.position.strip().lower()
                app_stmt = select(ApplicationModel).where(
                    ApplicationModel.company_id == company.id,
                    ApplicationModel.position_normalized == position_norm,
                )
                app_result = await db.execute(app_stmt)
                application = app_result.scalar_one_or_none()

                if not application:
                    application = ApplicationModel(
                        company_id=company.id,
                        position=extracted.position,
                        position_normalized=position_norm,
                        external_job_id=extracted.external_job_id,
                        job_url=extracted.job_url,
                        status=extracted.status or "APPLIED",
                    )
                    db.add(application)
                    await db.flush()
                elif extracted.status:
                    application.status = extracted.status

                # Record event timeline entry
                event = ApplicationEventModel(
                    email_application_id=application.id,
                    email_conversation_id=email.conversation_id,
                    email_received_at=email.received_at,
                    email_event_type=extracted.event_type or "UPDATED",
                    subject=email.subject,
                    body_summary=extracted.summary,
                    action_required=extracted.action_required,
                    action=extracted.action,
                )
                db.add(event)
                await db.commit()

                # Update task tracker stats
                task_tracker.record_item_success(
                    task_id=task_id,
                    is_application=True,
                )

            else:
                # Log as non-application event
                other_event = OtherEventModel(
                    email_conversation_id=email.conversation_id,
                    email_received_at=email.received_at,
                    email_type=extracted.email_type or "OTHER",
                    subject=email.subject,
                    body_summary=extracted.summary,
                    action_required=extracted.action_required,
                    action=extracted.action,
                )
                db.add(other_event)
                await db.commit()

                task_tracker.record_item_success(
                    task_id=task_id,
                    is_application=False,
                )

        except Exception as e:
            await db.rollback()
            error_msg = f"Failed processing email '{email.subject}': {str(e)}"
            logger.error(error_msg)
            task_tracker.record_item_failure(
                task_id=task_id,
                error_msg=error_msg,
            )

    task_tracker.complete_task(task_id)