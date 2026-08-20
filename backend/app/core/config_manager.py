import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
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

    async with AsyncSessionLocal() as session:
        return await _fetch_or_create(session)


async def load_settings(db: AsyncSession | None = None) -> dict[str, Any]:
    """Loads system settings as a dictionary."""
    try:
        model = await get_system_settings_model(db)
        return {
            "ENABLE_EMBEDDINGS": model.enable_embeddings,
            "AGENT_CHAT_RETENTION_DAYS": model.agent_chat_retention_days,
            "ENABLE_AUTO_COVER_LETTER": model.enable_auto_cover_letter,
            "COVER_LETTER_MATCH_THRESHOLD": model.cover_letter_match_threshold,
            "COVER_LETTER_LENGTH": getattr(model, "cover_letter_length", "standard")
            or "standard",
        }
    except Exception as e:
        logger.error(f"Failed to load global settings from DB: {e}")
        return {
            "ENABLE_EMBEDDINGS": True,
            "AGENT_CHAT_RETENTION_DAYS": 7,
            "ENABLE_AUTO_COVER_LETTER": False,
            "COVER_LETTER_MATCH_THRESHOLD": 70,
            "COVER_LETTER_LENGTH": "standard",
        }


async def save_settings(
    settings: dict[str, Any], db: AsyncSession | None = None
) -> None:
    """Saves system settings from a dictionary."""

    async def _update_settings(session: AsyncSession) -> None:
        model = await get_system_settings_model(session)
        if "ENABLE_EMBEDDINGS" in settings:
            model.enable_embeddings = bool(settings["ENABLE_EMBEDDINGS"])
        if "AGENT_CHAT_RETENTION_DAYS" in settings:
            model.agent_chat_retention_days = int(settings["AGENT_CHAT_RETENTION_DAYS"])
        if "ENABLE_AUTO_COVER_LETTER" in settings:
            model.enable_auto_cover_letter = bool(settings["ENABLE_AUTO_COVER_LETTER"])
        if "COVER_LETTER_MATCH_THRESHOLD" in settings:
            model.cover_letter_match_threshold = int(
                settings["COVER_LETTER_MATCH_THRESHOLD"]
            )
        if "COVER_LETTER_LENGTH" in settings:
            model.cover_letter_length = (
                str(settings["COVER_LETTER_LENGTH"]).strip().lower()
            )
        await session.commit()

    try:
        if db is not None:
            await _update_settings(db)
        else:
            async with AsyncSessionLocal() as session:
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
