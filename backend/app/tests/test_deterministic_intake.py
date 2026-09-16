from unittest.mock import MagicMock, patch

import pytest
from langchain_core.runnables import RunnableLambda
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.llm import HardMatches, JobAssessmentResult, ResumeTailoringStrategy
from app.services.llm import assess_job_posting
from app.services.matcher import compute_programmatic_skill_match


def test_compute_programmatic_skill_match_deterministic():
    """Verify that calling compute_programmatic_skill_match multiple times produces identical results."""
    candidate_skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]
    jd_text = """
    We are looking for a Senior Backend Engineer with deep experience in Python, FastAPI, and PostgreSQL.
    Experience with Kubernetes, AWS, and Kafka is a plus. Docker is required.
    """

    first_run = compute_programmatic_skill_match(candidate_skills, jd_text)
    assert first_run["programmatic_score"] is not None
    assert first_run["matched_count"] > 0
    assert len(first_run["matching_skills"]) == first_run["matched_count"]

    # Run 10 times to assert 100% determinism
    for _ in range(10):
        subsequent_run = compute_programmatic_skill_match(candidate_skills, jd_text)
        assert subsequent_run == first_run
        assert subsequent_run["matching_skills"] == first_run["matching_skills"]
        assert subsequent_run["missing_skills"] == first_run["missing_skills"]
        assert subsequent_run["programmatic_score"] == first_run["programmatic_score"]


@pytest.mark.asyncio
async def test_assess_job_posting_locks_deterministic_skills_and_score(
    db_session: AsyncSession,
):
    """Verify that assess_job_posting strictly locks programmatic_match_score and matching/missing skills."""

    # Simulate LLM returning its own subjective/differing skill lists
    mock_llm_result = JobAssessmentResult(
        company="Stripe",
        position="Senior Backend Engineer",
        fit_score=85,
        programmatic_match_score=999,  # Should be overwritten by deterministic baseline
        matching_skills=[
            "RandomSkill1",
            "RandomSkill2",
        ],  # Should be locked to deterministic
        missing_skills=["RandomSkill3"],  # Should be locked to deterministic
        matched_skills_count=2,
        total_required_skills_count=3,
        match_summary="Solid match for backend requirements.",
        hard_matches=HardMatches(
            keyword_match_rate="4/6 core skills", top_alignment=["Python", "FastAPI"]
        ),
        tailoring_strategy=ResumeTailoringStrategy(
            action_verb_enhancements=[],
            structural_adjustments=[],
            vocabulary_translation=[],
        ),
    )

    captured_prompt_inputs = {}

    def capture_and_return(prompt_val):
        nonlocal captured_prompt_inputs
        captured_prompt_inputs = prompt_val
        return mock_llm_result

    with patch("app.services.llm.get_task_chat_model") as mock_get_chat:
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = RunnableLambda(
            capture_and_return
        )
        mock_get_chat.return_value = mock_llm

        deterministic_matching = ["Docker", "FastAPI", "PostgreSQL", "Python"]
        deterministic_missing = ["AWS", "Kafka", "Kubernetes"]
        deterministic_score = 57  # 4 / 7 = 57%

        res = await assess_job_posting(
            db_session,
            job_description="Sample JD text",
            candidate_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            candidate_cv="Candidate CV content...",
            programmatic_baseline=deterministic_score,
            matched_skills_count=len(deterministic_matching),
            total_required_skills_count=len(deterministic_matching)
            + len(deterministic_missing),
            matching_skills=deterministic_matching,
            missing_skills=deterministic_missing,
        )

        # 1. Programmatic score must match the deterministic baseline exactly
        assert res.programmatic_match_score == deterministic_score
        assert res.matched_skills_count == 4
        assert res.total_required_skills_count == 7

        # 2. Matching and missing skills must match the deterministic lists, NOT LLM outputs
        assert res.matching_skills == deterministic_matching
        assert res.missing_skills == deterministic_missing

        # 3. Prompt must receive the verified skills
        prompt_text = captured_prompt_inputs.to_string()
        assert (
            "Verified Matching Skills: Docker, FastAPI, PostgreSQL, Python"
            in prompt_text
        )
        assert "Verified Missing Skills: AWS, Kafka, Kubernetes" in prompt_text


def test_compute_programmatic_skill_match_no_false_positive_substrings():
    """Verify that candidate skills like C, R, Go, Java are not falsely matched as substrings."""
    candidate_skills = [
        "Python",
        "Go",
        "Java",
        "JavaScript",
        "C",
        "R",
        "Vue.js",
        "Artificial Intelligence (AI)",
        "Large Language Models (LLM)",
        "Retrieval-Augmented Generation (RAG)",
        "Distributed Systems",
    ]
    tavily_jd = """
    We're building the infrastructure layer for agentic web interaction at scale.
    Our API is designed from the ground up to power Retrieval-Augmented Generation (RAG) and real-time reasoning in AI systems.
    By connecting LLMs to high-quality, trustworthy web content, we help developers build agents.
    In this role, you will work on browser rendering, JavaScript execution, and large-scale rendering infrastructure.
    You may be a good fit if you have experience with:
    Playwright, Puppeteer, React, Vue, Angular, Svelte, and modern frontend architectures.
    Distributed systems design and performance optimisation.
    """

    res = compute_programmatic_skill_match(candidate_skills, tavily_jd)

    # Must NOT contain false substring matches
    for false_skill in ["C", "R", "Go", "Java"]:
        assert false_skill not in res["matching_skills"]
        assert false_skill not in res["missing_skills"]

    # Must contain legitimate skills from JD
    assert "JavaScript" in res["matching_skills"]
    assert "Retrieval-Augmented Generation (RAG)" in res["matching_skills"]
    assert "Distributed Systems" in res["matching_skills"]
    assert "React" in res["missing_skills"]
    assert "Angular" in res["missing_skills"]
    assert "Playwright" in res["missing_skills"]


def test_calibration_window_gap():
    """Verify AI-first condition-driven calibration and deal-breaker safety ceilings."""
    from app.services.llm import calibrate_assessment_score_and_recommendation

    # 1. 1 minor caveat / risk caps score at 85% (APPLY_STRONGLY)
    score, rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=90,
        programmatic_baseline=60,
        critical_risks=["Minor caveat"],
        seniority_fit="MATCHES",
    )
    assert score == 85
    assert rec == "APPLY_STRONGLY"

    # raw score 30 respects low AI score (no artificial inflation)
    score_low, rec_low = calibrate_assessment_score_and_recommendation(
        raw_fit_score=30,
        programmatic_baseline=60,
        critical_risks=[],
        seniority_fit=None,
    )
    assert score_low == 30
    assert rec_low == "DO_NOT_APPLY"

    # 2. Strong candidate (0 risks, matches seniority) reaches full AI evaluated score 95%
    score_boost, rec_boost = calibrate_assessment_score_and_recommendation(
        raw_fit_score=95,
        programmatic_baseline=60,
        critical_risks=[],
        seniority_fit="MATCHES",
    )
    assert score_boost == 95
    assert rec_boost == "APPLY_STRONGLY"

    # 3. Underqualified penalty clamp: ceiling strictly clamped to 65% (STRETCH_ROLE)
    score_under, rec_under = calibrate_assessment_score_and_recommendation(
        raw_fit_score=90,
        programmatic_baseline=70,
        critical_risks=["Seniority deficit"],
        seniority_fit="UNDERQUALIFIED",
    )
    assert score_under == 65
    assert rec_under == "STRETCH_ROLE"

    # 4. Critical risks >= 2 without strong baseline (<75%) strictly clamped to 65%
    score_risks, rec_risks = calibrate_assessment_score_and_recommendation(
        raw_fit_score=90,
        programmatic_baseline=50,
        critical_risks=["Risk 1", "Risk 2"],
        seniority_fit="MATCHES",
    )
    assert score_risks == 65
    assert rec_risks == "STRETCH_ROLE"


def test_regex_false_positives_eliminated():
    """Verify common English phrases do not trigger false positive skills (Less, Next.js, REST)."""
    from app.services.skill_normalizer import extract_skills_from_text

    noisy_jd_text = (
        "Join our team to build our next generation platform with less overhead and downtime. "
        "The rest of the company relies on this infrastructure."
    )
    extracted = extract_skills_from_text(noisy_jd_text)
    assert "Less" not in extracted
    assert "Next.js" not in extracted
    assert "REST API" not in extracted

    # Legitimate mentions of Next.js and REST APIs must still be extracted
    legit_jd_text = (
        "We require experience with Next.js, React, and REST APIs, along with Python."
    )
    legit_extracted = extract_skills_from_text(legit_jd_text)
    assert "Next.js" in legit_extracted
    assert "REST API" in legit_extracted
    assert "Python" in legit_extracted
    assert "React" in legit_extracted


def test_concept_subsumption_and_conditional_fallback():
    """Verify concept subsumption (Containers, Databases, Concurrency) and regex fallback."""
    from app.services.matcher import compute_programmatic_skill_match

    # Subsumption: Docker satisfies Containers, PostgreSQL satisfies Databases, Distributed Systems satisfies Concurrency
    candidate_skills = ["Python", "Docker", "PostgreSQL", "Distributed Systems"]
    jd_skills = ["Containers", "Databases", "Concurrency", "Python"]

    res = compute_programmatic_skill_match(
        candidate_skills=candidate_skills,
        jd_text="Some random text with less downtime",
        jd_required_skills=jd_skills,
    )
    # All 4 skills should match due to subsumption clusters
    assert len(res["missing_skills"]) == 0
    assert len(res["matching_skills"]) == 4
    assert res["programmatic_score"] == 100

    # Fallback verification: When jd_required_skills is empty, fallback to text regex scanning
    res_fallback = compute_programmatic_skill_match(
        candidate_skills=["Python"],
        jd_text="Senior engineer with deep Python expertise.",
        jd_required_skills=None,
    )
    assert "Python" in res_fallback["matching_skills"]


def test_ai_first_scoring_with_noisy_denominators():
    """Verify that a noisy 17% baseline from 59 extra non-skills does not crush an 88% AI fit score."""
    from app.services.llm import calibrate_assessment_score_and_recommendation

    score, rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=88,
        programmatic_baseline=17,
        critical_risks=[],
        seniority_fit="MATCHES",
        total_required_skills=71,
    )
    # Under AI-First semantic scoring, score is preserved at 88% rather than clamped to 32%
    assert score == 88
    assert rec == "APPLY_STRONGLY"


def test_filter_non_technical_open_ended_skills_from_matrix():
    """Verify that open-ended LLM concepts (Safe Deployments, Quotas, Access Revocation) are rejected from the skills matrix."""
    from app.services.matcher import compute_programmatic_skill_match

    candidate_skills = ["Python", "Rust", "C", "TypeScript", "Linux", "Docker"]
    # 5 real skills + 10 open-ended duties/nouns from an unconstrained LLM
    noisy_llm_jd_skills = [
        "Python",
        "Rust",
        "PyTorch",
        "React",
        "Tauri",
        "Safe Deployments",
        "Access Revocation",
        "Quotas",
        "Incident Investigation",
        "Driver Compatibility",
        "Result Retrieval",
        "Workload Isolation",
        "Desktop Packaging",
        "Developer",
        "Deterministic Systems",
    ]

    res = compute_programmatic_skill_match(
        candidate_skills=candidate_skills,
        jd_text="Engineering role requirements...",
        jd_required_skills=noisy_llm_jd_skills,
    )

    # Only the 5 recognized tools (Python, Rust, PyTorch, React, Tauri) should be in target skills
    assert res["total_required_count"] == 5
    assert set(res["matching_skills"]) == {"Python", "Rust"}
    assert set(res["missing_skills"]) == {"PyTorch", "React", "Tauri"}
    # Non-skills must be completely excluded
    for non_skill in [
        "Safe Deployments",
        "Access Revocation",
        "Quotas",
        "Incident Investigation",
        "Driver Compatibility",
        "Result Retrieval",
        "Workload Isolation",
        "Desktop Packaging",
        "Developer",
        "Deterministic Systems",
    ]:
        assert non_skill not in res["missing_skills"]
        assert non_skill not in res["matching_skills"]


@pytest.mark.asyncio
async def test_extract_job_spec_context_anchors_injection():
    """Verify that extract_job_spec enriches raw webpage data with Context Anchors when hints are provided."""
    from unittest.mock import AsyncMock

    from app.schemas.llm import ExtractedJobSpec
    from app.services.llm import extract_job_spec

    mock_session = AsyncMock()
    captured_prompt_inputs = []

    def mock_invoke(inputs, config=None):
        captured_prompt_inputs.append(inputs)
        return ExtractedJobSpec(
            job_found=True,
            company="Anthropic",
            position="Senior AI Engineer",
            detected_language="English",
            extracted_skills=["Python", "PyTorch"],
        )

    mock_runnable = RunnableLambda(mock_invoke)

    with (
        patch("app.services.llm.get_task_chat_model") as mock_get_model,
        patch(
            "app.services.llm.get_prompt_template",
            return_value="System prompt:\n{raw_webpage_data}",
        ),
    ):
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_runnable
        mock_get_model.return_value = mock_model

        res = await extract_job_spec(
            mock_session,
            raw_webpage_data="We are looking for an engineer to join our team...",
            title_hint="Anthropic - Senior AI Engineer",
            page_title="Senior AI Engineer | Anthropic Careers",
        )

        assert res.position == "Senior AI Engineer"
        assert len(captured_prompt_inputs) == 1
        prompt_val = captured_prompt_inputs[0]
        prompt_text = str(prompt_val)
        assert "Context Anchors (External Metadata):" in prompt_text
        assert "Title / Role Hint: Anthropic - Senior AI Engineer" in prompt_text
        assert (
            "Candidate Page Title: Senior AI Engineer | Anthropic Careers"
            in prompt_text
        )
