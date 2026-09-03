from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.candidate_profile import CandidateCVModel
from app.services.agent_tools import (
    create_agent_tools,
    execute_get_candidate_profile,
)
from app.services.scraper import ScrapedJobContent
from app.services.web_search import fetch_webpage_content, search_web


@pytest.mark.asyncio
async def test_search_web_success():
    mock_results = [
        {
            "title": "Stripe Engineering Culture",
            "snippet": "Stripe focuses on developer velocity and reliable payment infrastructure.",
            "url": "https://stripe.com/jobs",
        }
    ]
    with patch("app.services.web_search._sync_ddgs_text", return_value=mock_results):
        res = await search_web("Stripe culture")
        assert len(res) == 1
        assert res[0]["title"] == "Stripe Engineering Culture"
        assert "developer velocity" in res[0]["snippet"]
        assert res[0]["url"] == "https://stripe.com/jobs"


@pytest.mark.asyncio
async def test_search_web_empty_query():
    res = await search_web("   ")
    assert res == []


@pytest.mark.asyncio
async def test_fetch_webpage_content_truncation():
    long_text = "A" * 5000
    mock_scraped = ScrapedJobContent(
        title="Engineering Blog",
        text=long_text,
        source_url="https://example.com/blog",
        scraped_via="camofox",
    )
    with patch(
        "app.services.web_search.scrape_job_url",
        new_callable=AsyncMock,
        return_value=mock_scraped,
    ):
        res = await fetch_webpage_content("https://example.com/blog", max_chars=1000)
        assert len(res) < 1100
        assert "... [Truncated for brevity]" in res


@pytest.mark.asyncio
async def test_get_candidate_profile_not_found():
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res

    res = await execute_get_candidate_profile(db)
    assert res["status"] == "not_found"


@pytest.mark.asyncio
async def test_get_candidate_profile_sections():
    db = AsyncMock()
    cv = CandidateCVModel(
        id=1,
        summary="Senior Distributed Systems Engineer with 8 years building Kafka pipelines.",
        years_of_experience=8.0,
        extracted_skills=["Python", "Go", "Kafka", "PostgreSQL", "Docker"],
        domain_expertise=["Fintech", "Distributed Systems"],
        spoken_languages=[{"language": "English", "proficiency": "Native"}],
        raw_text="Full resume raw text here...",
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = cv
    db.execute.return_value = mock_res

    # All section
    res_all = await execute_get_candidate_profile(db, section="all")
    assert res_all["years_of_experience"] == 8.0
    assert "Python" in res_all["extracted_skills"]
    assert "Fintech" in res_all["domain_expertise"]

    # Skills section
    res_skills = await execute_get_candidate_profile(db, section="skills")
    assert "extracted_skills" in res_skills
    assert "Kafka" in res_skills["extracted_skills"]
    assert "domain_expertise" not in res_skills

    # Raw CV section
    res_raw = await execute_get_candidate_profile(db, section="raw_cv")
    assert "Full resume raw text here..." in res_raw["cv_text"]


def test_create_agent_tools_dynamic_omission():
    db = AsyncMock()

    # 1. When web search is False: web search tools must be omitted
    tools_disabled = create_agent_tools(db, enable_web_search=False)
    tool_names_disabled = [t.name for t in tools_disabled]
    assert "get_candidate_profile" in tool_names_disabled
    assert "search_web" not in tool_names_disabled
    assert "fetch_webpage_content" not in tool_names_disabled

    # 2. When web search is True: web search tools must be present
    tools_enabled = create_agent_tools(db, enable_web_search=True)
    tool_names_enabled = [t.name for t in tools_enabled]
    assert "get_candidate_profile" in tool_names_enabled
    assert "search_web" in tool_names_enabled
    assert "fetch_webpage_content" in tool_names_enabled
