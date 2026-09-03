import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.core.database as db_module
from app.models.system_settings import SystemSettingsModel

logger = logging.getLogger(__name__)


async def get_system_settings_model(
    db: AsyncSession | None = None,
) -> SystemSettingsModel:
    """Fetches the singleton system settings model (id=1), creating it if it does not exist."""

    async def _fetch_or_create(session: AsyncSession) -> SystemSettingsModel:
        stmt = select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            record = SystemSettingsModel(
                id=1,
                has_completed_onboarding=False,
                enable_email_intake=True,
                enable_embeddings=False,
                agent_chat_retention_days=7,
                enable_auto_cover_letter=True,
                cover_letter_match_threshold=70,
                cover_letter_length="standard",
                cover_letter_tone="professional",
                enable_web_search=False,
                search_provider="automatic",
                searxng_url=None,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return record

    if db is not None:
        return await _fetch_or_create(db)

    async with db_module.AsyncSessionLocal() as session:
        return await _fetch_or_create(session)


async def load_settings(db: AsyncSession | None = None) -> dict[str, Any]:
    """Loads system settings as a dictionary with both canonical lower-case and upper-case keys."""
    try:
        model = await get_system_settings_model(db)
        has_completed_onboarding = getattr(model, "has_completed_onboarding", False)
        enable_email_intake = getattr(model, "enable_email_intake", False)
        enable_embeddings = getattr(model, "enable_embeddings", True)
        enable_web_search = getattr(model, "enable_web_search", False)
        agent_chat_retention_days = getattr(model, "agent_chat_retention_days", 7)
        enable_auto_cover_letter = getattr(model, "enable_auto_cover_letter", False)
        cover_letter_match_threshold = getattr(
            model, "cover_letter_match_threshold", 70
        )
        cover_letter_length = (
            getattr(model, "cover_letter_length", "standard") or "standard"
        )
        cover_letter_tone = (
            getattr(model, "cover_letter_tone", "professional") or "professional"
        )
        search_provider = getattr(model, "search_provider", "automatic") or "automatic"
        searxng_url = getattr(model, "searxng_url", None)

        return {
            "has_completed_onboarding": has_completed_onboarding,
            "enable_email_intake": enable_email_intake,
            "enable_embeddings": enable_embeddings,
            "enable_web_search": enable_web_search,
            "agent_chat_retention_days": agent_chat_retention_days,
            "enable_auto_cover_letter": enable_auto_cover_letter,
            "cover_letter_match_threshold": cover_letter_match_threshold,
            "cover_letter_length": cover_letter_length,
            "cover_letter_tone": cover_letter_tone,
            "search_provider": search_provider,
            "searxng_url": searxng_url,
            # Backward compatibility uppercase keys
            "HAS_COMPLETED_ONBOARDING": has_completed_onboarding,
            "ENABLE_EMAIL_INTAKE": enable_email_intake,
            "ENABLE_EMBEDDINGS": enable_embeddings,
            "ENABLE_WEB_SEARCH": enable_web_search,
            "AGENT_CHAT_RETENTION_DAYS": agent_chat_retention_days,
            "ENABLE_AUTO_COVER_LETTER": enable_auto_cover_letter,
            "COVER_LETTER_MATCH_THRESHOLD": cover_letter_match_threshold,
            "COVER_LETTER_LENGTH": cover_letter_length,
            "COVER_LETTER_TONE": cover_letter_tone,
            "SEARCH_PROVIDER": search_provider,
            "SEARXNG_URL": searxng_url,
        }
    except Exception as e:
        logger.error(f"Failed to load global settings from DB: {e}")
        return {
            "has_completed_onboarding": False,
            "enable_email_intake": True,
            "enable_embeddings": False,
            "enable_web_search": False,
            "agent_chat_retention_days": 7,
            "enable_auto_cover_letter": True,
            "cover_letter_match_threshold": 70,
            "cover_letter_length": "standard",
            "cover_letter_tone": "professional",
            "search_provider": "automatic",
            "searxng_url": None,
            "HAS_COMPLETED_ONBOARDING": False,
            "ENABLE_EMAIL_INTAKE": True,
            "ENABLE_EMBEDDINGS": False,
            "ENABLE_WEB_SEARCH": False,
            "AGENT_CHAT_RETENTION_DAYS": 7,
            "ENABLE_AUTO_COVER_LETTER": True,
            "COVER_LETTER_MATCH_THRESHOLD": 70,
            "COVER_LETTER_LENGTH": "standard",
            "COVER_LETTER_TONE": "professional",
            "SEARCH_PROVIDER": "automatic",
            "SEARXNG_URL": None,
        }


async def save_settings(
    settings: dict[str, Any], db: AsyncSession | None = None
) -> None:
    """Saves system settings from a dictionary supporting lower-case and upper-case keys."""

    async def _update_settings(session: AsyncSession) -> None:
        model = await get_system_settings_model(session)
        val_onboarding = (
            settings.get("has_completed_onboarding")
            if "has_completed_onboarding" in settings
            else settings.get("HAS_COMPLETED_ONBOARDING")
        )
        if val_onboarding is not None:
            model.has_completed_onboarding = bool(val_onboarding)

        val_email_intake = (
            settings.get("enable_email_intake")
            if "enable_email_intake" in settings
            else settings.get("ENABLE_EMAIL_INTAKE")
        )
        if val_email_intake is not None:
            model.enable_email_intake = bool(val_email_intake)

        val_embeddings = (
            settings.get("enable_embeddings")
            if "enable_embeddings" in settings
            else settings.get("ENABLE_EMBEDDINGS")
        )
        if val_embeddings is not None:
            model.enable_embeddings = bool(val_embeddings)

        val_web_search = (
            settings.get("enable_web_search")
            if "enable_web_search" in settings
            else settings.get("ENABLE_WEB_SEARCH")
        )
        if val_web_search is not None:
            model.enable_web_search = bool(val_web_search)

        val_retention = (
            settings.get("agent_chat_retention_days")
            if "agent_chat_retention_days" in settings
            else settings.get("AGENT_CHAT_RETENTION_DAYS")
        )
        if val_retention is not None:
            model.agent_chat_retention_days = int(val_retention)

        val_auto_cl = (
            settings.get("enable_auto_cover_letter")
            if "enable_auto_cover_letter" in settings
            else settings.get("ENABLE_AUTO_COVER_LETTER")
        )
        if val_auto_cl is not None:
            model.enable_auto_cover_letter = bool(val_auto_cl)

        val_threshold = (
            settings.get("cover_letter_match_threshold")
            if "cover_letter_match_threshold" in settings
            else settings.get("COVER_LETTER_MATCH_THRESHOLD")
        )
        if val_threshold is not None:
            model.cover_letter_match_threshold = int(val_threshold)

        val_length = (
            settings.get("cover_letter_length")
            if "cover_letter_length" in settings
            else settings.get("COVER_LETTER_LENGTH")
        )
        if val_length is not None:
            model.cover_letter_length = str(val_length).strip().lower()

        val_tone = (
            settings.get("cover_letter_tone")
            if "cover_letter_tone" in settings
            else settings.get("COVER_LETTER_TONE")
        )
        if val_tone is not None:
            model.cover_letter_tone = str(val_tone).strip().lower()

        val_search_provider = (
            settings.get("search_provider")
            if "search_provider" in settings
            else settings.get("SEARCH_PROVIDER")
        )
        if val_search_provider is not None:
            model.search_provider = str(val_search_provider).strip().lower()

        val_searxng_url = (
            settings.get("searxng_url")
            if "searxng_url" in settings
            else settings.get("SEARXNG_URL")
        )
        if "searxng_url" in settings or "SEARXNG_URL" in settings:
            model.searxng_url = (
                str(val_searxng_url).strip() if val_searxng_url else None
            )

        await session.commit()

    try:
        if db is not None:
            await _update_settings(db)
        else:
            async with db_module.AsyncSessionLocal() as session:
                await _update_settings(session)
    except Exception as e:
        logger.error(f"Failed to save global settings to DB: {e}")


async def get_setting(
    key: str, default: Any = None, db: AsyncSession | None = None
) -> Any:
    """Retrieves a specific system setting by key asynchronously."""
    settings = await load_settings(db)
    return settings.get(
        key, settings.get(key.lower(), settings.get(key.upper(), default))
    )


async def set_setting(key: str, value: Any, db: AsyncSession | None = None) -> None:
    """Sets a specific system setting by key asynchronously."""
    settings = await load_settings(db)
    settings[key] = value
    settings[key.lower()] = value
    settings[key.upper()] = value
    await save_settings(settings, db)
