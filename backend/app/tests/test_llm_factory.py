from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableLambda
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_factory import (
    _clean_base_url,
    _resolve_provider,
    get_active_llm_config_dict,
    get_chat_model,
    get_embeddings_model,
)
from app.core.prompts import seed_default_prompts
from app.models.llm import LLMConfigModel
from app.schemas.llm import (
    ApplicationSummaryResult,
    EmailExtractionResult,
    ExtractedJobSpec,
)
from app.services.llm import (
    extract_email_info,
    extract_job_spec,
    summarize_application_status,
)


def test_resolve_provider_and_clean_url():
    assert _resolve_provider("custom") == "openai"
    assert _resolve_provider("lmstudio") == "openai"
    assert _resolve_provider("anthropic") == "anthropic"
    assert _resolve_provider("gemini") == "google_genai"
    assert _resolve_provider(None) == "openai"

    assert (
        _clean_base_url("http://localhost:1234/v1/embeddings")
        == "http://localhost:1234/v1"
    )
    assert _clean_base_url("http://localhost:1234/v1/") == "http://localhost:1234/v1"
    assert _clean_base_url(None) is None


@pytest.mark.asyncio
async def test_get_active_llm_config_fallback():
    cfg = await get_active_llm_config_dict(None)
    assert cfg["source"] == ".env"
    assert cfg["provider_name"] == "openai"
    assert "model_name" in cfg


@pytest.mark.asyncio
async def test_get_active_llm_config_db(db_session: AsyncSession):
    custom_cfg = LLMConfigModel(
        provider_name="custom",
        api_base="http://192.168.1.187:1234/v1",
        api_key="test-key",
        model_name="qwen3.5-4b",
        embedding_model_name="nomic-embed-text-v2-moe",
        temperature=0.3,
        is_active=True,
    )
    db_session.add(custom_cfg)
    await db_session.commit()

    cfg = await get_active_llm_config_dict(db_session)
    assert cfg["source"] == "database"
    assert cfg["provider_name"] == "custom"
    assert cfg["model_name"] == "qwen3.5-4b"
    assert cfg["temperature"] == 0.3


@pytest.mark.asyncio
async def test_get_chat_model_and_embeddings_instantiation():
    chat_model = await get_chat_model()
    assert chat_model is not None

    embeddings_model = await get_embeddings_model()
    assert embeddings_model is not None


@pytest.mark.asyncio
async def test_extract_email_info_runnable(db_session: AsyncSession):
    await seed_default_prompts(db_session)

    mock_result = EmailExtractionResult(
        email_type="JOB_APPLICATION",
        company="Acme Corp",
        position="Python Engineer",
        external_job_id="REQ-123",
        job_url="https://acme.com/jobs/123",
        event_type="APPLICATION_CONFIRMATION",
        status="APPLIED",
        action_required=False,
        action=None,
        summary="Application received for Python Engineer.",
    )

    with patch("app.services.llm.get_task_chat_model") as mock_get_chat:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            AsyncMock(return_value=mock_result)
        )
        mock_get_chat.return_value = mock_llm

        res = await extract_email_info(
            db_session, "Thanks for applying to Acme Corp as Python Engineer."
        )
        assert res.company == "Acme Corp"
        assert res.position == "Python Engineer"
        assert res.status == "APPLIED"


@pytest.mark.asyncio
async def test_extract_job_spec_runnable(db_session: AsyncSession):
    await seed_default_prompts(db_session)

    mock_spec = ExtractedJobSpec(
        job_found=True,
        company="Stripe",
        position="Senior Staff Backend Engineer",
        location_work_type="San Francisco, CA (Hybrid)",
        salary_benefits="$220,000 - $280,000 + Equity",
        core_responsibilities="Lead architecture of real-time payment pipelines.",
        requirements_qualifications="10+ years experience, Distributed Systems, Python, Go.",
        ats_keywords=["Python", "Go", "Distributed Systems", "Kafka", "PostgreSQL"],
    )

    with patch("app.services.llm.get_task_chat_model") as mock_get_chat:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            AsyncMock(return_value=mock_spec)
        )
        mock_get_chat.return_value = mock_llm

        res = await extract_job_spec(
            db_session, "Stripe is hiring a Senior Staff Backend Engineer..."
        )
        assert res.job_found is True
        assert res.company == "Stripe"
        assert res.position == "Senior Staff Backend Engineer"
        assert "Kafka" in res.ats_keywords


@pytest.mark.asyncio
async def test_summarize_application_status_runnable(db_session: AsyncSession):
    await seed_default_prompts(db_session)

    mock_summary = ApplicationSummaryResult(
        snapshot="Applied on July 20. Interview scheduled for July 25.",
        current_stage="INTERVIEW",
        next_action="Prepare for interview",
    )

    with patch("app.services.llm.get_task_chat_model") as mock_get_chat:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            AsyncMock(return_value=mock_summary)
        )
        mock_get_chat.return_value = mock_llm

        timeline = [{"event_type": "INTERVIEW_INVITE", "date": "2026-07-25"}]
        res = await summarize_application_status(db_session, timeline)
        assert res.current_stage == "INTERVIEW"
        assert "Interview scheduled" in res.snapshot


@pytest.mark.asyncio
async def test_assess_job_posting_runnable(db_session: AsyncSession):
    await seed_default_prompts(db_session)

    from app.schemas.llm import (
        HardMatches,
        ImpactReframingItem,
        JobAssessmentResult,
        OptimizationGaps,
        ResumeTailoringStrategy,
        VocabularyTranslationItem,
    )
    from app.services.llm import assess_job_posting

    mock_assessment = JobAssessmentResult(
        company="Datadog",
        position="Staff Software Engineer",
        fit_score=88,
        programmatic_match_score=75,
        match_summary="Strong match across Python and distributed systems with minor terminology deltas.",
        hard_matches=HardMatches(
            keyword_match_rate="8/10 core skills found",
            top_alignment=["Python", "Distributed Systems", "PostgreSQL"],
        ),
        optimization_gaps=OptimizationGaps(
            missing_completely=["Rust"],
            vocabulary_mismatches=["Node -> Node.js"],
            experience_mismatch=None,
        ),
        tailoring_strategy=ResumeTailoringStrategy(
            vocabulary_translation=[
                VocabularyTranslationItem(
                    jd_term="PostgreSQL",
                    cv_term="Postgres",
                    replacement_guidance="Standardize to formal product name.",
                )
            ],
            impact_reframing=[
                ImpactReframingItem(
                    bullet_point="Maintained data pipelines.",
                    suggested_rewrite="Architected and scaled real-time data ingestion pipelines handling 50k req/sec.",
                    reason="Adds concrete throughput metrics and mirrors JD action verbs.",
                )
            ],
            structural_adjustments=[
                "Move distributed systems certifications to top of technical summary."
            ],
        ),
        matching_skills=["Python", "PostgreSQL", "Distributed Systems"],
        missing_skills=["Rust"],
        pros=["High impact role", "Modern tech stack"],
        cons=[],
        summary="High potential match.",
    )

    with patch("app.services.llm.get_task_chat_model") as mock_get_chat:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            AsyncMock(return_value=mock_assessment)
        )
        mock_get_chat.return_value = mock_llm

        res = await assess_job_posting(
            db_session,
            job_description="Datadog is looking for a Staff Software Engineer...",
            candidate_skills=["Python", "Postgres", "Distributed Systems"],
            candidate_cv="Candidate CV text with Python and Postgres experience.",
            programmatic_baseline=75,
        )

        assert res.fit_score == 88
        assert res.programmatic_match_score == 75
        assert res.hard_matches.keyword_match_rate == "8/10 core skills found"
        assert len(res.tailoring_strategy.vocabulary_translation) == 1
        assert "Job Match Analysis" in res.markdown_report
