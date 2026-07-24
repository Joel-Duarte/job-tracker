import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas.intake import EmailPayload, EmailProcessingSummary
from app.services.llm import extract_email_info
from app.models.applications import (
    CompanyModel,
    ApplicationModel,
    ApplicationEventModel,
    OtherEventModel,
)

logger = logging.getLogger(__name__)


async def process_email_batch(
    db: AsyncSession, emails: list[EmailPayload]
) -> EmailProcessingSummary:
    """Processes a batch of emails sequentially/async, creating or updating applications and logging events."""
    summary = EmailProcessingSummary(
        total_received=len(emails),
        applications_updated=0,
        other_events_logged=0,
        failed_count=0,
        errors=[],
    )

    for email in emails:
        try:
            # 1. Extract structured metadata using the database prompt & LM Studio
            extracted = await extract_email_info(db, email.body)

            # 2. Check if the email belongs to an actual job application
            if extracted.company and extracted.position:
                # Normalize company name
                company_name_norm = extracted.company.strip().lower()

                # Find or create company
                stmt = select(CompanyModel).where(CompanyModel.name_normalized == company_name_norm)
                result = await db.execute(stmt)
                company = result.scalar_one_or_none()

                if not company:
                    company = CompanyModel(
                        name=extracted.company,
                        name_normalized=company_name_norm,
                    )
                    db.add(company)
                    await db.flush()

                # Find existing application or create a new one
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
                    # Update status if new status is present
                    application.status = extracted.status

                # Add application event entry
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
                summary.applications_updated += 1

            else:
                # Log as a non-job email (promotions, newsletter, unlinked communication)
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
                summary.other_events_logged += 1

            await db.commit()

        except Exception as e:
            await db.rollback()
            summary.failed_count += 1
            error_msg = f"Failed processing email '{email.subject}': {str(e)}"
            logger.error(error_msg)
            summary.errors.append(error_msg)

    return summary