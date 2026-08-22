import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.runnables import RunnableConfig
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified

import app.services.llm as llm_service
from app.core.config_manager import get_setting
from app.core.url_utils import normalize_job_url
from app.models.applications import (
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
    try:
        return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
    except Exception:
        return None


def _get_db(config: RunnableConfig) -> AsyncSession:
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    db = configurable.get("db")
    if db is None:
        raise ValueError(
            "Database session 'db' must be provided in LangGraph config['configurable']."
        )
    return db


async def _upsert_processed_email(
    db: AsyncSession,
    message_id: str | None,
    status: str,
    subject: str | None = None,
) -> None:
    """Write a record to processed_email_ids. Silently ignores duplicate inserts."""
    if not message_id:
        return
    try:
        db.add(
            ProcessedEmailModel(
                message_id=message_id,
                status=status,
                subject=(subject or "")[:500] if subject else None,
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.debug(
            "processed_email_ids: insert skipped (likely duplicate) for message_id=%s",
            message_id,
        )


async def is_email_already_processed(db: AsyncSession, message_id: str | None) -> bool:
    """Checks whether an email has already been processed using the unified ProcessedEmailModel table,
    with fallback to legacy event tables for existing/historical records."""
    if not message_id:
        return False
    stmt = select(ProcessedEmailModel.id).where(
        ProcessedEmailModel.message_id == message_id
    )
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        return True

    for model in (ApplicationEventModel, OtherEventModel, StagingItemModel):
        stmt = select(model.id).where(model.email_message_id == message_id)
        if (await db.execute(stmt)).scalar_one_or_none():
            return True
    return False


async def normalize_and_dedupe_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    """Pre-LLM dedup: checks the unified processed_email_ids table."""
    db = _get_db(config)
    message_id = state.get("message_id")

    if await is_email_already_processed(db, message_id):
        logger.info("Duplicate email detected for message_id=%s, skipping.", message_id)
        return {"is_duplicate": True, "route": "skip"}

    return {
        "is_duplicate": False,
        "subject": state.get("subject", "").strip(),
        "body": state.get("body", "").strip(),
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
    pos_clean = None if (not pos or pos == "unknownPosition") else pos
    comp = extracted_dict.get("company")

    raw_job_url = extracted_dict.get("job_url")
    clean_job_url = normalize_job_url(raw_job_url) if raw_job_url else None

    is_app = (email_type == "JOB_APPLICATION") or bool(comp and pos_clean)
    return {
        "extracted_data": extracted_dict,
        "is_application": is_app,
        "company_name": comp,
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
        # No company extracted -> cannot match or create reliably, send to staging
        return {
            "match_score": 0.0,
            "company_id": None,
            "application_id": None,
            "route": "staging",
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
        }

    # Match application under matched company
    app_stmt = select(ApplicationModel).where(
        ApplicationModel.company_id == best_company.id
    )
    app_res = await db.execute(app_stmt)
    applications = app_res.scalars().all()

    # Case 1: Exactly 1 application exists for this company -> auto-link directly
    if len(applications) == 1:
        return {
            "match_score": 1.0,
            "company_id": best_company.id,
            "application_id": applications[0].id,
            "route": "commit",
        }

    # Case 2: Multiple applications exist for this company -> disambiguate by position name
    if len(applications) > 1:
        if not position_norm:
            # Ambiguous: multiple applications exist but position is missing from email
            return {
                "match_score": best_company_score,
                "company_id": best_company.id,
                "application_id": None,
                "route": "staging",
            }

        best_app = None
        best_app_score = 0.0
        for app in applications:
            if app.position_normalized:
                score = fuzz.ratio(position_norm, app.position_normalized) / 100.0
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
            # Ambiguous: position didn't match any existing application closely
            return {
                "match_score": best_app_score,
                "company_id": best_company.id,
                "application_id": None,
                "route": "staging",
            }

    # Case 3: 0 applications exist for this company
    return {
        "match_score": 1.0,
        "company_id": best_company.id,
        "application_id": None,
        "route": "commit",
    }


async def staging_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    received_at_dt = _parse_email_date(state.get("received_at"))
    message_id = state.get("message_id")

    staging_item = StagingItemModel(
        email_message_id=message_id,
        email_conversation_id=state.get("conversation_id"),
        email_sender=state.get("sender"),
        email_subject=state.get("subject", ""),
        email_received_at=received_at_dt,
        email_raw_body=state.get("body", ""),
        extracted_data=state.get("extracted_data"),
        match_score=state.get("match_score", 0.0),
        match_reason="LOW_FUZZY_MATCH_CONFIDENCE",
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
        other_event = OtherEventModel(
            email_message_id=state.get("message_id"),
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
        raw_job_url = extracted.get("job_url") or state.get("job_url")
        application = ApplicationModel(
            company_id=company_id,
            position=position,
            position_normalized=position.strip().lower(),
            external_job_id=extracted.get("external_job_id"),
            job_url=normalize_job_url(raw_job_url) if raw_job_url else None,
            status=status_val,
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

    event = ApplicationEventModel(
        email_application_id=application_id,
        email_message_id=state.get("message_id"),
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
