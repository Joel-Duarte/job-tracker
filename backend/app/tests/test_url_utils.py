from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.url_utils import normalize_job_url
from app.schemas.llm import JobAssessmentResult
from app.services.job_saver import persist_or_stage_job_assessment


def test_normalize_job_url_strips_tracking_params():
    url_with_tracking = (
        "https://jobs.lever.co/acme/12345"
        "?utm_source=linkedin&utm_medium=cpc&utm_campaign=hiring&ref=friend&source=indeed"
    )
    normalized = normalize_job_url(url_with_tracking)
    assert normalized == "https://jobs.lever.co/acme/12345"


def test_normalize_job_url_strips_google_fb_ms_click_ids():
    url = "https://example.com/careers/software-engineer?gclid=XYZ123&fbclid=ABC456&msclkid=789&ref_id=referral123"
    normalized = normalize_job_url(url)
    assert normalized == "https://example.com/careers/software-engineer"


def test_normalize_job_url_preserves_job_identifiers():
    # GreenHouse gh_jid should be kept
    gh_url = (
        "https://boards.greenhouse.io/stripe/jobs/123?gh_jid=12345&utm_source=twitter"
    )
    assert (
        normalize_job_url(gh_url)
        == "https://boards.greenhouse.io/stripe/jobs/123?gh_jid=12345"
    )

    # jobId should be kept
    jobid_url = "https://careers.company.com/view?jobId=8899&ref=123"
    assert normalize_job_url(jobid_url) == "https://careers.company.com/view?jobId=8899"

    # Indeed jk parameter should be kept
    indeed_url = "https://www.indeed.com/viewjob?jk=abc12345&from=serp"
    assert normalize_job_url(indeed_url) == "https://www.indeed.com/viewjob?jk=abc12345"


def test_normalize_job_url_scheme_domain_trailing_slash_fragment():
    # Prepend missing scheme and remove trailing slash
    assert (
        normalize_job_url("company.com/careers/backend/")
        == "https://company.com/careers/backend"
    )

    # Lowercase scheme/host and strip fragment
    assert (
        normalize_job_url("HTTP://EXAMPLE.COM/jobs/123/#section-apply")
        == "http://example.com/jobs/123"
    )

    # Preserve root slash
    assert normalize_job_url("https://company.com/") == "https://company.com/"


def test_normalize_job_url_sorts_query_params():
    url = "https://company.com/jobs/search?z_param=1&a_param=2"
    assert (
        normalize_job_url(url) == "https://company.com/jobs/search?a_param=2&z_param=1"
    )


def test_normalize_job_url_edge_cases():
    assert normalize_job_url(None) is None
    assert normalize_job_url("") is None
    assert normalize_job_url("   ") is None
    assert normalize_job_url("lead-1234abcd") == "lead-1234abcd"
    assert normalize_job_url("app-5678") == "app-5678"
    assert normalize_job_url("clip-xyz99") == "clip-xyz99"


@pytest.mark.asyncio
async def test_persist_or_stage_job_assessment_uses_normalized_url():
    """Unit test using mock AsyncSession to verify persist_or_stage_job_assessment uses normalized URL."""
    mock_db = AsyncSessionMock()

    assessment = JobAssessmentResult(
        company="TestCorp",
        position="Backend Engineer",
        fit_score=90,
        summary="Matches skills.",
    )

    url_raw = "https://testcorp.com/jobs/456?utm_source=newsletter&ref=ref123#apply"

    # Mock duplicate search query result (existing application found)
    mock_existing_app = MagicMock()
    mock_existing_app.id = 42

    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_existing_app

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalars

    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    res = await persist_or_stage_job_assessment(
        db=mock_db,
        assessment=assessment,
        raw_text="Job description",
        job_url=url_raw,
    )

    assert res["status"] == "staged"
    assert res["is_duplicate"] is True
    assert res["existing_application_id"] == 42


class AsyncSessionMock:
    pass
