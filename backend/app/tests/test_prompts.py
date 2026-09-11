import pytest
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompts import (
    DEFAULT_PROMPTS,
    clear_prompt_cache,
    get_prompt_template,
    seed_default_prompts,
)


def test_all_default_prompts_compile_and_have_valid_syntax():
    """Verify every prompt in DEFAULT_PROMPTS compiles cleanly with LangChain without unescaped brace errors."""
    assert "extraction" not in DEFAULT_PROMPTS
    assert len(DEFAULT_PROMPTS) == 15

    for _prompt_name, template_str in DEFAULT_PROMPTS.items():
        assert isinstance(template_str, str)
        assert len(template_str) > 20
        # ChatPromptTemplate parses all {placeholders} and enforces {{escaped_braces}}
        prompt_obj = ChatPromptTemplate.from_template(template_str)
        assert prompt_obj is not None

        # Format with dummy values for each identified variable to ensure string interpolation succeeds
        dummy_kwargs = {var: f"dummy_{var}" for var in prompt_obj.input_variables}
        formatted = prompt_obj.format(**dummy_kwargs)
        assert len(formatted) > len(template_str) or len(dummy_kwargs) == 0


@pytest.mark.asyncio
async def test_seed_and_get_prompt_template(db_session: AsyncSession):
    """Verify seeding into DB and retrieving cached prompts works for all 15 prompts."""
    clear_prompt_cache()
    await seed_default_prompts(db_session)

    for prompt_name in DEFAULT_PROMPTS:
        tmpl = await get_prompt_template(db_session, prompt_name)
        assert tmpl == DEFAULT_PROMPTS[prompt_name]

    # Verify cache invalidation
    clear_prompt_cache("jd_extraction")
    tmpl_reloaded = await get_prompt_template(db_session, "jd_extraction")
    assert tmpl_reloaded == DEFAULT_PROMPTS["jd_extraction"]


def test_assessment_prompt_seniority_directives():
    """Verify assessment prompt contains explicit seniority bands, tolerance buffers, and anti-speculation rules."""
    template = DEFAULT_PROMPTS["assessment"]
    assert "STRICT BAN ON SPECULATIVE INFERENCE" in template
    assert "Junior / Associate / Intern: 0–3 years" in template
    assert "Mid-Level / Medior / Generic Titles" in template
    assert "Senior / Lead: 4+ years" in template
    assert "Staff / Principal / Architect: 8+ years" in template
    assert "1-Year Tolerance Buffer" in template
    assert "Permissive Overqualification" in template


def test_assessment_prompt_factual_grounding_directives():
    """Verify assessment prompt contains anti-stretching, zero-metric hallucination, and factual pros/cons directives."""
    template = DEFAULT_PROMPTS["assessment"]
    assert "ZERO-METRIC HALLUCINATION" in template
    assert "FACTUAL STRATEGIC PROS (pros)" in template
    assert "FACTUAL GAP CAVEATS (cons)" in template
    assert "OBJECTIVE MATCH SUMMARY (match_summary)" in template
    assert (
        "FACTUAL TAILORING STRATEGY & VOCABULARY MAPPING (tailoring_strategy)"
        in template
    )


def test_jd_extraction_factual_grounding_directives():
    """Verify jd_extraction prompt forbids speculating or guessing why_hiring and what_you_will_build."""
    template = DEFAULT_PROMPTS["jd_extraction"]
    assert "MUST be null unless explicitly stated under a clear heading" in template
    assert "Strictly forbid inferring, guessing, or summarizing reasons" in template


def test_previous_assessment_payload_backward_compatibility():
    """Verify that existing stored assessment payloads deserialize into JobAssessmentResult with zero breakage."""
    from app.schemas.llm import JobAssessmentResult

    # Simulate an assessment stored prior to these changes
    legacy_assessment_json = {
        "company": "Legacy Corp",
        "company_url": "legacy.com",
        "position": "Backend Engineer",
        "fit_score": 78,
        "programmatic_match_score": 75,
        "matched_skills_count": 6,
        "total_required_skills_count": 8,
        "match_summary": "Candidate matches primary stack with slight gaps.",
        "matching_skills": ["Python", "PostgreSQL", "Docker", "FastAPI"],
        "missing_skills": ["Kubernetes", "Kafka"],
        "pros": ["Strong Python experience", "Great culture fit"],
        "cons": ["Missing Kafka"],
        "critical_risks": [],
        "seniority_fit": "MATCHES",
        "salary_min": 120000.0,
        "salary_max": 140000.0,
        "currency": "USD",
        "salary_period": "YEARLY",
        "location": "Remote",
        "work_model": "Remote",
        "recommendation": "APPLY_MODERATELY",
        "hard_matches": {
            "keyword_match_rate": "4/6",
            "top_alignment": ["Python", "FastAPI"],
        },
        "optimization_gaps": {
            "missing_completely": ["Kafka"],
            "vocabulary_mismatches": ["Postgres vs PostgreSQL"],
            "experience_mismatch": None,
        },
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "jd_term": "PostgreSQL",
                    "cv_term": "Postgres",
                    "replacement_guidance": "Use official term",
                }
            ],
            "impact_reframing": [
                {
                    "bullet_point": "Built an API",
                    "suggested_rewrite": "Engineered high-throughput API with FastAPI",
                    "reason": "Aligns with JD verbs",
                }
            ],
            "structural_adjustments": ["Highlight backend section"],
        },
        "markdown_report": "# Job Match Analysis: 78%\n\nLegacy report text.",
        "summary": "Legacy summary string",
    }

    parsed = JobAssessmentResult.model_validate(legacy_assessment_json)
    assert parsed.company == "Legacy Corp"
    assert parsed.fit_score == 78
    assert parsed.pros == ["Strong Python experience", "Great culture fit"]
    assert len(parsed.matching_skills) == 4
    assert parsed.tailoring_strategy is not None
    assert len(parsed.tailoring_strategy.impact_reframing) == 1
    # Verify dumping to dict works identically
    dumped = parsed.model_dump()
    assert dumped["company"] == "Legacy Corp"
    assert dumped["fit_score"] == 78


def test_is_context_size_error():
    """Verify context size exceeded error detection matches various engine error payloads."""
    from app.services.llm import is_context_size_error

    err1 = Exception(
        'Engine protocol predict stream returned an error: {"code":500,"message":"Context size has been exceeded.","type":"server_error"}'
    )
    assert is_context_size_error(err1) is True

    err2 = Exception("Error: context length exceeded: max 4096 tokens")
    assert is_context_size_error(err2) is True

    err3 = Exception("BadRequestError: maximum context length is 8192 tokens")
    assert is_context_size_error(err3) is True

    err4 = Exception("Connection refused: 127.0.0.1:1234")
    assert is_context_size_error(err4) is False


def test_sanitize_and_cap_jd_ceiling():
    """Verify sanitize_and_cap_jd strictly enforces character and token ceilings."""
    from app.core.prompts import sanitize_and_cap_jd

    huge_text = "Software Engineer with distributed systems experience.\n" * 500
    assert len(huge_text) > 25000

    capped = sanitize_and_cap_jd(huge_text, max_tokens=1500)
    # 1500 tokens * 4 = 6000 chars + truncation marker
    assert len(capped) <= 6100
    assert "[Job posting truncated to fit context window]" in capped

    short_text = "Senior Python Developer at TechCorp."
    assert sanitize_and_cap_jd(short_text, max_tokens=1500) == short_text


def test_calibrate_assessment_score_prevents_arbitrary_risk_cliff_drop():
    """Verify that multiple critical risks do NOT artificially slam a high-matching candidate to 65%."""
    from app.services.llm import calibrate_assessment_score_and_recommendation

    # 1. 91% baseline with 1 risk
    score_1_risk, rec_1 = calibrate_assessment_score_and_recommendation(
        raw_fit_score=82,
        programmatic_baseline=91,
        critical_risks=["Missing Computer Vision"],
        seniority_fit="MATCHES",
    )
    assert score_1_risk == 82
    assert rec_1 == "APPLY_MODERATELY"

    # Score >= 85 with <= 1 risk yields APPLY_STRONGLY
    score_strong, rec_strong = calibrate_assessment_score_and_recommendation(
        raw_fit_score=88,
        programmatic_baseline=91,
        critical_risks=["Missing Computer Vision"],
        seniority_fit="MATCHES",
    )
    assert score_strong >= 85
    assert rec_strong == "APPLY_STRONGLY"

    # 2. 91% baseline with 3 risks (previously caused cliff-drop to 65%)
    score_3_risks, rec_3 = calibrate_assessment_score_and_recommendation(
        raw_fit_score=82,
        programmatic_baseline=91,
        critical_risks=[
            "Missing Computer Vision",
            "Compliance specifics (ISO 27001/GDPR)",
            "AI Coding Tools proficiency",
        ],
        seniority_fit="MATCHES",
    )
    # The score must remain stable at 82 instead of dropping to 65!
    assert score_3_risks == 82
    assert rec_3 == "APPLY_MODERATELY"

    # 3. True underqualified candidate is strictly clamped to <= 65%
    underqualified_score, underqualified_rec = (
        calibrate_assessment_score_and_recommendation(
            raw_fit_score=85,
            programmatic_baseline=91,
            critical_risks=["Seniority deficit: 4 yrs vs 8+ yrs Staff requirement"],
            seniority_fit="UNDERQUALIFIED",
        )
    )
    assert underqualified_score <= 65
    assert underqualified_rec == "STRETCH_ROLE"

    # 4. Low programmatic baseline (35% on N=10 skills) prevents grade inflation (clamped to <= 60 with +25% seniority bonus)
    low_match_score, _ = calibrate_assessment_score_and_recommendation(
        raw_fit_score=85,
        programmatic_baseline=35,
        critical_risks=[],
        seniority_fit="MATCHES",
        total_required_skills=10,
    )
    assert low_match_score <= 60

    # 5. Sparse keywords (1 of 2 matched = 50% baseline, but N=2 total skills)
    # Blended baseline: 0.70 * 85 + 0.30 * 50 = 60 + 15 = 75. Candidate matches seniority and 0 risks -> score reaches 85!
    sparse_score, sparse_rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=85,
        programmatic_baseline=50,
        critical_risks=[],
        seniority_fit="MATCHES",
        total_required_skills=2,
    )
    assert sparse_score == 85
    assert sparse_rec == "APPLY_STRONGLY"

    # 6. Zero keywords extracted (N=0, baseline None, raw AI score 88, seniority MATCHES)
    # Bounded up to 90%, not artificially crushed to 70%!
    zero_kw_score, zero_kw_rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=88,
        programmatic_baseline=None,
        critical_risks=[],
        seniority_fit="MATCHES",
        total_required_skills=0,
    )
    assert zero_kw_score == 88
    assert zero_kw_rec == "APPLY_STRONGLY"


def test_interview_star_eval_rubric_point_decomposition():
    """Verify interview_star_eval prompt includes deterministic point decomposition rubric and score calculation."""
    from app.services.interview_simulator_service import _normalize_evaluation_data

    template = DEFAULT_PROMPTS["interview_star_eval"]
    assert (
        "DETERMINISTIC STAR RUBRIC POINT DECOMPOSITION (100 TOTAL POINTS):" in template
    )
    assert "situation (0 to 20 points):" in template
    assert "task (0 to 20 points):" in template
    assert "action (0 to 35 points - Core Depth):" in template
    assert "result (0 to 25 points):" in template
    assert '"rubric_scores"' in template

    # Verify normalization with explicit rubric scores calculates sum
    raw_with_rubric = {
        "rubric_scores": {
            "situation": 18,
            "task": 17,
            "action": 32,
            "result": 21,
        },
        "score": 50,  # Model output drifted score, normalization must override with exact sum!
        "star_presence": {
            "situation": True,
            "task": True,
            "action": True,
            "result": True,
        },
        "strengths": ["Clear metrics"],
        "missing_gaps": [],
        "constructive_critique": "Solid answer",
        "exemplar_rewrite": "Exemplar...",
    }
    normalized = _normalize_evaluation_data(raw_with_rubric)
    assert normalized["score"] == 88.0  # 18 + 17 + 32 + 21 = 88
    assert normalized["rubric_scores"] == {
        "situation": 18.0,
        "task": 17.0,
        "action": 32.0,
        "result": 21.0,
    }

    # Verify backward compatibility with legacy evaluation without rubric_scores
    raw_legacy = {
        "score": 79.5,
        "star_presence": {
            "situation": True,
            "task": True,
            "action": True,
            "result": False,
        },
        "strengths": ["Good start"],
        "missing_gaps": ["No result"],
    }
    norm_legacy = _normalize_evaluation_data(raw_legacy)
    assert norm_legacy["score"] == 79.5
    assert "rubric_scores" not in norm_legacy


def test_role_alignment_dossier_metric_fabrication_rules():
    """Verify role_alignment_dossier prompt strictly bans fake metrics and anchors rewrites in architectural scope."""
    template = DEFAULT_PROMPTS["role_alignment_dossier"]
    assert "ZERO-METRIC FABRICATION" in template
    assert "NEVER invent synthetic numbers, percentages" in template
    assert "ARCHITECTURAL & MECHANISM GROUNDING" in template
    assert (
        "elevate them strictly through technical mechanism, architectural scope"
        in template
    )


def test_application_qa_behavioral_grounding_rules():
    """Verify application_qa prompt strictly bans fake behavioral stories and grounds in real technical methodology."""
    template = DEFAULT_PROMPTS["application_qa"]
    assert "HONEST BEHAVIORAL & METHODOLOGY GROUNDING" in template
    assert (
        "STRICTLY FORBID fabricating fictional past stories, imaginary employers, or synthetic crises"
        in template
    )
    assert "verified engineering principles, architectural methodologies" in template
