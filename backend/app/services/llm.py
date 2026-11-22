import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_factory import (
    get_active_llm_config_dict,
    get_task_chat_model,
    strip_reasoning_tags,
)
from app.core.prompts import get_prompt_template, sanitize_and_cap_jd
from app.models.applications import ApplicationEmbeddingModel
from app.schemas.candidate_profile import CVAnonymizationResult
from app.schemas.llm import (
    EmailExtractionResult,
    EmailMatchTiebreakerResult,
    ExtractedJobSpec,
    JobAssessmentResult,
)
from app.services.postgres_tracer import PostgresTracer
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)


def is_context_size_error(exc: Exception) -> bool:
    """Checks if an exception indicates LLM context length / window was exceeded."""
    err_str = str(exc).lower()
    return any(
        kw in err_str
        for kw in (
            "context size has been exceeded",
            "context length exceeded",
            "maximum context length",
            "context window",
            "context_length_exceeded",
            "too many tokens",
        )
    ) or ("context" in err_str and "exceeded" in err_str)


def split_text_semantically(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[str]:
    """
    Splits text semantically using RecursiveCharacterTextSplitter on sentence
    and Markdown section boundaries.
    """
    if not text:
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


def truncate_text_semantically(text: str, max_chars: int = 8000) -> str:
    """
    Cleans raw text (normalizes whitespace, strips noise) and semantically bounds/truncates
    the text along sentence and Markdown section boundaries while preserving essential content.
    """
    if not text:
        return ""

    cleaned = re.sub(r"[ \t]+", " ", text)
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    chunks = split_text_semantically(cleaned, chunk_size=max_chars, chunk_overlap=0)
    if chunks:
        return chunks[0]
    return cleaned[:max_chars]


async def get_active_llm_config(db: AsyncSession) -> dict[str, Any]:
    """Backward compatibility helper returning active LLM config dictionary."""
    return await get_active_llm_config_dict(db)


async def extract_job_spec(
    db: AsyncSession,
    raw_webpage_data: str,
    title_hint: str | None = None,
    page_title: str | None = None,
) -> ExtractedJobSpec:
    """
    Stage 1: Extracts structured job specs, responsibilities, requirements, and ATS keywords from raw webpage data.
    Uses JD_EXTRACTION task binding with temperature=0.0 and reasoning disabled.
    """
    context_anchors = []
    if (
        title_hint
        and title_hint.strip()
        and title_hint.strip().lower() not in {"job lead", "pasted job description"}
    ):
        context_anchors.append(f"- Title / Role Hint: {title_hint.strip()}")
    if page_title and page_title.strip():
        context_anchors.append(f"- Candidate Page Title: {page_title.strip()}")

    anchor_block = ""
    if context_anchors:
        anchor_block = (
            "Context Anchors (External Metadata):\n"
            + "\n".join(context_anchors)
            + "\n\n"
        )

    enriched_data = anchor_block + raw_webpage_data
    cleaned_data = truncate_text_semantically(enriched_data)
    async with trace_operation(
        category="llm",
        name="extract_job_spec",
        inputs={
            "char_count": len(cleaned_data),
            "sample": cleaned_data[:200],
            "has_title_hint": bool(title_hint),
            "has_page_title": bool(page_title),
        },
        db=db,
    ) as trace_ctx:
        llm = await get_task_chat_model(db, task_type="JD_EXTRACTION", temperature=0.0)
        structured_llm = llm.with_structured_output(
            ExtractedJobSpec, method="json_schema"
        )
        template_str = await get_prompt_template(db, "jd_extraction")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert recruitment data analyst. "
                        "Extract essential job details from raw scraped webpage markdown text or pasted specs. "
                        "Disregard navigation, cookie popups, footers, headers, ads, or legal notices. "
                        "If no job vacancy is found, set job_found to false and leave fields as default."
                    ),
                ),
                ("human", template_str),
            ]
        )

        chain = prompt | structured_llm
        try:
            result = await chain.ainvoke(
                {
                    "raw_webpage_data": cleaned_data,
                    "email_content": cleaned_data,
                },
                config={"callbacks": [PostgresTracer()]},
            )
        except Exception as exc:
            if is_context_size_error(exc):
                logger.warning(
                    "Context size exceeded during extract_job_spec (%d chars). Retrying with compact fallback (3,500 chars)...",
                    len(cleaned_data),
                )
                compact_data = truncate_text_semantically(cleaned_data, max_chars=3500)
                result = await chain.ainvoke(
                    {
                        "raw_webpage_data": compact_data,
                        "email_content": compact_data,
                    },
                    config={"callbacks": [PostgresTracer()]},
                )
            else:
                raise

        if not isinstance(result, ExtractedJobSpec):
            result = ExtractedJobSpec.model_validate(result)

        from app.services.compensation_parser import parse_compensation_text
        from app.services.domain_resolver import clean_company_name

        if result.company:
            result.company = clean_company_name(result.company)

        # Parse compensation text into structured fields if available
        if result.compensation_text:
            parsed_comp = parse_compensation_text(result.compensation_text)
            if result.salary_min is None and parsed_comp.get("salary_min") is not None:
                result.salary_min = parsed_comp["salary_min"]
            if result.salary_max is None and parsed_comp.get("salary_max") is not None:
                result.salary_max = parsed_comp["salary_max"]
            if (not result.currency or result.currency == "USD") and parsed_comp.get(
                "currency"
            ):
                result.currency = parsed_comp["currency"]
            if (
                not result.salary_period or result.salary_period == "NOT_SPECIFIED"
            ) and parsed_comp.get("salary_period"):
                result.salary_period = parsed_comp["salary_period"]

        trace_ctx["outputs"] = {
            "job_found": result.job_found,
            "company": result.company,
            "position": result.position,
            "responsibilities_count": len(result.responsibilities),
            "requirements_count": len(result.requirements),
            "extracted_skills": result.extracted_skills,
            "salary_min": result.salary_min,
            "salary_max": result.salary_max,
            "currency": result.currency,
            "salary_period": result.salary_period,
        }

        return result


async def extract_email_info(
    db: AsyncSession,
    email_content: str,
    sender: str | None = None,
    subject: str | None = None,
    date: str | None = None,
) -> EmailExtractionResult:
    """Extracts structured job application metadata from email body using LangChain EXTRACTION model."""
    llm = await get_task_chat_model(db, task_type="EXTRACTION", temperature=0.1)
    structured_llm = llm.with_structured_output(
        EmailExtractionResult, method="json_schema"
    )
    template_str = await get_prompt_template(db, "email_extraction")

    formatted_content = email_content
    if sender or subject or date:
        formatted_content = f"""From: {sender or "Not specified"}
Date: {date or "Not specified"}
Subject: {subject or "Not specified"}

Email Body:
{email_content}"""

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract only the newest recruitment message. Return structured data. "
                "For status and action return exact verbatim excerpts in status_evidence and action_evidence. "
                "For an explicit task deadline return its verbatim clause in deadline_evidence; "
                "never use meeting availability as a task deadline. "
                "Return meeting dates discussed in prose as verbatim meeting_proposal. "
                "Acknowledgments do not change status or create tasks. "
                "due_date must be null; never confirm meeting times from prose.",
            ),
            ("human", template_str),
        ]
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke(
        {"email_content": formatted_content},
        config={"callbacks": [PostgresTracer()]},
    )
    res_obj = (
        result
        if isinstance(result, EmailExtractionResult)
        else EmailExtractionResult.model_validate(result)
    )
    if res_obj.summary:
        res_obj.summary = strip_reasoning_tags(res_obj.summary)
    if res_obj.action:
        res_obj.action = strip_reasoning_tags(res_obj.action)
    if res_obj.position:
        res_obj.position = strip_reasoning_tags(res_obj.position)
    if res_obj.company:
        res_obj.company = strip_reasoning_tags(res_obj.company)
    # Deprecated field: deadline_evidence / meeting_proposal replace raw LLM due_date
    res_obj.due_date = None
    return res_obj


async def resolve_email_match_tiebreaker(
    db: AsyncSession,
    *,
    sender: str | None = None,
    subject: str | None = None,
    summary: str | None = None,
    extracted_company: str | None = None,
    extracted_position: str | None = None,
    candidates: list[dict[str, Any]],
) -> EmailMatchTiebreakerResult:
    """Gray-zone entity-resolution tiebreaker invoked only when deterministic matching
    would otherwise route an email to staging. Uses EMAIL_EXTRACTION / EXTRACTION model.
    """
    if not candidates:
        return EmailMatchTiebreakerResult(
            matched_application_id=None, confidence=0.0, reason="no_candidates"
        )

    lines = []
    for c in candidates:
        last_act = c.get("last_activity_at") or "unknown"
        status_label = c.get("status") or "UNKNOWN"
        note = " [no-response archived]" if status_label == "ARCHIVED" else ""
        lines.append(
            f"- ID={c['application_id']} | Company={c['company']} | Position={c['position']} "
            f"| Status={status_label}{note} | LastActivity={last_act}"
        )
    candidates_text = "\n".join(lines)

    try:
        llm = await get_task_chat_model(
            db, task_type="EMAIL_EXTRACTION", temperature=0.0
        )
        structured_llm = llm.with_structured_output(
            EmailMatchTiebreakerResult, method="json_schema"
        )
        template_str = await get_prompt_template(db, "email_match_tiebreaker")
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an entity-resolution tiebreaker. Match the email to the right candidate application when the company/brand alias and role discipline align (allowing normal recruiter title abbreviations); return null only when the company is unrelated or roles are genuinely indistinguishable.",
                ),
                ("human", template_str),
            ]
        )
        chain = prompt | structured_llm
        result = await chain.ainvoke(
            {
                "sender": sender or "Not specified",
                "subject": subject or "Not specified",
                "extracted_company": extracted_company or "Not specified",
                "extracted_position": extracted_position or "Not specified",
                "summary": summary or "Not specified",
                "candidates_text": candidates_text,
            },
            config={"callbacks": [PostgresTracer()]},
        )
        res_obj = (
            result
            if isinstance(result, EmailMatchTiebreakerResult)
            else EmailMatchTiebreakerResult.model_validate(result)
        )
        if res_obj.reason:
            res_obj.reason = strip_reasoning_tags(res_obj.reason)
        return res_obj
    except Exception as err:
        logger.warning(
            "Email match tiebreaker failed; falling back to staging: %s", err
        )
        return EmailMatchTiebreakerResult(
            matched_application_id=None, confidence=0.0, reason="tiebreaker_error"
        )


def _sanitize_critical_risks(risks: list[str] | None) -> list[str]:
    """
    Cleanses critical_risks by stripping false-positive 'pseudo-risks' where the LLM
    reports an absence of risk (e.g. 'Missing mandatory spoken language: None', 'No critical risks', 'N/A').
    """
    if not risks:
        return []

    pseudo_patterns = [
        r"^none[\.\s]*$",
        r"^n/?a[\.\s]*$",
        r"^no\s+(critical\s+)?(risks?|deal[- ]?breakers?|hesitations?|red\s*flags?|concerns?|issues?)",
        r"^missing\s+mandatory\s+(spoken\s+)?language\s*:\s*(none|n/?a|not\s+specified|no\b|neither|english|candidate)",
        r"\blanguage.*:\s*(none|n/?a|not\s+specified|no\b)",
        r"\bnone\b.*(does not specify|no mandatory|not required|no requirement|context)",
        r"^no\s+mandatory\s+(spoken\s+)?language",
        r"^verified\s+prerequisites\s+met",
        r"^candidate\s+meets\s+(all\s+)?requirements",
    ]
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in pseudo_patterns]

    cleaned = []
    for item in risks:
        if not item or not isinstance(item, str):
            continue
        trimmed = item.strip()
        if not trimmed:
            continue
        if any(pat.search(trimmed) for pat in compiled_patterns):
            continue
        lower_trimmed = trimmed.lower()
        if (
            lower_trimmed.endswith(": none")
            or lower_trimmed.endswith(": n/a")
            or lower_trimmed.endswith(": none.")
        ):
            continue
        cleaned.append(trimmed)

    return cleaned


def calibrate_assessment_score_and_recommendation(
    raw_fit_score: int,
    programmatic_baseline: int | None,
    critical_risks: list[str] | None = None,
    seniority_fit: str | None = None,
    total_required_skills: int | None = None,
) -> tuple[int, str]:
    """
    Applies safety bounding and recommendation synchronization to preserve AI-first
    semantic scoring while enforcing hard ceilings strictly for verified deal-breakers:
    1. AI-First Semantic Scoring:
       - The LLM's raw fit score serves as the primary measure of candidate fit.
       - The programmatic baseline is preserved as an informational reference, rather
         than mechanically clamping the score to a narrow [baseline - 15, baseline + 15] window
         which breaks down when extracted skill counts explode with descriptive terminology.
    2. Factual Underqualification Penalty:
       - If seniority_fit is 'UNDERQUALIFIED' (verified deficit >= 2 years), score is strictly capped at 65%.
    3. Critical Risks & Deal-Breakers:
       - If there are >= 2 critical risks (e.g. missing mandatory language, core stack absence),
         ceiling is capped at min(65, raw_fit_score).
       - If there is 1 critical risk, score is capped at 85% (preventing unhedged APPLY_STRONGLY).
    4. Bounding:
       - Ensures the score is within [10, 100].
    5. Synchronizes recommendation:
       - APPLY_STRONGLY: fit_score >= 85 and len(critical_risks) <= 1 and not is_underqualified
       - APPLY_MODERATELY: fit_score >= 70 and not is_underqualified and not has_hard_ceiling
       - STRETCH_ROLE: fit_score >= 50
       - DO_NOT_APPLY: fit_score < 50
    """
    seniority_upper = (seniority_fit or "").strip().upper()
    is_underqualified = seniority_upper == "UNDERQUALIFIED"
    sanitized_risks = _sanitize_critical_risks(critical_risks)
    num_risks = len(sanitized_risks)

    # True disqualifier penalty: underqualified, or multiple critical risks on a candidate without a strong baseline (<75%)
    has_hard_ceiling = is_underqualified or (
        num_risks >= 2 and (programmatic_baseline is None or programmatic_baseline < 75)
    )

    # Start with the model's holistic semantic fit evaluation
    clamped_score = max(10, min(100, int(raw_fit_score)))

    # Apply safety ceilings strictly for verified disqualifiers
    if has_hard_ceiling:
        clamped_score = min(65, clamped_score)
    elif num_risks >= 2:
        # Candidate has multiple minor risks: dampen ceiling smoothly (3 pts per risk)
        max_bound = max(65, min(100, 100 - (num_risks * 3)))
        clamped_score = min(max_bound, clamped_score)
    elif num_risks == 1:
        clamped_score = min(85, clamped_score)

    # Synchronize recommendation tier
    if clamped_score >= 85 and num_risks <= 1 and not is_underqualified:
        rec = "APPLY_STRONGLY"
    elif clamped_score >= 70 and not is_underqualified and not has_hard_ceiling:
        rec = "APPLY_MODERATELY"
    elif clamped_score >= 50:
        rec = "STRETCH_ROLE"
    else:
        rec = "DO_NOT_APPLY"

    return clamped_score, rec


async def assess_job_posting(
    db: AsyncSession,
    job_description: str,
    candidate_skills: list[str] | None = None,
    candidate_cv: str | None = None,
    candidate_domain_breakdown: str | None = None,
    candidate_spoken_languages: str | None = None,
    candidate_years_of_experience: float | None = None,
    programmatic_baseline: int | None = None,
    matched_skills_count: int | None = None,
    total_required_skills_count: int | None = None,
    matching_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
) -> JobAssessmentResult:
    """
    Evaluates a job posting / JD against candidate CV for pre-application qualification,
    strict terminology gap mapping, spoken language compatibility audit, and granular resume tailoring strategy.
    """
    llm = await get_task_chat_model(db, task_type="ASSESSMENT", temperature=0.0)
    structured_llm = llm.with_structured_output(
        JobAssessmentResult, method="json_schema"
    )

    template_str = await get_prompt_template(db, "assessment")
    prompt = ChatPromptTemplate.from_template(template_str)

    skills_text = ", ".join(candidate_skills) if candidate_skills else "None provided"
    matching_skills_text = (
        ", ".join(matching_skills) if matching_skills else "None explicitly matched"
    )
    missing_skills_text = (
        ", ".join(missing_skills) if missing_skills else "None identified"
    )
    domain_text = candidate_domain_breakdown or "None provided"
    spoken_langs_text = candidate_spoken_languages or "English (Fluent)"
    years_exp_text = (
        f"{candidate_years_of_experience:.1f} years"
        if candidate_years_of_experience is not None
        else "Not explicitly verified"
    )
    capped_jd = sanitize_and_cap_jd(job_description, max_tokens=1500)
    capped_cv = (
        truncate_text_semantically(candidate_cv, max_chars=5000)
        if candidate_cv
        else "No CV provided"
    )
    cv_text = capped_cv

    chain = prompt | structured_llm
    try:
        result = await chain.ainvoke(
            {
                "job_description": capped_jd,
                "candidate_cv": cv_text,
                "candidate_domain_breakdown": domain_text,
                "candidate_spoken_languages": spoken_langs_text,
                "candidate_years_of_experience": years_exp_text,
                "candidate_skills": skills_text,
                "programmatic_baseline": str(
                    programmatic_baseline if programmatic_baseline is not None else 0
                ),
                "candidate_matching_skills": matching_skills_text,
                "candidate_missing_skills": missing_skills_text,
            },
            config={"callbacks": [PostgresTracer()]},
        )
    except Exception as exc:
        if is_context_size_error(exc):
            logger.warning(
                "Context size exceeded during assess_job_posting (JD: %d chars, CV: %d chars). Retrying with emergency compact payload...",
                len(capped_jd),
                len(cv_text),
            )
            emergency_jd = sanitize_and_cap_jd(job_description, max_tokens=750)
            emergency_cv = (
                truncate_text_semantically(candidate_cv, max_chars=2500)
                if candidate_cv
                else "No CV provided"
            )
            result = await chain.ainvoke(
                {
                    "job_description": emergency_jd,
                    "candidate_cv": emergency_cv,
                    "candidate_domain_breakdown": domain_text,
                    "candidate_spoken_languages": spoken_langs_text,
                    "candidate_years_of_experience": years_exp_text,
                    "candidate_skills": skills_text,
                    "programmatic_baseline": str(
                        programmatic_baseline
                        if programmatic_baseline is not None
                        else 0
                    ),
                    "candidate_matching_skills": matching_skills_text,
                    "candidate_missing_skills": missing_skills_text,
                },
                config={"callbacks": [PostgresTracer()]},
            )
        else:
            raise

    if not isinstance(result, JobAssessmentResult):
        result = JobAssessmentResult.model_validate(result)

    # 1. Synchronize curated skills counts and calculate exact algorithmic coverage
    if matching_skills is not None or missing_skills is not None:
        result.matching_skills = matching_skills or []
        result.missing_skills = missing_skills or []
        result.matched_skills_count = (
            matched_skills_count
            if matched_skills_count is not None
            else len(result.matching_skills)
        )
        result.total_required_skills_count = (
            total_required_skills_count
            if total_required_skills_count is not None
            else (len(result.matching_skills) + len(result.missing_skills))
        )
        result.programmatic_match_score = programmatic_baseline
        effective_baseline = programmatic_baseline
    elif programmatic_baseline is not None:
        result.programmatic_match_score = programmatic_baseline
        result.matched_skills_count = matched_skills_count
        result.total_required_skills_count = total_required_skills_count
        effective_baseline = programmatic_baseline
    else:
        curated_matched = len(result.matching_skills) if result.matching_skills else 0
        curated_missing = len(result.missing_skills) if result.missing_skills else 0
        curated_total = curated_matched + curated_missing

        if curated_total > 0:
            result.matched_skills_count = curated_matched
            result.total_required_skills_count = curated_total
            effective_baseline = int(round((curated_matched / curated_total) * 100))
            result.programmatic_match_score = effective_baseline
        else:
            result.programmatic_match_score = None
            result.matched_skills_count = None
            result.total_required_skills_count = None
            effective_baseline = None

    # 2. Auto-guard critical risks for underqualification or significant missing skills
    result.critical_risks = _sanitize_critical_risks(result.critical_risks)
    if (
        result.seniority_fit
        and result.seniority_fit.upper() == "UNDERQUALIFIED"
        and not any(
            "seniority" in r.lower() or "experience" in r.lower()
            for r in result.critical_risks
        )
    ):
        exp_str = (
            f" ({candidate_years_of_experience:.1f} yrs)"
            if candidate_years_of_experience is not None
            else ""
        )
        result.critical_risks.append(
            f"Seniority deficit: Candidate verified experience{exp_str} is below role requirements."
        )
    if (
        result.missing_skills
        and result.fit_score < 75
        and len(result.critical_risks) == 0
    ):
        result.critical_risks.append(
            f"Missing core technical prerequisites: {', '.join(result.missing_skills[:3])}."
        )

    # 3. Mathematically calibrate score and recommendation against effective baseline
    calibrated_score, calibrated_rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=result.fit_score,
        programmatic_baseline=effective_baseline,
        critical_risks=result.critical_risks,
        seniority_fit=result.seniority_fit,
        total_required_skills=result.total_required_skills_count,
    )
    result.fit_score = calibrated_score
    result.recommendation = calibrated_rec

    # Synthesize fallback markdown_report if model omitted it
    if not result.markdown_report:
        report_lines = [
            f"# Job Match Analysis: {result.fit_score}%",
            "",
            "## 📊 Match Summary",
            result.match_summary
            or result.summary
            or "Evaluation completed against candidate profile.",
        ]
        if result.critical_risks:
            report_lines.extend(
                [
                    "",
                    "## ⚠️ Critical Hiring Risks & Recruiter Hesitations",
                ]
            )
            for risk in result.critical_risks:
                report_lines.append(f"* **Risk:** {risk}")

        report_lines.extend(
            [
                "",
                "## ✅ Hard Matches (Your Strengths)",
                f"* **Keyword Match Rate:** {result.hard_matches.keyword_match_rate if result.hard_matches else f'{len(result.matching_skills)} core skills found'}",
                f"* **Top Alignment:** {', '.join(result.hard_matches.top_alignment) if result.hard_matches and result.hard_matches.top_alignment else ', '.join(result.matching_skills[:3]) if result.matching_skills else 'Strong core profile alignment'}",
                "",
                "## ❌ Optimization Gaps (Strict Terminology Mismatches)",
            ]
        )
        if result.optimization_gaps:
            if result.optimization_gaps.missing_completely:
                report_lines.append(
                    f"* **Missing Completely:** {', '.join(result.optimization_gaps.missing_completely)}"
                )
            if result.optimization_gaps.vocabulary_mismatches:
                report_lines.append(
                    f"* **Vocabulary Mismatches:** {', '.join(result.optimization_gaps.vocabulary_mismatches)}"
                )
            if result.optimization_gaps.experience_mismatch:
                report_lines.append(
                    f"* **Experience Delta:** {result.optimization_gaps.experience_mismatch}"
                )
        elif result.missing_skills:
            report_lines.append(
                f"* **Missing Requirements:** {', '.join(result.missing_skills)}"
            )

        report_lines.extend(
            [
                "",
                "## 💡 Step-by-Step Resume Tailoring Strategy",
            ]
        )
        if result.tailoring_strategy:
            if result.tailoring_strategy.vocabulary_translation:
                report_lines.append("### Vocabulary Translation:")
                for vt in result.tailoring_strategy.vocabulary_translation:
                    report_lines.append(
                        f"* Swap **'{vt.cv_term}'** → **'{vt.jd_term}'**: {vt.replacement_guidance}"
                    )
            if result.tailoring_strategy.impact_reframing:
                report_lines.append("### Impact Reframing:")
                for ir in result.tailoring_strategy.impact_reframing:
                    report_lines.append(f"* **Original:** {ir.bullet_point}")
                    report_lines.append(
                        f"  **Suggested Rewrite:** {ir.suggested_rewrite}"
                    )
                    report_lines.append(f"  *Rationale:* {ir.reason}")
            if result.tailoring_strategy.structural_adjustments:
                report_lines.append("### Structural Adjustments:")
                for sa in result.tailoring_strategy.structural_adjustments:
                    report_lines.append(f"* {sa}")
        result.markdown_report = "\n".join(report_lines)

    # Ensure salary fields and salary_period are populated
    from app.services.compensation_parser import _detect_period, parse_compensation_text

    if result.salary_min is None and result.salary_max is None:
        parsed_comp = parse_compensation_text(job_description)
        if parsed_comp.get("salary_min") or parsed_comp.get("salary_max"):
            result.salary_min = parsed_comp.get("salary_min")
            result.salary_max = parsed_comp.get("salary_max")
            if parsed_comp.get("currency"):
                result.currency = parsed_comp["currency"]
            if parsed_comp.get("salary_period") != "NOT_SPECIFIED":
                result.salary_period = parsed_comp["salary_period"]
    elif not result.salary_period or result.salary_period == "NOT_SPECIFIED":
        result.salary_period = _detect_period(
            job_description, num_sample=result.salary_max or result.salary_min
        )

    return result


def build_application_company_context(
    company_research: dict[str, Any] | None,
) -> str:
    """Selects a small, application-safe subset of company research."""
    if not company_research:
        return ""

    bullets: list[str] = []
    field_labels = (
        ("company_mission_and_customer", "Mission and Customers"),
        ("summary", "Mission and Products"),
        ("products_and_technical_domain", "Products and Technical Domains"),
        ("engineering_culture", "Engineering Signals"),
        ("strategic_priorities", "Strategic Priorities"),
        ("recent_initiatives", "Recent Verified Initiative"),
        ("language_to_mirror", "Company Language"),
    )
    used_labels: set[str] = set()
    for field_name, label in field_labels:
        value = company_research.get(field_name)
        if not value or label in used_labels:
            continue
        if isinstance(value, list):
            value = "; ".join(str(item) for item in value[:5] if item)
        if value:
            bullets.append(f"- {label}: {value}")
            used_labels.add(label)

    for fact in company_research.get("verified_facts", [])[:3]:
        if (
            isinstance(fact, dict)
            and fact.get("fact")
            and fact.get("confidence", "low") in {"medium", "high"}
        ):
            bullets.append(f"- Verified Fact: {fact['fact']}")

    if not bullets:
        return ""
    return (
        "Verified Company Intelligence - Application-Safe Context (use only when directly relevant to the role):\n"
        + "\n".join(bullets)
        + "\nDo not mention employee signals, public ratings, or unsupported hypotheses."
    )


async def generate_cover_letter(
    db: AsyncSession,
    company_name: str,
    position: str,
    job_description: str,
    candidate_cv: str,
    tone: str | None = "professional",
    length: str | None = None,
    custom_instructions: str | None = None,
    company_research: dict[str, Any] | None = None,
) -> str:
    """
    Generates a tailored cover letter using the COVER_LETTER task type and PostgresTracer.
    Supports optional grounded company research context for authentic company hooks.
    Returns the cover letter markdown string.
    """
    from app.core.config_manager import get_setting

    cleaned_jd = truncate_text_semantically(job_description)
    cleaned_cv = truncate_text_semantically(candidate_cv)
    if not tone:
        tone = await get_setting("COVER_LETTER_TONE", "professional", db=db)
    tone_str = (tone or "professional").strip().lower()

    if not length:
        length = await get_setting("COVER_LETTER_LENGTH", "standard", db=db)
    length_code = str(length or "standard").strip().lower()

    length_map = {
        "concise": "Concise (STRICT LIMIT: 120 to 180 words total)",
        "standard": "Standard (STRICT LIMIT: 250 to 320 words total)",
        "detailed": "Detailed (STRICT LIMIT: 380 to 450 words total)",
    }
    length_formatted = length_map.get(
        length_code,
        f"{length_code.capitalize()} length (STRICT LIMIT: 250 to 320 words total)",
    )

    instructions_parts = []
    if custom_instructions and custom_instructions.strip():
        instructions_parts.append(
            f"Custom User Instructions: {custom_instructions.strip()}"
        )

    company_context = build_application_company_context(company_research)
    if company_context:
        instructions_parts.append(
            company_context
            + "\n(Directive: Connect candidate motivations authentically to these company facts. Do NOT invent company achievements or candidate skills.)"
        )

    instructions_str = (
        ("\n" + "\n\n".join(instructions_parts)) if instructions_parts else ""
    )

    async with trace_operation(
        category="llm",
        name="generate_cover_letter",
        inputs={
            "company_name": company_name,
            "position": position,
            "tone": tone_str,
            "length": length_code,
            "jd_length": len(cleaned_jd),
            "cv_length": len(cleaned_cv),
            "has_company_research": bool(company_research),
        },
        db=db,
    ) as trace_ctx:
        llm = await get_task_chat_model(db, task_type="COVER_LETTER", temperature=0.15)
        template_str = await get_prompt_template(db, "cover_letter")
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert executive resume and cover letter writer. "
                        "Write a compelling, concise, and professional cover letter tailored to the target role and company using the candidate's CV. "
                        "STRICT GROUNDING DIRECTIVE: Strictly adhere to facts, roles, and accomplishments in the candidate's CV. "
                        "Never fabricate unmentioned projects, companies, tools, metrics, or client situations."
                    ),
                ),
                ("human", template_str),
            ]
        )

        chain = prompt | llm
        response = await chain.ainvoke(
            {
                "company_name": company_name or "Target Company",
                "position": position or "Target Role",
                "job_description": cleaned_jd or "No detailed description provided.",
                "candidate_cv": cleaned_cv or "No CV provided.",
                "tone": tone_str,
                "length": length_formatted,
                "custom_instructions": instructions_str,
            },
            config={"callbacks": [PostgresTracer()]},
        )

        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                [c.get("text", "") if isinstance(c, dict) else str(c) for c in content]
            )

        trace_ctx["outputs"] = {"cover_letter_length": len(content)}
        return content.strip()


async def generate_application_answers(
    db: AsyncSession,
    company_name: str,
    position: str,
    job_description: str,
    candidate_cv: str,
    questions: list[dict[str, Any]],
    tone: str | None = "professional",
    custom_instructions: str | None = None,
    company_research: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Generates strictly grounded answers to application form questions using APPLICATION_QA task type.
    Returns a list of dicts with {"id": ..., "question": ..., "word_limit": ..., "answer": ..., "status": ..., "updated_at": ...}.
    """
    if not questions:
        return []

    cleaned_jd = truncate_text_semantically(job_description)
    cleaned_cv = truncate_text_semantically(candidate_cv)
    tone_str = (tone or "professional").strip().lower()

    questions_payload = []
    for q in questions:
        q_item: dict[str, Any] = {
            "id": q.get("id") or f"q_{uuid4().hex[:8]}",
            "question": q.get("question", ""),
        }
        if q.get("word_limit"):
            q_item["word_limit"] = q["word_limit"]
        questions_payload.append(q_item)

    questions_json_str = json.dumps(questions_payload, indent=2)

    instructions_str = (
        f"\nCustom User Instructions: {custom_instructions.strip()}"
        if custom_instructions and custom_instructions.strip()
        else ""
    )

    company_research_str = build_application_company_context(company_research)

    async with trace_operation(
        category="llm",
        name="generate_application_answers",
        inputs={
            "company_name": company_name,
            "position": position,
            "tone": tone_str,
            "questions_count": len(questions_payload),
            "jd_length": len(cleaned_jd),
            "cv_length": len(cleaned_cv),
            "has_company_research": bool(company_research),
        },
        db=db,
    ) as trace_ctx:
        llm = await get_task_chat_model(db, task_type="APPLICATION_QA", temperature=0.0)
        template_str = await get_prompt_template(db, "application_qa")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert career strategist and recruiter. Write concise, compelling, and strictly factual answers "
                        "to application form questions. Derive all facts, metrics, and experiences strictly from the candidate's CV. "
                        "Never fabricate unmentioned technologies, achievements, or stories. Output strict JSON array."
                    ),
                ),
                ("human", template_str),
            ]
        )

        chain = prompt | llm
        response = await chain.ainvoke(
            {
                "company_name": company_name or "Target Company",
                "position": position or "Target Role",
                "company_research_context": company_research_str,
                "job_description": cleaned_jd or "No detailed description provided.",
                "candidate_cv": cleaned_cv or "No CV provided.",
                "questions_json": questions_json_str,
                "tone": tone_str,
                "custom_instructions": instructions_str,
            },
            config={"callbacks": [PostgresTracer()]},
        )

        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                [c.get("text", "") if isinstance(c, dict) else str(c) for c in content]
            )

        # Parse JSON output
        parsed_answers: list[dict[str, Any]] = []
        cleaned_content = content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()

        try:
            raw_parsed = json.loads(cleaned_content)
            if isinstance(raw_parsed, list):
                parsed_answers = raw_parsed
            elif (
                isinstance(raw_parsed, dict)
                and "questions" in raw_parsed
                and isinstance(raw_parsed["questions"], list)
            ):
                parsed_answers = raw_parsed["questions"]
            elif (
                isinstance(raw_parsed, dict)
                and "answers" in raw_parsed
                and isinstance(raw_parsed["answers"], list)
            ):
                parsed_answers = raw_parsed["answers"]
            elif isinstance(raw_parsed, dict):
                parsed_answers = [raw_parsed]
        except Exception as parse_err:
            logger.warning(
                "Failed to parse JSON for application QA: %s. Content: %s",
                parse_err,
                cleaned_content,
            )
            parsed_answers = [
                {
                    "id": q.get("id"),
                    "question": q.get("question"),
                    "answer": cleaned_content,
                }
                for q in questions_payload
            ]

        # Merge back into original question objects
        merged_results = []
        now_iso = datetime.now(UTC).isoformat()
        answer_by_id = {
            str(a.get("id")): a.get("answer", "")
            for a in parsed_answers
            if isinstance(a, dict)
        }
        answer_by_q = {
            str(a.get("question")): a.get("answer", "")
            for a in parsed_answers
            if isinstance(a, dict)
        }

        for q in questions_payload:
            q_id = str(q.get("id"))
            q_text = str(q.get("question"))
            ans = answer_by_id.get(q_id) or answer_by_q.get(q_text) or ""
            merged_results.append(
                {
                    "id": q_id,
                    "question": q_text,
                    "word_limit": q.get("word_limit"),
                    "answer": ans,
                    "status": "GENERATED" if ans else "DRAFT",
                    "updated_at": now_iso,
                }
            )

        trace_ctx["outputs"] = {
            "questions_answered": len(merged_results),
            "success_count": sum(1 for m in merged_results if m.get("answer")),
        }
        return merged_results


async def anonymize_and_parse_cv(
    db: AsyncSession, raw_cv_text: str
) -> CVAnonymizationResult:
    """
    De-identifies candidate resume:
    - Runs local programmatic regex pre-scrubber on emails, phones, URLs, addresses, and candidate name.
    - Sends pre-scrubbed text to LLM to convert dates to duration windows and replace companies with scale tags.
    - Extracts canonical technical skills, domain expertise, core competencies, and calculated total years of experience.
    """
    from app.services.scrubber import programmatic_scrub_cv

    pre_scrubbed_text, stats = programmatic_scrub_cv(raw_cv_text)
    logger.info(
        "Local PII pre-scrubbing complete before AI dispatch: %d emails, %d phones, %d urls, %d addresses redacted",
        stats.get("emails", 0),
        stats.get("phones", 0),
        stats.get("urls", 0),
        stats.get("addresses", 0),
    )

    llm = await get_task_chat_model(db, task_type="EXTRACTION", temperature=0.2)
    structured_llm = llm.with_structured_output(
        CVAnonymizationResult, method="json_schema"
    )
    template_str = await get_prompt_template(db, "cv_anonymization")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an expert resume privacy officer and talent analyst. "
                    "Completely de-identify the candidate resume: redact contacts and real names, convert dates to relative duration windows, "
                    "and replace company names with industry/scale tags while extracting canonical skills, domain expertise, and core competencies."
                ),
            ),
            ("human", template_str),
        ]
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke(
        {"resume_text": pre_scrubbed_text},
        config={"callbacks": [PostgresTracer()]},
    )
    if isinstance(result, CVAnonymizationResult):
        return result
    return CVAnonymizationResult.model_validate(result)


async def generate_embedding(
    db: AsyncSession,
    text_input: str,
    embeddings_model: Any | None = None,
) -> list[float]:
    """Reject embedding generation while vector embeddings are disabled."""
    raise RuntimeError("Vector embeddings are disabled.")


async def generate_and_save_application_embedding(
    db: AsyncSession,
    application_id: int,
    skip_llm_summary: bool = True,
) -> ApplicationEmbeddingModel | None:
    """Embedding persistence is disabled; keep this compatibility hook as a no-op."""
    return None


async def async_enqueue_application_embedding(
    application_id: int,
    skip_llm_summary: bool = True,
) -> None:
    """Embedding tasks are disabled; retain a no-op for legacy call sites."""
    return None
