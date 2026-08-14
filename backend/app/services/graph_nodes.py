import logging
from datetime import datetime
from typing import Any
from langchain_core.runnables import RunnableConfig
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)
from app.models.staging import StagingItemModel
from app.schemas.graph_state import JobTrackerState
from app.services.llm import generate_and_save_application_embedding
import app.services.llm as llm_service

logger = logging.getLogger(__name__)


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
        raise ValueError("Database session 'db' must be provided in LangGraph config['configurable'].")
    return db


async def is_email_already_processed(db: AsyncSession, message_id: str | None) -> bool:
    if not message_id:
        return False
    for model in (ApplicationEventModel, OtherEventModel, StagingItemModel):
        stmt = select(model.id).where(model.email_message_id == message_id)
        if (await db.execute(stmt)).scalar_one_or_none():
            return True
    return False


async def normalize_and_dedupe_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
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
    extract_fn = getattr(intake_mod, "extract_email_info", llm_service.extract_email_info)

    extracted = await extract_fn(db, body)
    extracted_dict = extracted.model_dump() if hasattr(extracted, "model_dump") else extracted.__dict__

    is_app = bool(extracted_dict.get("company") and extracted_dict.get("position"))
    return {
        "extracted_data": extracted_dict,
        "is_application": is_app,
        "company_name": extracted_dict.get("company"),
        "position_name": extracted_dict.get("position"),
        "job_url": extracted_dict.get("job_url"),
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

    threshold = settings.STAGING_MATCH_THRESHOLD
    if not best_company or best_company_score < threshold:
        return {
            "match_score": best_company_score,
            "company_id": None,
            "application_id": None,
            "route": "staging",
        }

    # Match application under matched company
    app_stmt = select(ApplicationModel).where(ApplicationModel.company_id == best_company.id)
    app_res = await db.execute(app_stmt)
    applications = app_res.scalars().all()

    best_app = None
    best_app_score = 0.0
    for app in applications:
        if app.position_normalized:
            score = fuzz.ratio(position_norm, app.position_normalized) / 100.0
            if score > best_app_score:
                best_app_score = score
                best_app = app

    overall_score = best_app_score if best_app else 1.0
    return {
        "match_score": overall_score,
        "company_id": best_company.id,
        "application_id": best_app.id if best_app else None,
        "route": "staging" if overall_score < threshold else "commit",
    }


async def staging_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    received_at_dt = _parse_email_date(state.get("received_at"))

    staging_item = StagingItemModel(
        email_message_id=state.get("message_id"),
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

    return {"staging_item_id": staging_item.id, "route": "staging_done"}


async def scrape_enrich_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    job_url = state.get("job_url")
    if job_url:
        logger.info("External job URL detected: %s. Scrape hook triggered.", job_url)
    return {"scraped_spec": None}


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
    position = state.get("position_name") or extracted.get("position", "Unknown")
    status_val = extracted.get("status") or "APPLIED"

    if not application_id:
        application = ApplicationModel(
            company_id=company_id,
            position=position,
            position_normalized=position.strip().lower(),
            external_job_id=extracted.get("external_job_id"),
            job_url=extracted.get("job_url"),
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

    return {
        "company_id": company_id,
        "application_id": application_id,
        "event_id": event.id,
    }


async def summarize_embed_node(
    state: JobTrackerState, config: RunnableConfig
) -> dict[str, Any]:
    db = _get_db(config)
    application_id = state.get("application_id")

    if application_id:
        try:
            await generate_and_save_application_embedding(db, application_id)
            return {"embedding_created": True}
        except Exception as err:
            logger.warning("Embedding synthesis deferred for application %s: %s", application_id, err)

    return {"embedding_created": False}
