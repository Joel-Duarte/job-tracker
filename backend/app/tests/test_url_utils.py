from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.url_utils import normalize_job_url
from app.schemas.llm import JobAssessmentResult
from app.services.job_saver import persist_or_stage_job_assessment


def test_normalize_job_url_preserves_full_url():
    url = (
        "https://jobs.lever.co/acme/12345"
        "?utm_source=linkedin&utm_medium=cpc&ref=friend#apply"
    )
    normalized = normalize_job_url(url)
    assert normalized == url


def test_normalize_job_url_strips_whitespace():
    url = "   https://example.com/careers/software-engineer?id=123   "
    normalized = normalize_job_url(url)
    assert normalized == "https://example.com/careers/software-engineer?id=123"


def test_normalize_job_url_preserves_job_identifiers():
    gh_url = (
        "https://boards.greenhouse.io/stripe/jobs/123?gh_jid=12345&utm_source=twitter"
    )
    assert normalize_job_url(gh_url) == gh_url

    jobid_url = "https://careers.company.com/view?jobId=8899&ref=123"
    assert normalize_job_url(jobid_url) == jobid_url

    indeed_url = "https://www.indeed.com/viewjob?jk=abc12345&from=serp"
    assert normalize_job_url(indeed_url) == indeed_url


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

    mock_company = MagicMock()
    mock_company.id = 10
    mock_company.name = "TestCorp"
    mock_company.domain = "testcorp.com"

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_company

    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    added_models = []
    mock_db.add = MagicMock(side_effect=lambda obj: added_models.append(obj))

    res = await persist_or_stage_job_assessment(
        db=mock_db,
        assessment=assessment,
        raw_text="Job description",
        job_url=url_raw,
    )

    assert res["status"] == "success"
    assert res["is_duplicate"] is False

    # Verify that added ApplicationModel and JobPostingModel received the normalized URL
    app_added = next((m for m in added_models if hasattr(m, "company_id")), None)
    jp_added = next(
        (m for m in added_models if hasattr(m, "description_markdown")), None
    )

    assert app_added is not None
    assert app_added.job_url == url_raw
    assert jp_added is not None
    assert jp_added.job_url == url_raw


class AsyncSessionMock:
    pass
