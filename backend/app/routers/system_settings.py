import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import load_settings, save_settings
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.schemas.global_settings import (
    SystemSettingsRead,
    SystemSettingsUpdate,
    TestSearchProviderRequest,
    TestSearchProviderResponse,
)
from app.services.web_search import validate_searxng_connection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/config/system",
    tags=["System Settings"],
    dependencies=[Depends(verify_admin_access)],
)


@router.get("", response_model=SystemSettingsRead)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
) -> SystemSettingsRead:
    settings = await load_settings(db)
    return SystemSettingsRead(
        has_completed_onboarding=settings.get("has_completed_onboarding", False),
        enable_email_intake=settings.get("enable_email_intake", False),
        enable_embeddings=settings.get("enable_embeddings", False),
        enable_web_search=settings.get("enable_web_search", False),
        enable_auto_cover_letter=settings.get("enable_auto_cover_letter", False),
        cover_letter_match_threshold=settings.get("cover_letter_match_threshold", 70),
        cover_letter_length=settings.get("cover_letter_length", "standard"),
        cover_letter_tone=settings.get("cover_letter_tone", "professional"),
        agent_chat_retention_days=settings.get("agent_chat_retention_days", 7),
        search_provider=settings.get("search_provider", "automatic"),
        searxng_url=settings.get("searxng_url", None),
    )


@router.patch("", response_model=SystemSettingsRead)
async def update_system_settings(
    payload: SystemSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> SystemSettingsRead:
    settings = await load_settings(db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            settings[key] = val
    await save_settings(settings, db)
    return SystemSettingsRead(
        has_completed_onboarding=settings.get("has_completed_onboarding", False),
        enable_email_intake=settings.get("enable_email_intake", False),
        enable_embeddings=settings.get("enable_embeddings", False),
        enable_web_search=settings.get("enable_web_search", False),
        enable_auto_cover_letter=settings.get("enable_auto_cover_letter", False),
        cover_letter_match_threshold=settings.get("cover_letter_match_threshold", 70),
        cover_letter_length=settings.get("cover_letter_length", "standard"),
        cover_letter_tone=settings.get("cover_letter_tone", "professional"),
        agent_chat_retention_days=settings.get("agent_chat_retention_days", 7),
        search_provider=settings.get("search_provider", "automatic"),
        searxng_url=settings.get("searxng_url", None),
    )


@router.post("/test-search-provider", response_model=TestSearchProviderResponse)
async def test_search_provider(
    payload: TestSearchProviderRequest,
) -> TestSearchProviderResponse:
    """Validates connectivity to a search provider (such as SearXNG) before saving settings."""
    provider = payload.provider.strip().lower()
    if provider == "ddgs":
        return TestSearchProviderResponse(
            success=True,
            provider="ddgs",
            message="DuckDuckGo (DDGS) search provider ready",
            latency_ms=0.0,
        )

    if provider in ("searxng", "automatic"):
        success, message, latency = await validate_searxng_connection(
            payload.searxng_url
        )
        return TestSearchProviderResponse(
            success=success,
            provider=provider,
            message=message,
            latency_ms=latency,
        )

    return TestSearchProviderResponse(
        success=False,
        provider=provider,
        message=f"Unknown search provider '{provider}'",
        latency_ms=0.0,
    )
