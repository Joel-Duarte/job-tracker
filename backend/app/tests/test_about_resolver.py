from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.about_resolver import (
    is_permissive_domain_match,
    resolve_company_about_url,
)


def test_is_permissive_domain_match():
    assert is_permissive_domain_match("https://linear.app/about", "linear.app") is True
    assert (
        is_permissive_domain_match("https://careers.linear.app/jobs", "linear.app")
        is True
    )
    assert is_permissive_domain_match("https://about.stripe.com", "stripe.com") is True
    assert (
        is_permissive_domain_match("https://malicious.com/linear.app", "linear.app")
        is False
    )
    assert (
        is_permissive_domain_match("https://notlinear.app/about", "linear.app") is False
    )
    assert is_permissive_domain_match("", "linear.app") is False
    assert is_permissive_domain_match("https://linear.app", "") is False


@pytest.mark.asyncio
async def test_resolve_company_about_url_from_homepage_html():
    html_content = """
    <html>
      <body>
        <nav>
          <a href="/">Home</a>
          <a href="/products">Products</a>
          <a href="/about-us">About Us</a>
          <a href="/contact">Contact</a>
        </nav>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.url = "https://acme.org"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        url = await resolve_company_about_url("acme.org")
        assert url == "https://acme.org/about-us"


@pytest.mark.asyncio
async def test_resolve_company_about_url_subdomain_priority():
    html_content = """
    <html>
      <body>
        <footer>
          <a href="https://about.netflix.com">About Netflix</a>
        </footer>
      </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.url = "https://netflix.com"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        url = await resolve_company_about_url("netflix.com")
        assert url == "https://about.netflix.com"


@pytest.mark.asyncio
async def test_resolve_company_about_url_fallback_to_search():
    # Homepage has no about links
    html_content = "<html><body><h1>Welcome</h1></body></html>"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = html_content
    mock_resp.url = "https://stealth-ai.com"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    mock_search_results = [
        {"title": "Stealth AI Careers", "url": "https://stealth-ai.com/careers"},
        {"title": "Our Story - Stealth AI", "url": "https://stealth-ai.com/our-story"},
    ]

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch(
            "app.services.web_search.search_web",
            new=AsyncMock(return_value=mock_search_results),
        ),
    ):
        url = await resolve_company_about_url("stealth-ai.com")
        assert url == "https://stealth-ai.com/our-story"


@pytest.mark.asyncio
async def test_resolve_company_about_url_default_fallback():
    # Both homepage and search fail
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Connection error")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch(
            "app.services.web_search.search_web",
            new=AsyncMock(return_value=[]),
        ),
    ):
        url = await resolve_company_about_url("custom-domain.io")
        assert url == "https://custom-domain.io/about"
