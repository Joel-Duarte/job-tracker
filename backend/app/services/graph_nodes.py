import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.runnables import RunnableConfig
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified

import app.services.llm as llm_service
from app.core.config_manager import get_setting
from app.core.html_utils import clean_html_text
from app.core.url_utils import normalize_job_url
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.processed_email import ProcessedEmailModel
from app.models.staging import StagingItemModel
from app.schemas.graph_state import JobTrackerState

generate_and_save_application_embedding = (
    llm_service.generate_and_save_application_embedding
)

logger = logging.getLogger(__name__)
STAGING_MATCH_THRESHOLD = 0.75


def _parse_email_date(date_val: str | datetime | None) -> datetime | None:
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str):
        try:
            return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(UTC)
    return None


async def _upsert_processed_email(
    db: AsyncSession,
    message_id: str | None,
    status: str,
    subject: str | None = None,
    account_id: int | None = None,
) -> None:
    if not message_id:
        return
    stmt = select(ProcessedEmailModel).where(
        ProcessedEmailModel.message_id == message_id
    )
    res = await db.execute(stmt)
    record = res.scalar_one_or_none()
    if record:
        record.status = status
        record.subject = subject or record.subject
        if account_id is not None:
            record.account_id = account_id
    else:
        record = ProcessedEmailModel(
            message_id=message_id,
            subject=subject,
            status=status,
            account_id=account_id,
        )
        db.add(record)
    await db.commit()


async def is_email_already_processed(db: AsyncSession, message_id: str | None) -> bool:
    """Checks whether an email has already been processed using the unified ProcessedEmailModel table."""
    if not message_id:
        return False
    stmt = select(ProcessedEmailModel.id).where(
        ProcessedEmailModel.message_id == message_id
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


def _get_db(config: RunnableConfig) -> AsyncSession:
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    db = configurable.get("db")
    if db is None:
        raise ValueError(
            "Database session 'db' must be provided in LangGraph config['configurable']."
        )
    return db


async def normalize_and_dedupe_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    """Pre-LLM dedup: checks the unified processed_email_ids table and strips HTML tags."""
    db = _get_db(config)
    message_id = state.get("message_id")

    if await is_email_already_processed(db, message_id):
        logger.info("Duplicate email detected for message_id=%s, skipping.", message_id)
        return {"is_duplicate": True, "route": "skip"}

    cleaned_body = clean_html_text(state.get("body", ""))

    return {
        "is_duplicate": False,
        "subject": state.get("subject", "").strip(),
        "body": cleaned_body,
    }


async def extraction_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    body = state.get("body", "")

    # Resolve extract_email_info dynamically so module mocks in tests are respected
    import app.services.intake as intake_mod

    extract_fn = getattr(
        intake_mod, "extract_email_info", llm_service.extract_email_info
    )

    try:
        extracted = await extract_fn(
            db,
            body,
            sender=state.get("sender"),
            subject=state.get("subject"),
            date=str(state.get("received_at")) if state.get("received_at") else None,
        )
    except TypeError:
        # Fallback for mock callables that only accept (db, body)
        extracted = await extract_fn(db, body)

    extracted_dict = (
        extracted.model_dump()
        if hasattr(extracted, "model_dump")
        else extracted.__dict__
    )

    email_type = str(extracted_dict.get("email_type") or "").upper()
    pos = extracted_dict.get("position")
    pos_clean = (
        None
        if (
            not pos
            or pos.strip().lower() in ["unknownposition", "unknown", "none", "null"]
        )
        else pos.strip()
    )
    comp = extracted_dict.get("company")
    comp_clean = (
        None
        if (
            not comp
            or comp.strip().lower()
            in ["none", "null", "unknown", "n/a", "not specified"]
        )
        else comp.strip()
    )

    raw_job_url = extracted_dict.get("job_url")
    clean_job_url = normalize_job_url(raw_job_url) if raw_job_url else None

    # Recruitment communication includes:
    # 1. Any email typed as JOB_APPLICATION or RECRUITER_OUTREACH
    # 2. Any email with a company or position extracted
    # 3. Any email with a recruitment event_type or status
    is_recruitment_type = email_type in ["JOB_APPLICATION", "RECRUITER_OUTREACH"]
    has_company_or_position = bool(comp_clean or pos_clean)
    has_recruitment_event = bool(
        extracted_dict.get("event_type")
        and str(extracted_dict.get("event_type")).upper()
        not in ["OTHER", "NONE", "NULL", ""]
    ) or bool(
        extracted_dict.get("status")
        and str(extracted_dict.get("status")).upper()
        not in ["OTHER", "NONE", "NULL", ""]
    )

    is_app = (
        is_recruitment_type
        or (has_company_or_position and email_type not in ["NEWSLETTER", "SPAM"])
        or has_recruitment_event
    )

    return {
        "extracted_data": extracted_dict,
        "is_application": is_app,
        "company_name": comp_clean,
        "position_name": pos_clean,
        "job_url": clean_job_url,
        "route": "match" if is_app else "other_event",
    }


async def fuzzy_match_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    company_name = state.get("company_name", "")
    position_name = state.get("position_name", "")

    company_norm = company_name.strip().lower() if company_name else ""
    position_norm = position_name.strip().lower() if position_name else ""

    if not company_norm:
        # No company extracted -> route to staging for user to assign company
        return {
            "match_score": 0.0,
            "company_id": None,
            "application_id": None,
            "route": "staging",
            "match_reason": "MISSING_COMPANY_NAME",
        }

    stmt = select(CompanyModel)
    res = await db.execute(stmt)
    companies = res.scalars().all()

    if not companies:
        # First company in DB: direct match with score 1.0
        return {
            "match_score": 1.0,
            "company_id": None,
            "application_id": None,
            "route": "commit",
        }

    best_company = None
    best_company_score = 0.0
    for comp in companies:
        score = fuzz.ratio(company_norm, comp.name_normalized) / 100.0
        if score > best_company_score:
            best_company_score = score
            best_company = comp

    threshold = STAGING_MATCH_THRESHOLD
    if not best_company or best_company_score < threshold:
        return {
            "match_score": best_company_score,
            "company_id": None,
            "application_id": None,
            "route": "staging",
            "match_reason": "NEW_COMPANY_LEAD",
        }

    extracted = state.get("extracted_data") or {}
    raw_status = str(extracted.get("status") or "APPLIED").upper()
    is_initial_application = raw_status in ["APPLIED", "IN_PROGRESS", "ASSESSMENT"]

    # Match application under matched company
    app_stmt = select(ApplicationModel).where(
        ApplicationModel.company_id == best_company.id
    )
    app_res = await db.execute(app_stmt)
    applications = app_res.scalars().all()

    ACTIVE_STATUSES = {"APPLIED", "ONLINE_ASSESSMENT", "TECHNICAL_INTERVIEW", "OFFER"}
    active_apps = [a for a in applications if a.status in ACTIVE_STATUSES]
    terminal_apps = [a for a in applications if a.status not in ACTIVE_STATUSES]

    # Case 1: Exactly 1 Active Application exists
    if len(active_apps) == 1:
        target_app = active_apps[0]
        if not position_norm:
            return {
                "match_score": 1.0,
                "company_id": best_company.id,
                "application_id": target_app.id,
                "route": "commit",
            }

        pos_score = 0.0
        if target_app.position_normalized:
            if position_norm == target_app.position_normalized:
                pos_score = 1.0
            else:
                pos_score = (
                    fuzz.ratio(position_norm, target_app.position_normalized) / 100.0
                )

        if pos_score >= threshold:
            return {
                "match_score": pos_score,
                "company_id": best_company.id,
                "application_id": target_app.id,
                "route": "commit",
            }
        else:
            return {
                "match_score": pos_score,
                "company_id": best_company.id,
                "application_id": None,
                "route": "staging",
                "match_reason": "DIFFERENT_POSITION_NEW_LEAD"
                if is_initial_application
                else "UNMATCHED_STATUS_UPDATE",
            }

    # Case 2: Multiple Active Applications exist
    if len(active_apps) > 1:
        if not position_norm:
            return {
                "match_score": best_company_score,
                "company_id": best_company.id,
                "application_id": None,
                "route": "staging",
                "match_reason": "AMBIGUOUS_MULTIPLE_APPLICATIONS",
            }

        best_app = None
        best_app_score = 0.0
        for app in active_apps:
            if app.position_normalized:
                score = (
                    1.0
                    if position_norm == app.position_normalized
                    else fuzz.ratio(position_norm, app.position_normalized) / 100.0
                )
                if score > best_app_score:
                    best_app_score = score
                    best_app = app

        if best_app and best_app_score >= threshold:
            return {
                "match_score": best_app_score,
                "company_id": best_company.id,
                "application_id": best_app.id,
                "route": "commit",
            }
        else:
            return {
                "match_score": best_app_score,
                "company_id": best_company.id,
                "application_id": None,
                "route": "staging",
                "match_reason": "AMBIGUOUS_MULTIPLE_APPLICATIONS",
            }

    # Case 3: Only Terminal Applications exist — Re-Application or Historical Concluded sync scenario
    if len(terminal_apps) > 0:
        best_term_app = None
        best_term_score = 0.0
        for app in terminal_apps:
            if not position_norm:
                best_term_app = app
                best_term_score = 1.0
                break
            if app.position_normalized:
                score = (
                    1.0
                    if position_norm == app.position_normalized
                    else fuzz.ratio(position_norm, app.position_normalized) / 100.0
                )
                if score > best_term_score:
                    best_term_score = score
                    best_term_app = app

        if best_term_app and best_term_score >= threshold:
            email_dt = _parse_email_date(state.get("received_at"))
            term_date = best_term_app.updated_at or best_term_app.created_at
            if email_dt and term_date:
                email_utc = (
                    email_dt if email_dt.tzinfo else email_dt.replace(tzinfo=UTC)
                )
                term_utc = (
                    term_date if term_date.tzinfo else term_date.replace(tzinfo=UTC)
                )
                if email_utc <= term_utc + timedelta(days=7):
                    # Historical sync / past event for this concluded application
                    return {
                        "match_score": best_term_score,
                        "company_id": best_company.id,
                        "application_id": best_term_app.id,
                        "route": "commit",
                    }

        return {
            "match_score": best_company_score,
            "company_id": best_company.id,
            "application_id": None,
            "route": "staging",
            "match_reason": "REAPPLICATION_PREVIOUSLY_CONCLUDED"
            if is_initial_application
            else "UNMATCHED_STATUS_UPDATE",
        }

    # Case 4: 0 Applications exist for Company
    if is_initial_application:
        return {
            "match_score": 1.0,
            "company_id": best_company.id,
            "application_id": None,
            "route": "commit",
        }
    else:
        return {
            "match_score": 1.0,
            "company_id": best_company.id,
            "application_id": None,
            "route": "staging",
            "match_reason": "UNMATCHED_STATUS_UPDATE",
        }


async def staging_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    received_at_dt = _parse_email_date(state.get("received_at"))
    message_id = state.get("message_id")

    if message_id:
        existing_stmt = select(StagingItemModel).where(
            StagingItemModel.email_message_id == message_id
        )
        existing_res = await db.execute(existing_stmt)
        existing_item = existing_res.scalar_one_or_none()
        if existing_item:
            existing_item.extracted_data = (
                state.get("extracted_data") or existing_item.extracted_data
            )
            existing_item.match_score = state.get(
                "match_score", existing_item.match_score
            )
            existing_item.match_reason = (
                state.get("match_reason") or existing_item.match_reason
            )
            existing_item.email_raw_body = state.get(
                "body", existing_item.email_raw_body
            )
            await db.commit()
            await db.refresh(existing_item)
            await _upsert_processed_email(
                db, message_id, "staged", state.get("subject")
            )
            return {"staging_item_id": existing_item.id, "route": "staging_done"}

    staging_item = StagingItemModel(
        email_message_id=message_id,
        email_conversation_id=state.get("conversation_id"),
        email_sender=state.get("sender"),
        email_subject=state.get("subject", ""),
        email_received_at=received_at_dt,
        email_raw_body=state.get("body", ""),
        extracted_data=state.get("extracted_data"),
        match_score=state.get("match_score", 0.0),
        match_reason=state.get("match_reason") or "LOW_FUZZY_MATCH_CONFIDENCE",
        status="PENDING",
    )
    db.add(staging_item)
    await db.commit()
    await db.refresh(staging_item)

    # Mark as staged in unified dedup table
    await _upsert_processed_email(db, message_id, "staged", state.get("subject"))

    return {"staging_item_id": staging_item.id, "route": "staging_done"}


async def scrape_enrich_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    job_url = normalize_job_url(state.get("job_url"))
    scraped_text = None
    if job_url:
        logger.info("External job URL detected: %s. Scrape hook triggered.", job_url)
        try:
            from app.services.scraper import scrape_job_url

            scraped = await scrape_job_url(job_url)
            if scraped.text:
                scraped_text = scraped.text
        except Exception as err:
            logger.warning(
                "Scrape enrich node encountered error for %s: %s", job_url, err
            )
    return {"scraped_spec": scraped_text}


async def db_commit_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    received_at_dt = _parse_email_date(state.get("received_at"))
    extracted = state.get("extracted_data") or {}

    if not state.get("is_application"):
        msg_id = state.get("message_id")
        if msg_id:
            existing_other = (
                await db.execute(
                    select(OtherEventModel).where(
                        OtherEventModel.email_message_id == msg_id
                    )
                )
            ).scalar_one_or_none()
            if existing_other:
                await _upsert_processed_email(
                    db, msg_id, "other_event", state.get("subject")
                )
                return {"event_id": existing_other.id, "application_id": None}

        other_event = OtherEventModel(
            email_message_id=msg_id,
            email_conversation_id=state.get("conversation_id"),
            email_subject=state.get("subject", ""),
            email_received_at=received_at_dt,
            email_type=extracted.get("email_type") or "OTHER",
            summary=extracted.get("summary", ""),
            action_required=extracted.get("action_required", False),
            action=extracted.get("action"),
            raw_body=state.get("body", ""),
        )
        db.add(other_event)
        await db.commit()
        await db.refresh(other_event)
        return {"event_id": other_event.id, "application_id": None}

    # High-confidence application processing
    company_id = state.get("company_id")
    company_name = state.get("company_name") or extracted.get("company", "Unknown")

    if not company_id:
        company = CompanyModel(
            name=company_name,
            name_normalized=company_name.strip().lower(),
        )
        db.add(company)
        await db.flush()
        company_id = company.id

    application_id = state.get("application_id")
    pos_raw = state.get("position_name") or extracted.get("position")
    position = (
        "Applicant / Open Role"
        if (not pos_raw or pos_raw == "unknownPosition")
        else pos_raw
    )

    raw_status = str(extracted.get("status") or "APPLIED").upper()
    stage_mapping = {
        "APPLIED": "APPLIED",
        "RECRUITER_CONTACT": "TECHNICAL_INTERVIEW",
        "PHONE_SCREEN": "TECHNICAL_INTERVIEW",
        "ONLINE_ASSESSMENT": "TECHNICAL_INTERVIEW",
        "TECHNICAL_INTERVIEW": "TECHNICAL_INTERVIEW",
        "BEHAVIORAL_INTERVIEW": "TECHNICAL_INTERVIEW",
        "ONSITE_INTERVIEW": "TECHNICAL_INTERVIEW",
        "FINAL_INTERVIEW": "TECHNICAL_INTERVIEW",
        "INTERVIEW": "TECHNICAL_INTERVIEW",
        "OFFER": "OFFER",
        "OFFER_RECEIVED": "OFFER",
        "REJECTED": "REJECTED",
        "REJECTION_RECEIVED": "REJECTED",
        "WITHDRAWN": "REJECTED",
        "ASSESSMENT": "ASSESSMENT",
    }
    status_val = stage_mapping.get(raw_status, "APPLIED")

    if not application_id:
        if status_val not in ["APPLIED", "IN_PROGRESS", "ASSESSMENT"]:
            logger.warning(
                "Preventing automatic creation of ApplicationModel in status %s without matching application.",
                status_val,
            )
            return await staging_node(
                dict(state, match_reason="UNMATCHED_STATUS_UPDATE"), config
            )

        raw_job_url = extracted.get("job_url") or state.get("job_url")
        application = ApplicationModel(
            company_id=company_id,
            position=position,
            position_normalized=position.strip().lower(),
            external_job_id=extracted.get("external_job_id"),
            job_url=normalize_job_url(raw_job_url) if raw_job_url else None,
            status=status_val,
            application_date=(
                received_at_dt.date() if received_at_dt else datetime.now(UTC).date()
            ),
            last_activity_at=received_at_dt or datetime.now(UTC),
        )
        db.add(application)
        await db.flush()
        application_id = application.id
    else:
        app_stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
        app_res = await db.execute(app_stmt)
        application = app_res.scalar_one()
        if status_val:
            application.status = status_val
        if received_at_dt:
            application.last_activity_at = received_at_dt

    msg_id = state.get("message_id")
    if msg_id:
        existing_app_ev = (
            await db.execute(
                select(ApplicationEventModel).where(
                    ApplicationEventModel.email_message_id == msg_id
                )
            )
        ).scalar_one_or_none()
        if existing_app_ev:
            await _upsert_processed_email(
                db, msg_id, "application_event", state.get("subject")
            )
            return {"event_id": existing_app_ev.id, "application_id": application_id}

    event = ApplicationEventModel(
        email_application_id=application_id,
        email_message_id=msg_id,
        email_conversation_id=state.get("conversation_id"),
        email_received_at=received_at_dt,
        email_event_type=extracted.get("event_type") or "UPDATED",
        email_subject=state.get("subject", ""),
        email_summary=extracted.get("summary", ""),
        email_action_required=extracted.get("action_required", False),
        email_action=extracted.get("action"),
        email_raw_body=state.get("body", ""),
    )
    db.add(event)
    await db.flush()

    # Automatically create pending ActionItemModel if action is required
    if extracted.get("action_required") and extracted.get("action"):
        action_text = str(extracted.get("action")).strip()
        if action_text:
            raw_due = extracted.get("due_date")
            parsed_due = _parse_email_date(raw_due) if raw_due else None

            if parsed_due:
                now_utc = datetime.now(UTC)
                due_dt = (
                    parsed_due if parsed_due.tzinfo else parsed_due.replace(tzinfo=UTC)
                )
                diff = (due_dt - now_utc).total_seconds()
                if diff <= 48 * 3600:
                    urgency = "HIGH"
                elif diff <= 7 * 24 * 3600:
                    urgency = "MEDIUM"
                else:
                    urgency = "LOW"
            else:
                act_lower = action_text.lower()
                urgency = (
                    "HIGH"
                    if any(
                        k in act_lower
                        for k in [
                            "interview",
                            "assessment",
                            "urgent",
                            "deadline",
                            "schedule",
                            "offer",
                            "today",
                            "tomorrow",
                            "expir",
                        ]
                    )
                    else "MEDIUM"
                )
            action_item = ActionItemModel(
                application_id=application_id,
                event_id=event.id,
                title=action_text[:500],
                urgency=urgency,
                due_date=parsed_due,
                status="PENDING",
            )
            db.add(action_item)

    await db.commit()
    await db.refresh(event)

    # Mark as ingested (or not_a_job) in unified dedup table
    status_label = "ingested" if state.get("is_application") else "not_a_job"
    await _upsert_processed_email(
        db,
        state.get("message_id"),
        status_label,
        state.get("subject"),
    )

    return {
        "company_id": company_id,
        "application_id": application_id,
        "event_id": event.id,
    }


async def summarize_embed_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    # Vector embeddings are deferred during raw intake workflows and generated strictly during application lifecycle management events.
    return {"embedding_created": False, "reason": "deferred_intake"}


async def cover_letter_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    application_id = state.get("application_id")

    if not application_id:
        return {"cover_letter_status": "SKIPPED"}

    enable_auto = await get_setting("ENABLE_AUTO_COVER_LETTER", False, db=db)
    threshold = await get_setting("COVER_LETTER_MATCH_THRESHOLD", 70, db=db)

    raw_score = state.get("match_score") or 0.0
    score_pct = raw_score * 100.0 if (0.0 <= raw_score <= 1.0) else raw_score

    # Query application record
    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
        )
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    application = res.scalar_one_or_none()

    if not application:
        return {"cover_letter_status": "SKIPPED"}

    # If match_score wasn't provided or was 0, check application.match_analysis_payload fit_score
    if raw_score == 0.0 and application.match_analysis_payload:
        payload_score = application.match_analysis_payload.get(
            "fit_score"
        ) or application.match_analysis_payload.get("overall_fit_score")
        if payload_score is not None:
            try:
                fit_val = float(payload_score)
                score_pct = fit_val * 100.0 if (0.0 <= fit_val <= 1.0) else fit_val
            except (ValueError, TypeError):
                pass

    if enable_auto and score_pct >= threshold:
        # Fetch active candidate CV
        cv_stmt = (
            select(CandidateCVModel)
            .where(CandidateCVModel.is_active.is_(True))
            .limit(1)
        )
        cv_res = await db.execute(cv_stmt)
        active_cv = cv_res.scalars().first()
        if not active_cv:
            cv_stmt_fallback = select(CandidateCVModel).limit(1)
            cv_res_fallback = await db.execute(cv_stmt_fallback)
            active_cv = cv_res_fallback.scalars().first()

        cv_text = (active_cv.anonymized_text or active_cv.raw_text) if active_cv else ""

        company_name = (
            application.company.name
            if application.company
            else (state.get("company_name") or "")
        )
        position_name = application.position or state.get("position_name") or ""
        job_desc = (
            application.job_posting.description_markdown
            if application.job_posting and application.job_posting.description_markdown
            else (state.get("scraped_spec") or state.get("body") or "")
        )

        try:
            letter_text = await llm_service.generate_cover_letter(
                db,
                company_name=company_name,
                position=position_name,
                job_description=job_desc,
                candidate_cv=cv_text,
            )
            application.cover_letter_text = letter_text
            application.cover_letter_status = "GENERATED"
            application.cover_letter_generated_at = datetime.now(UTC)
            await db.commit()
            cl_status = "GENERATED"
        except Exception as err:
            logger.error(
                "Failed to generate cover letter for application %s: %s",
                application_id,
                err,
                exc_info=True,
            )
            application.cover_letter_status = "FAILED"
            await db.commit()
            cl_status = "FAILED"
    else:
        application.cover_letter_status = "SKIPPED"
        await db.commit()
        cl_status = "SKIPPED"

    # Update corresponding IntakeEvaluationTaskModel task if present
    task_id_input = state.get("task_id")
    if task_id_input:
        task_stmt = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.id == task_id_input
        )
        task_res = await db.execute(task_stmt)
        task_record = task_res.scalar_one_or_none()
        if task_record:
            task_record.status = "COMPLETED"
            task_record.stage = "COMPLETE"
            res_payload = dict(task_record.result_json or {})
            res_payload["cover_letter_status"] = cl_status
            if cl_status == "GENERATED":
                res_payload["cover_letter_note"] = (
                    "Cover letter generated successfully."
                )
            elif cl_status == "FAILED":
                res_payload["cover_letter_note"] = (
                    "Cover letter generation failed during pipeline execution."
                )
            else:
                res_payload["cover_letter_note"] = (
                    f"Cover letter generation skipped (auto_enabled={enable_auto}, "
                    f"score={score_pct:.1f}%, threshold={threshold}%)"
                )
            task_record.result_json = res_payload
            flag_modified(task_record, "result_json")
            await db.commit()

    return {"cover_letter_status": cl_status}
