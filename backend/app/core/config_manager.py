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
                enable_email_intake=False,
                enable_embeddings=True,
                agent_chat_retention_days=7,
                enable_auto_cover_letter=False,
                cover_letter_match_threshold=70,
                cover_letter_length="standard",
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
        agent_chat_retention_days = getattr(model, "agent_chat_retention_days", 7)
        enable_auto_cover_letter = getattr(model, "enable_auto_cover_letter", False)
        cover_letter_match_threshold = getattr(
            model, "cover_letter_match_threshold", 70
        )
        cover_letter_length = (
            getattr(model, "cover_letter_length", "standard") or "standard"
        )

        return {
            "has_completed_onboarding": has_completed_onboarding,
            "enable_email_intake": enable_email_intake,
            "enable_embeddings": enable_embeddings,
            "agent_chat_retention_days": agent_chat_retention_days,
            "enable_auto_cover_letter": enable_auto_cover_letter,
            "cover_letter_match_threshold": cover_letter_match_threshold,
            "cover_letter_length": cover_letter_length,
            # Backward compatibility uppercase keys
            "HAS_COMPLETED_ONBOARDING": has_completed_onboarding,
            "ENABLE_EMAIL_INTAKE": enable_email_intake,
            "ENABLE_EMBEDDINGS": enable_embeddings,
            "AGENT_CHAT_RETENTION_DAYS": agent_chat_retention_days,
            "ENABLE_AUTO_COVER_LETTER": enable_auto_cover_letter,
            "COVER_LETTER_MATCH_THRESHOLD": cover_letter_match_threshold,
            "COVER_LETTER_LENGTH": cover_letter_length,
        }
    except Exception as e:
        logger.error(f"Failed to load global settings from DB: {e}")
        return {
            "has_completed_onboarding": False,
            "enable_email_intake": True,
            "enable_embeddings": True,
            "agent_chat_retention_days": 7,
            "enable_auto_cover_letter": False,
            "cover_letter_match_threshold": 70,
            "cover_letter_length": "standard",
            "HAS_COMPLETED_ONBOARDING": False,
            "ENABLE_EMAIL_INTAKE": True,
            "ENABLE_EMBEDDINGS": True,
            "AGENT_CHAT_RETENTION_DAYS": 7,
            "ENABLE_AUTO_COVER_LETTER": False,
            "COVER_LETTER_MATCH_THRESHOLD": 70,
            "COVER_LETTER_LENGTH": "standard",
        }


async def save_settings(
    settings: dict[str, Any], db: AsyncSession | None = None
) -> None:
    """Saves system settings from a dictionary supporting lower-case and upper-case keys."""

    async def _update_settings(session: AsyncSession) -> None:
        model = await get_system_settings_model(session)
        if "has_completed_onboarding" in settings:
            model.has_completed_onboarding = bool(settings["has_completed_onboarding"])
        elif "HAS_COMPLETED_ONBOARDING" in settings:
            model.has_completed_onboarding = bool(settings["HAS_COMPLETED_ONBOARDING"])

        if "enable_email_intake" in settings:
            model.enable_email_intake = bool(settings["enable_email_intake"])
        elif "ENABLE_EMAIL_INTAKE" in settings:
            model.enable_email_intake = bool(settings["ENABLE_EMAIL_INTAKE"])

        if "enable_embeddings" in settings:
            model.enable_embeddings = bool(settings["enable_embeddings"])
        elif "ENABLE_EMBEDDINGS" in settings:
            model.enable_embeddings = bool(settings["ENABLE_EMBEDDINGS"])

        if "agent_chat_retention_days" in settings:
            model.agent_chat_retention_days = int(settings["agent_chat_retention_days"])
        elif "AGENT_CHAT_RETENTION_DAYS" in settings:
            model.agent_chat_retention_days = int(settings["AGENT_CHAT_RETENTION_DAYS"])

        if "enable_auto_cover_letter" in settings:
            model.enable_auto_cover_letter = bool(settings["enable_auto_cover_letter"])
        elif "ENABLE_AUTO_COVER_LETTER" in settings:
            model.enable_auto_cover_letter = bool(settings["ENABLE_AUTO_COVER_LETTER"])

        if "cover_letter_match_threshold" in settings:
            model.cover_letter_match_threshold = int(
                settings["cover_letter_match_threshold"]
            )
        elif "COVER_LETTER_MATCH_THRESHOLD" in settings:
            model.cover_letter_match_threshold = int(
                settings["COVER_LETTER_MATCH_THRESHOLD"]
            )

        if "cover_letter_length" in settings:
            model.cover_letter_length = (
                str(settings["cover_letter_length"]).strip().lower()
            )
        elif "COVER_LETTER_LENGTH" in settings:
            model.cover_letter_length = (
                str(settings["COVER_LETTER_LENGTH"]).strip().lower()
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
    return settings.get(key, default)


async def set_setting(key: str, value: Any, db: AsyncSession | None = None) -> None:
    """Sets a specific system setting by key asynchronously."""
    settings = await load_settings(db)
    settings[key] = value
    await save_settings(settings, db)
