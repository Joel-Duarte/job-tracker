from unittest.mock import AsyncMock, patch

import pytest

from app.services.domain_resolver import (
    clean_domain,
    extract_domain_from_url,
    is_ats_hostname,
    resolve_company_domain,
)


def test_clean_domain():
    assert clean_domain("https://www.stripe.com/jobs?id=123") == "stripe.com"
    assert clean_domain("http://linear.app/") == "linear.app"
    assert clean_domain("  careers.airbnb.com:443/positions  ") == "careers.airbnb.com"
    assert clean_domain("invalid-domain-without-tld") is None
    assert clean_domain("") is None
    assert clean_domain(None) is None


def test_is_ats_hostname():
    assert is_ats_hostname("boards.greenhouse.io") is True
    assert is_ats_hostname("jobs.lever.co") is True
    assert is_ats_hostname("jobs.ashbyhq.com") is True
    assert is_ats_hostname("company.myworkdayjobs.com") is True
    assert is_ats_hostname("stripe.com") is False
    assert is_ats_hostname("linear.app") is False
    assert is_ats_hostname("careers.google.com") is False


def test_extract_domain_from_url():
    # ATS URLs must return None so we don't treat greenhouse.io as the company domain
    assert (
        extract_domain_from_url("https://boards.greenhouse.io/stripe/jobs/123") is None
    )
    assert extract_domain_from_url("https://jobs.lever.co/linear/456") is None
    assert extract_domain_from_url("https://jobs.ashbyhq.com/figma/789") is None

    # Direct company website URLs should extract clean root domains
    assert extract_domain_from_url("https://stripe.com/jobs/staff-eng") == "stripe.com"
    assert (
        extract_domain_from_url("https://careers.stripe.com/jobs/123") == "stripe.com"
    )
    assert extract_domain_from_url("https://jobs.airbnb.com/positions") == "airbnb.com"


@pytest.mark.asyncio
async def test_resolve_company_domain_known_overrides():
    assert await resolve_company_domain("Linear", allow_network=False) == "linear.app"
    assert (
        await resolve_company_domain("Datadog", allow_network=False) == "datadoghq.com"
    )
    assert await resolve_company_domain("Stripe", allow_network=False) == "stripe.com"
    assert await resolve_company_domain("Notion", allow_network=False) == "notion.so"


@pytest.mark.asyncio
async def test_resolve_company_domain_ats_with_ai_domain():
    # When posting URL is on Greenhouse, use AI-extracted domain
    domain = await resolve_company_domain(
        company_name="Acme Corp",
        source_url="https://boards.greenhouse.io/acme/jobs/101",
        ai_domain="acme-corp.io",
        allow_network=False,
    )
    assert domain == "acme-corp.io"


@pytest.mark.asyncio
async def test_resolve_company_domain_direct_url():
    domain = await resolve_company_domain(
        company_name="Custom Enterprise",
        source_url="https://careers.customenterprise.org/openings",
        ai_domain=None,
        allow_network=False,
    )
    assert domain == "customenterprise.org"


@pytest.mark.asyncio
async def test_resolve_company_domain_clearbit_fallback():
    with (
        patch(
            "app.services.domain_resolver.search_company_domain_and_about",
            new=AsyncMock(return_value=(None, None)),
        ),
        patch(
            "app.services.domain_resolver.query_clearbit_autocomplete",
            new=AsyncMock(return_value="segment.com"),
        ),
    ):
        domain = await resolve_company_domain(
            company_name="Segment",
            source_url=None,
            ai_domain=None,
            allow_network=True,
        )
        assert domain == "segment.com"


def test_clean_company_name():
    from app.services.domain_resolver import clean_company_name

    assert clean_company_name("Stripe, Inc.") == "Stripe"
    assert clean_company_name("Acme LLC") == "Acme"
    assert clean_company_name("Linear - Careers") == "Linear"
    assert clean_company_name("Datadog Jobs") == "Datadog"
    assert clean_company_name("  'Figma'  ") == "Figma"
    assert clean_company_name("TechCorp GmbH") == "TechCorp"
    assert clean_company_name(None) == ""


def test_extract_organization_from_ats_url():
    from app.services.domain_resolver import extract_organization_from_ats_url

    assert (
        extract_organization_from_ats_url(
            "https://boards.greenhouse.io/stripe/jobs/123"
        )
        == "stripe"
    )
    assert (
        extract_organization_from_ats_url("https://jobs.lever.co/linear/456")
        == "linear"
    )
    assert (
        extract_organization_from_ats_url("https://jobs.ashbyhq.com/figma/789")
        == "figma"
    )
    assert (
        extract_organization_from_ats_url("https://apply.workable.com/vercel/j/ABC/")
        == "vercel"
    )
    assert (
        extract_organization_from_ats_url("https://datadog.bamboohr.com/careers/10")
        == "datadog"
    )
    assert (
        extract_organization_from_ats_url("https://warp.rippling-ats.com/job/10")
        == "warp"
    )
    assert extract_organization_from_ats_url("https://stripe.com/jobs/123") is None


@pytest.mark.asyncio
async def test_resolve_company_domain_searches_and_ignores_hallucinated_ai():
    # ATS job with hallucinated ai_domain should search and return the authentic .com domain
    mock_search_results = [
        {
            "title": "LinkedIn: Jobs at Acme",
            "url": "https://www.linkedin.com/jobs/acme",
        },
        {"title": "Acme - Official Site", "url": "https://www.acme-corp.com/home"},
        {"title": "Acme About Page", "url": "https://www.acme-corp.com/about-us"},
    ]
    with patch(
        "app.services.web_search.search_web",
        new=AsyncMock(return_value=mock_search_results),
    ):
        domain = await resolve_company_domain(
            company_name="Acme Corp, Inc.",
            source_url="https://boards.greenhouse.io/acme/jobs/999",
            ai_domain="acme.ai",  # Hallucinated by LLM
            allow_network=True,
        )
        assert domain == "acme-corp.com"
