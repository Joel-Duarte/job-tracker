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
    with patch(
        "app.services.domain_resolver.query_clearbit_autocomplete",
        new=AsyncMock(return_value="segment.com"),
    ):
        domain = await resolve_company_domain(
            company_name="Segment",
            source_url=None,
            ai_domain=None,
            allow_network=True,
        )
        assert domain == "segment.com"
