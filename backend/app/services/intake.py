import logging
from datetime import datetime
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)
from app.models.staging import StagingItemModel
from app.schemas.intake import EmailPayload
from app.services.llm import extract_email_info
from app.services.task_tracker import task_tracker

logger = logging.getLogger(__name__)

MATCH_CONFIDENCE_THRESHOLD = 0.75  # Normalized 0.0 - 1.0


def parse_email_date(date_val: str | datetime | None) -> datetime | None:
    """Helper to convert string ISO timestamps to timezone-aware datetime instances."""
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))


async def is_email_already_processed(db: AsyncSession, message_id: str | None) -> bool:
    """Verifies whether an email has already been ingested into any event or staging table."""
    if not message_id:
        return False

    # Check across application events, non-application logs, and staging
    for model in [ApplicationEventModel, OtherEventModel, StagingItemModel]:
        stmt = select(model.id).where(model.email_message_id == message_id)
        if (await db.execute(stmt)).scalar_one_or_none():
            return True

    return False


async def calculate_best_match(
    db: AsyncSession, company_name: str, position_name: str
) -> tuple[CompanyModel | None, ApplicationModel | None, float]:
    """Calculates fuzzy matching score against existing companies and applications."""
    company_norm = company_name.strip().lower()
    position_norm = position_name.strip().lower()

    # Search for matching company
    stmt = select(CompanyModel)
    result = await db.execute(stmt)
    companies = result.scalars().all()

    best_company = None
    best_company_score = 0.0

    for company in companies:
        score = fuzz.ratio(company_norm, company.name_normalized) / 100.0
        if score > best_company_score:
            best_company_score = score
            best_company = company

    # If no confident company match, score defaults low
    if not best_company or best_company_score < MATCH_CONFIDENCE_THRESHOLD:
        return None, None, best_company_score

    # Search for matching application within the found company
    app_stmt = select(ApplicationModel).where(
        ApplicationModel.company_id == best_company.id
    )
    app_result = await db.execute(app_stmt)
    applications = app_result.scalars().all()

    best_app = None
    best_app_score = 0.0

    for app in applications:
        if app.position_normalized:
            score = fuzz.ratio(position_norm, app.position_normalized) / 100.0
            if score > best_app_score:
                best_app_score = score
                best_app = app

    # Combined confidence score calculation
    overall_score = (best_company_score + best_app_score) / 2.0 if best_app else best_company_score
    return best_company, best_app, overall_score


async def process_email_batch_sequential(
    db: AsyncSession,
    emails: list[EmailPayload],
    task_id: str,
) -> None:
    """Processes emails sequentially, checking for duplicates and routing low-confidence matches to staging."""
    for index, email in enumerate(emails, start=1):
        task_tracker.update_progress_before_item(
            task_id=task_id,
            current_index=index,
            subject=email.subject,
        )

        try:
            # Step 1: Duplicate Check
            if await is_email_already_processed(db, getattr(email, "message_id", None)):
                logger.info(f"Skipping duplicate email: '{email.subject}'")
                continue

            # Step 2: LLM Extraction
            extracted = await extract_email_info(db, email.body)
            received_at_dt = parse_email_date(email.received_at)

            # Step 3: Evaluate Company/Position Match
            if extracted.company and extracted.position:
                company, application, match_score = await calculate_best_match(
                    db, extracted.company, extracted.position
                )

                # Step 4: Staging Branch (Low confidence or new unconfirmed match)
                if match_score < MATCH_CONFIDENCE_THRESHOLD:
                    staging_item = StagingItemModel(
                        email_message_id=getattr(email, "message_id", None),
                        email_conversation_id=email.conversation_id,
                        email_sender=getattr(email, "sender", None),
                        email_subject=email.subject,
                        email_received_at=received_at_dt,
                        email_raw_body=email.body,
                        extracted_data=extracted.model_dump() if hasattr(extracted, "model_dump") else extracted.__dict__,
                        match_score=match_score,
                        match_reason="LOW_FUZZY_MATCH_CONFIDENCE",
                        status="PENDING",
                    )
                    db.add(staging_item)
                    await db.commit()

                    task_tracker.record_item_success(task_id=task_id, is_application=False)
                    continue

                # Step 5: High-Confidence Processing (Proceed to Direct Ingestion)
                if not company:
                    company = CompanyModel(
                        name=extracted.company,
                        name_normalized=extracted.company.strip().lower(),
                    )
                    db.add(company)
                    await db.flush()

                if not application:
                    application = ApplicationModel(
                        company_id=company.id,
                        position=extracted.position,
                        position_normalized=extracted.position.strip().lower(),
                        external_job_id=extracted.external_job_id,
                        job_url=extracted.job_url,
                        status=extracted.status or "APPLIED",
                    )
                    db.add(application)
                    await db.flush()
                elif extracted.status:
                    application.status = extracted.status

                event = ApplicationEventModel(
                    email_application_id=application.id,
                    email_message_id=getattr(email, "message_id", None),
                    email_conversation_id=email.conversation_id,
                    email_received_at=received_at_dt,
                    email_event_type=extracted.event_type or "UPDATED",
                    email_subject=email.subject,
                    email_summary=extracted.summary,
                    email_action_required=extracted.action_required or False,
                    email_action=extracted.action,
                    email_raw_body=email.body,
                )
                db.add(event)
                await db.commit()

                task_tracker.record_item_success(task_id=task_id, is_application=True)

            else:
                # Non-application log
                other_event = OtherEventModel(
                    email_message_id=getattr(email, "message_id", None),
                    email_conversation_id=email.conversation_id,
                    email_subject=email.subject,
                    email_received_at=received_at_dt,
                    email_type=extracted.email_type or "OTHER",
                    summary=extracted.summary,
                    action_required=extracted.action_required or False,
                    action=extracted.action,
                    raw_body=email.body,
                )
                db.add(other_event)
                await db.commit()

                task_tracker.record_item_success(task_id=task_id, is_application=False)

        except Exception as e:
            await db.rollback()
            error_msg = f"Failed processing email '{email.subject}': {str(e)}"
            logger.error(error_msg)
            task_tracker.record_item_failure(task_id=task_id, error_msg=error_msg)

    task_tracker.complete_task(task_id)