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
    """Verify asymmetric condition-driven calibration window."""
    from app.services.llm import calibrate_assessment_score_and_recommendation

    # 1. Base window (+/- 15%) when baseline is 60 and no special conditions
    # raw score 90 clamped to 60 + 15 = 75 with 1 risk
    score, rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=90,
        programmatic_baseline=60,
        critical_risks=["Minor caveat"],
        seniority_fit="MATCHES",
    )
    assert score == 75
    assert rec == "APPLY_MODERATELY"

    # raw score 30 clamped to 60 - 15 = 45
    score_low, rec_low = calibrate_assessment_score_and_recommendation(
        raw_fit_score=30,
        programmatic_baseline=60,
        critical_risks=[],
        seniority_fit=None,
    )
    assert score_low == 45
    assert rec_low == "DO_NOT_APPLY"

    # 2. Seniority boost (+25%) when verified seniority matches/exceeds and 0 critical risks
    score_boost, rec_boost = calibrate_assessment_score_and_recommendation(
        raw_fit_score=95,
        programmatic_baseline=60,
        critical_risks=[],
        seniority_fit="MATCHES",
    )
    assert score_boost == 85  # 60 + 25
    assert rec_boost == "APPLY_STRONGLY"

    # 3. Underqualified penalty clamp: ceiling clamped to min(65, baseline + 5)
    score_under, rec_under = calibrate_assessment_score_and_recommendation(
        raw_fit_score=90,
        programmatic_baseline=70,
        critical_risks=["Seniority deficit"],
        seniority_fit="UNDERQUALIFIED",
    )
    assert score_under == 65
    assert rec_under == "STRETCH_ROLE"

    # 4. Critical risks >= 2 penalty clamp
    score_risks, rec_risks = calibrate_assessment_score_and_recommendation(
        raw_fit_score=90,
        programmatic_baseline=50,
        critical_risks=["Risk 1", "Risk 2"],
        seniority_fit="MATCHES",
    )
    assert score_risks == 55  # 50 + 5
    assert rec_risks == "STRETCH_ROLE"
