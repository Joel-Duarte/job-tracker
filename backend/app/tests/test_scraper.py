import json
from unittest.mock import patch

import httpx
import pytest

from app.services.scraper import (
    ScrapedJobContent,
    _scrape_via_camofox,
    _scrape_via_http_fallback,
    clean_extracted_text,
    has_job_content_keywords,
    scrape_job_url,
    validate_job_content,
    validate_target_url,
)


def test_validate_job_content_multi_language():
    # English
    en_text = "We are seeking a Senior Developer. Requirements: Python and SQL. Responsibilities include system architecture."
    assert validate_job_content(en_text, min_matches=2) is True

    # German
    de_text = "Wir suchen einen Entwickler. Anforderungen: Erfahrung mit Python. Aufgaben: Entwicklung von Backend-Systemen."
    assert validate_job_content(de_text, min_matches=2) is True

    # French
    fr_text = "Nous recherchons un ingénieur. Exigences: expérience en Python. Qualifications requises pour le poste."
    assert validate_job_content(fr_text, min_matches=2) is True

    # Spanish
    es_text = "Buscamos un desarrollador. Requisitos: experiencia comprobable. Responsabilidades del puesto."
    assert validate_job_content(es_text, min_matches=2) is True

    # Portuguese
    pt_text = "Procuramos um desenvolvedor. Requisitos: experiência prévia. Responsabilidades do cargo."
    assert validate_job_content(pt_text, min_matches=2) is True

    # Italian
    it_text = "Cerciamo uno sviluppatore. Requisiti: esperienza con Python. Mansioni e responsabilità."
    assert validate_job_content(it_text, min_matches=2) is True

    # Polish
    pl_text = "Poszukujemy programisty. Wymagania: doświadczenie w Pythonie. Obowiązki na stanowisku."
    assert validate_job_content(pl_text, min_matches=2) is True

    # Swedish
    se_text = "Vi söker en utvecklare. Krav: erfarenhet av Python. Ansvar och arbetsuppgifter."
    assert validate_job_content(se_text, min_matches=2) is True

    # Non-job / Invalid
    invalid_text = "Welcome to our homepage! Read our blog posts and company news here."
    assert validate_job_content(invalid_text, min_matches=2) is False

    # Empty string
    assert validate_job_content("", min_matches=2) is False

    # Test backward compatibility alias
    assert has_job_content_keywords(en_text, min_matches=2) is True
    assert has_job_content_keywords(invalid_text, min_matches=2) is False


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
    fake_eval_payload = json.dumps(
        {
            "title": "Senior Python Engineer at Stripe",
            "text": "Job Description:\nWe are hiring a Senior Python Engineer to work on core payment systems.",
        }
    )

    with (
        patch("httpx.AsyncClient.post") as mock_post,
        patch("httpx.AsyncClient.delete") as mock_delete,
    ):
        # Mock /tabs/open
        open_resp = httpx.Response(200, json={"ok": True, "tabId": "tab-1234"})
        # Mock /tabs/tab-1234/evaluate
        expand_resp = httpx.Response(200, json={"ok": True, "result": "true"})
        eval_resp = httpx.Response(200, json={"ok": True, "result": fake_eval_payload})
        mock_post.side_effect = [open_resp, expand_resp, eval_resp]

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
    with (
        patch("httpx.AsyncClient.post") as mock_post,
        patch("app.services.scraper._scrape_via_http_fallback") as mock_http,
    ):
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
            text="Valid description with more than 100 characters to pass the length check. "
            * 3,
            source_url="https://company.com/jobs/1",
            scraped_via="camofox",
        )

        result = await scrape_job_url("company.com/jobs/1")
        assert result.source_url == "https://company.com/jobs/1"


def test_validate_target_url_ssrf_protection():
    # Valid public URLs
    assert validate_target_url("https://example.com/job") == "https://example.com/job"
    assert validate_target_url("http://google.com") == "http://google.com"

    # Private / loopback targets must be blocked
    invalid_targets = [
        "http://localhost:8000",
        "http://127.0.0.1/admin",
        "http://0.0.0.0:80",
        "http://10.0.0.1/secret",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/file",
        "file:///etc/passwd",
    ]
    for target in invalid_targets:
        with pytest.raises(ValueError):
            validate_target_url(target)


@pytest.mark.asyncio
async def test_scrape_job_url_ssrf_target_returns_failed():
    result = await scrape_job_url("http://127.0.0.1:8000/internal")
    assert result.scraped_via == "failed"
    assert result.text == ""
