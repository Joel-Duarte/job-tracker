from unittest.mock import AsyncMock, patch

import pytest

from app.services.web_search import (
    resolve_search_provider_settings,
    search_web,
    validate_searxng_connection,
)


@pytest.mark.asyncio
async def test_resolve_search_provider_settings_auto_without_url():
    with patch(
        "app.core.config_manager.load_settings",
        new=AsyncMock(
            return_value={"search_provider": "automatic", "searxng_url": None}
        ),
    ):
        provider, url = await resolve_search_provider_settings()
        assert provider == "ddgs"
        assert url is None


@pytest.mark.asyncio
async def test_resolve_search_provider_settings_auto_with_url():
    with patch(
        "app.core.config_manager.load_settings",
        new=AsyncMock(
            return_value={
                "search_provider": "automatic",
                "searxng_url": "http://localhost:8080",
            }
        ),
    ):
        provider, url = await resolve_search_provider_settings()
        assert provider == "searxng"
        assert url == "http://localhost:8080"


@pytest.mark.asyncio
async def test_validate_searxng_connection_empty_url():
    success, msg, latency = await validate_searxng_connection("")
    assert success is False
    assert "empty" in msg.lower()


@pytest.mark.asyncio
async def test_search_web_searxng_fallback_to_ddgs():
    with (
        patch(
            "app.services.web_search.resolve_search_provider_settings",
            new=AsyncMock(return_value=("searxng", "http://unreachable:8080")),
        ),
        patch(
            "app.services.web_search._query_searxng",
            side_effect=Exception("Connection refused"),
        ),
        patch(
            "app.services.web_search._sync_ddgs_text",
            return_value=[
                {
                    "title": "DDGS Result",
                    "url": "https://example.com",
                    "snippet": "Test",
                }
            ],
        ),
    ):
        results = await search_web("test query")
        assert len(results) == 1
        assert results[0]["title"] == "DDGS Result"
