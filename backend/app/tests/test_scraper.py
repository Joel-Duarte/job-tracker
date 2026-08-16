import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.services.scraper import (
    clean_extracted_text,
    scrape_job_url,
    _scrape_via_camofox,
    _scrape_via_http_fallback,
    ScrapedJobContent,
)


def test_clean_extracted_text():
    raw = """
    Software Engineer - Backend
    
    
    About Us:
    We are a leading tech company.
    
    
    Requirements:
    - Python 3.12+
    - FastAPI & PostgreSQL
    """
    cleaned = clean_extracted_text(raw)
    assert "Software Engineer - Backend" in cleaned
    assert "Requirements:" in cleaned
    assert "Python 3.12+" in cleaned
    # Ensure no triple newlines
    assert "\n\n\n" not in cleaned


@pytest.mark.asyncio
async def test_scrape_via_camofox_success():
    fake_eval_payload = json.dumps({
        "title": "Senior Python Engineer at Stripe",
        "text": "Job Description:\nWe are hiring a Senior Python Engineer to work on core payment systems."
    })

    with patch("httpx.AsyncClient.post") as mock_post, patch("httpx.AsyncClient.delete") as mock_delete:
        # Mock /tabs/open
        open_resp = httpx.Response(200, json={"ok": True, "tabId": "tab-1234"})
        # Mock /tabs/tab-1234/evaluate
        eval_resp = httpx.Response(200, json={"ok": True, "result": fake_eval_payload})
        mock_post.side_effect = [open_resp, eval_resp]

        # Mock DELETE /tabs/tab-1234
        mock_delete.return_value = httpx.Response(200, json={"ok": True})

        result = await _scrape_via_camofox("https://jobs.stripe.com/123")

        assert result is not None
        assert result.title == "Senior Python Engineer at Stripe"
        assert "Senior Python Engineer" in result.text
        assert result.scraped_via == "camofox"
        assert result.source_url == "https://jobs.stripe.com/123"

        # Verify tab was closed
        mock_delete.assert_called_once()


@pytest.mark.asyncio
async def test_scrape_via_camofox_tab_open_failure_triggers_fallback():
    with patch("httpx.AsyncClient.post") as mock_post, patch("app.services.scraper._scrape_via_http_fallback") as mock_http:
        # Mock Camofox failure
        mock_post.return_value = httpx.Response(500, text="Internal Server Error")
        
        # Mock HTTP fallback
        mock_http.return_value = ScrapedJobContent(
            title="Frontend Developer",
            text="Frontend Developer role description",
            source_url="https://example.com/job/456",
            scraped_via="http_fallback",
        )

        result = await scrape_job_url("https://example.com/job/456")

        assert result.scraped_via == "http_fallback"
        assert result.title == "Frontend Developer"
        assert "Frontend Developer" in result.text


@pytest.mark.asyncio
async def test_scrape_via_http_fallback():
    html_sample = """
    <!DOCTYPE html>
    <html>
    <head><title>Staff Platform Engineer - Acme Corp</title></head>
    <body>
        <nav><a href="/">Home</a></nav>
        <script>console.log("analytics");</script>
        <main class="job-description">
            <h1>Staff Platform Engineer</h1>
            <p>Acme Corp is seeking an experienced Platform Engineer.</p>
            <ul>
                <li>Kubernetes</li>
                <li>Go / Python</li>
            </ul>
        </main>
        <footer>Copyright 2026 Acme Corp</footer>
    </body>
    </html>
    """
    with patch("httpx.AsyncClient.get") as mock_get:
        req = httpx.Request("GET", "https://acme.com/jobs/staff-eng")
        mock_get.return_value = httpx.Response(200, text=html_sample, request=req)

        result = await _scrape_via_http_fallback("https://acme.com/jobs/staff-eng")

        assert result.scraped_via == "http_fallback"
        assert result.title == "Staff Platform Engineer - Acme Corp"
        assert "Staff Platform Engineer" in result.text
        assert "Kubernetes" in result.text
        assert "console.log" not in result.text
        assert "analytics" not in result.text


@pytest.mark.asyncio
async def test_scrape_job_url_normalizes_url_scheme():
    with patch("app.services.scraper._scrape_via_camofox") as mock_camofox:
        mock_camofox.return_value = ScrapedJobContent(
            title="DevOps Engineer",
            text="Valid description with more than 100 characters to pass the length check. " * 3,
            source_url="https://company.com/jobs/1",
            scraped_via="camofox",
        )

        result = await scrape_job_url("company.com/jobs/1")
        assert result.source_url == "https://company.com/jobs/1"
