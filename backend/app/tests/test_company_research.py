from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.applications import CompanyModel
from app.services.company_research import (
    _collect_company_evidence,
    build_company_research_query,
    research_company_context,
)
from app.services.llm import generate_cover_letter


def test_build_company_research_query():
    # Anchored domain
    q1 = build_company_research_query("Stripe", "stripe.com")
    assert '"Stripe"' in q1
    assert '"stripe.com"' in q1

    # Generic ATS host domain should not be used as anchor
    q2 = build_company_research_query("Acme Corp", "boards.greenhouse.io")
    assert '"Acme Corp"' in q2
    assert "greenhouse.io" not in q2
    assert "company mission values" in q2


@pytest.mark.asyncio
async def test_collect_company_evidence_uses_categories_and_deduplicates():
    result = {
        "title": "Company page",
        "snippet": "Useful evidence",
        "url": "https://example.com/page#section",
    }
    with patch(
        "app.services.company_research.search_web",
        new_callable=AsyncMock,
        return_value=[result] * 5,
    ) as search_mock:
        evidence = await _collect_company_evidence("Acme", "acme.com", None)

    assert search_mock.await_count == 6
    assert all(call.kwargs["max_results"] == 5 for call in search_mock.await_args_list)
    assert len(evidence) == 1
    assert evidence[0]["category"] == "identity"
    assert evidence[0]["url"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_research_company_context_cached():
    db = AsyncMock()
    cached_data = {
        "summary": "Financial infrastructure for the internet.",
        "engineering_culture": "API-first, high developer velocity.",
        "recent_initiatives": "Stripe Agentic Toolkit",
        "sources": ["https://stripe.com"],
    }
    company = CompanyModel(
        id=1,
        name="Stripe",
        name_normalized="stripe",
        domain="stripe.com",
        company_research=cached_data,
    )
    db.get.return_value = company

    # Without force_refresh -> returns cached
    res = await research_company_context(
        "Stripe", company_id=1, db=db, force_refresh=False
    )
    assert res == cached_data


@pytest.mark.asyncio
async def test_research_company_context_web_disabled():
    db = AsyncMock()
    company = CompanyModel(
        id=1,
        name="Linear",
        name_normalized="linear",
        domain="linear.app",
        company_research=None,
    )
    db.get.return_value = company

    with patch(
        "app.services.company_research.get_setting",
        new_callable=AsyncMock,
        return_value=False,
    ):
        res = await research_company_context("Linear", company_id=1, db=db)
        assert res == {}


@pytest.mark.asyncio
async def test_research_company_context_synthesis():
    db = AsyncMock()
    company = CompanyModel(
        id=1,
        name="Linear",
        name_normalized="linear",
        domain="linear.app",
        company_research=None,
    )
    db.get.return_value = company

    mock_snippets = [
        {
            "title": "Linear - Issue Tracking",
            "snippet": "Linear is a purpose-built tool for planning and building products.",
            "url": "https://linear.app/about",
        }
    ]

    mock_ai_response = MagicMock()
    mock_ai_response.content = (
        '{"summary": "Issue tracking for high-performance software teams.", '
        '"engineering_culture": "Keyboard-driven, fast sync engine.", '
        '"recent_initiatives": "Linear Asks", '
        '"public_rating_snippet": "4.8 on Glassdoor", '
        '"sources": ["https://linear.app/about"]}'
    )
    mock_chat_model = AsyncMock()
    mock_chat_model.ainvoke.return_value = mock_ai_response

    with (
        patch(
            "app.services.company_research.get_setting",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.services.company_research.search_web",
            new_callable=AsyncMock,
            return_value=mock_snippets,
        ),
        patch(
            "app.services.company_research.get_task_chat_model",
            new_callable=AsyncMock,
            return_value=mock_chat_model,
        ),
    ):
        res = await research_company_context(
            "Linear", company_id=1, db=db, force_refresh=True
        )
        assert res["summary"] == "Issue tracking for high-performance software teams."
        assert "Keyboard-driven" in res["engineering_culture"]
        assert company.company_research == res


@pytest.mark.asyncio
async def test_generate_cover_letter_injects_company_research():
    db = AsyncMock()
    research = {
        "summary": "Payment platform processing billions.",
        "engineering_culture": "Distributed systems, Ruby & Go.",
        "recent_initiatives": "Agentic commerce API",
    }

    from langchain_core.runnables import RunnableLambda

    mock_response = MagicMock()
    mock_response.content = "Dear Hiring Manager at Stripe, I am excited..."
    mock_llm_fn = AsyncMock(return_value=mock_response)
    mock_llm = RunnableLambda(mock_llm_fn)

    with (
        patch(
            "app.services.llm.get_task_chat_model",
            new_callable=AsyncMock,
            return_value=mock_llm,
        ),
        patch(
            "app.services.llm.get_prompt_template",
            new_callable=AsyncMock,
            return_value="Target Company: {company_name}\n{custom_instructions}",
        ),
    ):
        result = await generate_cover_letter(
            db=db,
            company_name="Stripe",
            position="Staff Engineer",
            job_description="Lead payment pipelines.",
            candidate_cv="8 years building Kafka and distributed APIs.",
            company_research=research,
        )
        assert "Dear Hiring Manager" in result
        call_args = mock_llm_fn.call_args[0][0]
        human_msg = str(call_args)
        assert "Verified Company Intelligence" in human_msg
        assert "Payment platform processing billions" in human_msg


def test_build_application_company_context_filters_low_value_research():
    from app.services.llm import build_application_company_context

    context = build_application_company_context(
        {
            "summary": "Builds payment infrastructure for online businesses.",
            "employee_signals": [{"signal": "Long interview loop"}],
            "public_rating_snippet": "4.2 on Glassdoor",
            "candidate_alignment_angles": ["Strong fit"],
            "verified_facts": [
                {"fact": "Launched a new API", "confidence": "high"},
                {"fact": "Unverified expansion", "confidence": "low"},
            ],
        }
    )

    assert "Builds payment infrastructure" in context
    assert "Launched a new API" in context
    assert "Long interview loop" not in context
    assert "4.2 on Glassdoor" not in context
    assert "Strong fit" not in context
    assert "Unverified expansion" not in context
