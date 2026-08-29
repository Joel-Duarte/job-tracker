import json
import logging
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.llm_factory import (
    get_active_llm_config_dict,
    get_task_chat_model,
    get_task_embeddings_model,
    strip_reasoning_tags,
)
from app.core.prompts import get_prompt_template
from app.models.applications import ApplicationEmbeddingModel, ApplicationModel
from app.schemas.candidate_profile import CVAnonymizationResult
from app.schemas.llm import (
    ApplicationSummaryResult,
    EmailExtractionResult,
    ExtractedJobSpec,
    JobAssessmentResult,
)
from app.services.postgres_tracer import PostgresTracer
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)


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


def truncate_text_semantically(text: str, max_chars: int = 12000) -> str:
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
) -> ExtractedJobSpec:
    """
    Stage 1: Extracts structured job specs, responsibilities, requirements, and ATS keywords from raw webpage data.
    Uses JD_EXTRACTION task binding with temperature=0.0 and reasoning disabled.
    """
    cleaned_data = truncate_text_semantically(raw_webpage_data)
    async with trace_operation(
        category="llm",
        name="extract_job_spec",
        inputs={
            "char_count": len(cleaned_data),
            "sample": cleaned_data[:200],
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
        result = await chain.ainvoke(
            {
                "raw_webpage_data": cleaned_data,
                "email_content": cleaned_data,
            },
            config={"callbacks": [PostgresTracer()]},
        )

        if not isinstance(result, ExtractedJobSpec):
            result = ExtractedJobSpec.model_validate(result)

        trace_ctx["outputs"] = {
            "job_found": result.job_found,
            "company": result.company,
            "position": result.position,
            "responsibilities_count": len(result.responsibilities),
            "requirements_count": len(result.requirements),
            "extracted_skills": result.extracted_skills,
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
                "You are an information extraction engine for recruitment emails. Return only valid structured data.",
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
    return res_obj


def calibrate_assessment_score_and_recommendation(
    raw_fit_score: int,
    programmatic_baseline: int | None,
    critical_risks: list[str] | None = None,
    seniority_fit: str | None = None,
) -> tuple[int, str]:
    """
    Applies mathematical bounding and recommendation synchronization to eliminate
    AI grade inflation:
    1. If programmatic_baseline is present: Clamps AI fit score to [max(10, baseline - 25), min(100, baseline + 25)].
    2. If programmatic_baseline is None (0 JD skills extractable): Caps score at max 70.
    3. If seniority_fit is UNDERQUALIFIED: Caps score at max 65.
    4. Synchronizes recommendation:
       - APPLY_STRONGLY: fit_score >= 85 and 0 critical risks and seniority_fit != 'UNDERQUALIFIED'
       - APPLY_MODERATELY: fit_score >= 70 and len(critical_risks) <= 1 and seniority_fit != 'UNDERQUALIFIED'
       - STRETCH_ROLE: fit_score >= 50 (or has critical risks / seniority deficit)
       - DO_NOT_APPLY: fit_score < 50
    """
    # 1. Mathematical clamp
    if programmatic_baseline is not None:
        min_bound = max(10, programmatic_baseline - 25)
        max_bound = min(100, programmatic_baseline + 25)
        clamped_score = max(min_bound, min(max_bound, raw_fit_score))
    else:
        clamped_score = min(70, max(10, raw_fit_score))

    # 2. Hard penalty for seniority gap
    if seniority_fit and seniority_fit.upper() == "UNDERQUALIFIED":
        clamped_score = min(65, clamped_score)

    # 3. Synchronize recommendation tier
    num_risks = len(critical_risks or [])
    is_underqualified = bool(
        seniority_fit and seniority_fit.upper() == "UNDERQUALIFIED"
    )
    if clamped_score >= 85 and num_risks == 0 and not is_underqualified:
        rec = "APPLY_STRONGLY"
    elif clamped_score >= 70 and num_risks <= 1 and not is_underqualified:
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
    candidate_core_competencies: list[str] | None = None,
    programmatic_baseline: int | None = None,
    matched_skills_count: int | None = None,
    total_required_skills_count: int | None = None,
) -> JobAssessmentResult:
    """
    Evaluates a job posting / JD against candidate CV for pre-application qualification,
    strict terminology gap mapping, spoken language compatibility audit, and granular resume tailoring strategy.
    """
    llm = await get_task_chat_model(db, task_type="ASSESSMENT", temperature=0.2)
    structured_llm = llm.with_structured_output(
        JobAssessmentResult,
        method="json_mode"
        if "anthropic" in type(llm).__name__.lower()
        else "function_calling",
    )

    template_str = await get_prompt_template(db, "assessment")
    prompt = ChatPromptTemplate.from_template(template_str)

    skills_text = ", ".join(candidate_skills) if candidate_skills else "None provided"
    domain_text = candidate_domain_breakdown or "None provided"
    spoken_langs_text = candidate_spoken_languages or "English (Fluent)"
    years_exp_text = (
        f"{candidate_years_of_experience:.1f} years"
        if candidate_years_of_experience is not None
        else "Not explicitly verified"
    )
    competencies_text = (
        ", ".join(candidate_core_competencies)
        if candidate_core_competencies
        else "None provided"
    )
    cv_text = candidate_cv or "No CV provided"

    chain = prompt | structured_llm
    result = await chain.ainvoke(
        {
            "job_description": job_description,
            "candidate_cv": cv_text,
            "candidate_domain_breakdown": domain_text,
            "candidate_spoken_languages": spoken_langs_text,
            "candidate_years_of_experience": years_exp_text,
            "candidate_skills": skills_text,
            "candidate_core_competencies": competencies_text,
            "programmatic_baseline": str(
                programmatic_baseline if programmatic_baseline is not None else 0
            ),
        },
        config={"callbacks": [PostgresTracer()]},
    )

    if not isinstance(result, JobAssessmentResult):
        result = JobAssessmentResult.model_validate(result)

    calibrated_score, calibrated_rec = calibrate_assessment_score_and_recommendation(
        raw_fit_score=result.fit_score,
        programmatic_baseline=programmatic_baseline,
        critical_risks=result.critical_risks,
        seniority_fit=result.seniority_fit,
    )
    result.fit_score = calibrated_score
    result.recommendation = calibrated_rec

    result.programmatic_match_score = programmatic_baseline
    if matched_skills_count is not None:
        result.matched_skills_count = matched_skills_count
    elif result.matching_skills:
        result.matched_skills_count = len(result.matching_skills)

    if total_required_skills_count is not None:
        result.total_required_skills_count = total_required_skills_count
    elif result.matching_skills or result.missing_skills:
        result.total_required_skills_count = len(result.matching_skills) + len(
            result.missing_skills
        )

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

    return result


async def generate_cover_letter(
    db: AsyncSession,
    company_name: str,
    position: str,
    job_description: str,
    candidate_cv: str,
    tone: str | None = "professional",
    length: str | None = None,
    custom_instructions: str | None = None,
) -> str:
    """
    Generates a tailored cover letter using the COVER_LETTER task type and PostgresTracer.
    Returns the cover letter markdown string.
    """
    from app.core.config_manager import get_setting

    cleaned_jd = truncate_text_semantically(job_description)
    cleaned_cv = truncate_text_semantically(candidate_cv)
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

    instructions_str = (
        f"\nCustom User Instructions: {custom_instructions.strip()}"
        if custom_instructions and custom_instructions.strip()
        else ""
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
        },
        db=db,
    ) as trace_ctx:
        llm = await get_task_chat_model(db, task_type="COVER_LETTER", temperature=0.3)
        template_str = await get_prompt_template(db, "cover_letter")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an expert executive resume and cover letter writer. "
                        "Write a compelling, concise, and professional cover letter tailored to the target role and company using the candidate's CV. "
                        "Strictly adhere to the candidate's actual CV facts without inventing skills, metrics, histories, or tools."
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


async def summarize_application_status(
    db: AsyncSession, events_timeline: list[dict[str, Any]]
) -> ApplicationSummaryResult:
    """Synthesizes a narrative status snapshot from timeline events using LangChain SUMMARIZATION model."""
    llm = await get_task_chat_model(db, task_type="SUMMARIZATION", temperature=0.1)
    structured_llm = llm.with_structured_output(
        ApplicationSummaryResult, method="json_schema"
    )
    events_str = json.dumps(events_timeline, indent=2)
    template_str = await get_prompt_template(db, "summarization")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You summarize job application timelines for embeddings."),
            ("human", template_str),
        ]
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke(
        {"events_str": events_str},
        config={"callbacks": [PostgresTracer()]},
    )
    if isinstance(result, ApplicationSummaryResult):
        return result
    return ApplicationSummaryResult.model_validate(result)


async def generate_embedding(
    db: AsyncSession,
    text_input: str,
    embeddings_model: Any | None = None,
) -> list[float]:
    """Generates vector embedding for input text using configured LangChain EMBEDDING model."""
    if isinstance(text_input, str):
        cleaned_text = text_input.strip()
    elif isinstance(text_input, (dict, list)):
        cleaned_text = json.dumps(text_input)
    else:
        cleaned_text = str(text_input).strip() if text_input is not None else ""

    if not cleaned_text:
        cleaned_text = "Job Application"

    async with trace_operation(
        category="embedding",
        name="generate_embedding",
        inputs={"text_sample": cleaned_text[:200], "char_count": len(cleaned_text)},
    ) as ctx:
        embeddings = embeddings_model or await get_task_embeddings_model(db)

        # Local OpenAI-compatible servers (such as LM Studio / Ollama) often strictly require
        # an array of strings in the 'input' JSON payload (e.g. {"input": ["..."], "model": "..."}).
        # Trying aembed_documents([cleaned_text]) first satisfies array input requirement.
        try:
            doc_vectors = await embeddings.aembed_documents([cleaned_text])
            if doc_vectors and len(doc_vectors) > 0 and len(doc_vectors[0]) > 0:
                ctx["outputs"] = {
                    "dimensions": len(doc_vectors[0]),
                    "method": "aembed_documents",
                }
                return doc_vectors[0]
        except Exception as doc_err:
            logger.debug(
                "aembed_documents attempt failed, trying aembed_query: %s", doc_err
            )

        vector = await embeddings.aembed_query(cleaned_text)
        ctx["outputs"] = {"dimensions": len(vector), "method": "aembed_query"}
        return vector


async def generate_and_save_application_embedding(
    db: AsyncSession,
    application_id: int,
    skip_llm_summary: bool = True,
) -> ApplicationEmbeddingModel:
    """
    Creates or updates 768-dim vector embedding record for an application.
    Constructs the embedding directly from structured application metadata and the latest timeline event.
    """
    stmt = (
        select(ApplicationModel)
        .options(
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.company),
        )
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    application = res.scalar_one_or_none()

    if not application:
        raise ValueError(f"Application ID {application_id} not found.")

    comp_name = application.company.name if application.company else "Unknown Company"
    date_str = (
        application.application_date.strftime("%Y-%m-%d")
        if application.application_date
        else (
            application.created_at.strftime("%Y-%m-%d")
            if application.created_at
            else "Recent"
        )
    )

    # Resolve latest timeline event
    sorted_events = sorted(
        application.events or [],
        key=lambda e: e.email_received_at or e.id or 0,
        reverse=True,
    )
    latest_event = sorted_events[0] if sorted_events else None

    evt_date = (
        latest_event.email_received_at.strftime("%Y-%m-%d")
        if (latest_event and latest_event.email_received_at)
        else date_str
    )
    evt_type = latest_event.email_event_type if latest_event else "INITIAL_APPLICATION"
    evt_summary = (
        latest_event.email_summary
        if (latest_event and latest_event.email_summary)
        else "Application recorded."
    )
    action_info = (
        f"\nAction Required: {latest_event.email_action}"
        if (
            latest_event
            and latest_event.email_action_required
            and latest_event.email_action
        )
        else ""
    )

    content_to_embed = (
        f"Job Application: {application.position} at {comp_name}.\n"
        f"Status: {application.status}.\n"
        f"Latest Update ({evt_date}): [{evt_type}] {evt_summary}.{action_info}"
    )

    metadata_payload = {
        "company": comp_name,
        "position": application.position,
        "status": application.status,
        "updated_at": application.updated_at.isoformat()
        if application.updated_at
        else None,
    }

    # Resolve embedding model before network I/O
    embeddings_model = await get_task_embeddings_model(db)

    # Execute network call without holding active DB query in flight
    vector = await generate_embedding(
        db, str(content_to_embed), embeddings_model=embeddings_model
    )

    emb_stmt = select(ApplicationEmbeddingModel).where(
        ApplicationEmbeddingModel.email_application_id == application_id
    )
    emb_res = await db.execute(emb_stmt)
    embedding_record = emb_res.scalar_one_or_none()

    if not embedding_record:
        embedding_record = ApplicationEmbeddingModel(
            email_application_id=application_id,
            content=content_to_embed,
            metadata_=metadata_payload,
            embedding=vector,
        )
        db.add(embedding_record)
    else:
        embedding_record.content = content_to_embed
        embedding_record.metadata_ = metadata_payload
        embedding_record.embedding = vector

    await db.commit()
    return embedding_record


async def async_enqueue_application_embedding(
    application_id: int,
    skip_llm_summary: bool = True,
) -> None:
    """
    Non-blocking background worker task to generate and save application vector embeddings.
    Tracks state in IntakeEvaluationTaskModel and uses Priority 2 in the ConcurrencyManager.
    """
    from app.core.config_manager import get_setting

    if not await get_setting("ENABLE_EMBEDDINGS", True):
        logger.debug(
            f"Skipping vector embedding for app {application_id} (Embeddings Disabled)"
        )
        return

    from app.core.ai_queue import concurrency_manager
    from app.core.database import AsyncSessionLocal
    from app.models.ai_providers import AIProviderModel, AITaskBindingModel
    from app.models.intake_tasks import IntakeEvaluationTaskModel

    provider_id = None
    max_concurrency = 1
    task_id = None

    async with AsyncSessionLocal() as session:
        try:
            binding_stmt = (
                select(AITaskBindingModel, AIProviderModel)
                .join(
                    AIProviderModel,
                    AITaskBindingModel.provider_id == AIProviderModel.id,
                )
                .where(
                    AITaskBindingModel.task_type == "EMBEDDING",
                    AITaskBindingModel.is_active,
                    AIProviderModel.is_active,
                )
            )
            binding_res = await session.execute(binding_stmt)
            row = binding_res.first()
            if row:
                provider_id = row[1].id
                max_concurrency = row[1].max_concurrency or 1
        except Exception as err:
            logger.debug("Could not resolve EMBEDDING provider binding: %s", err)

        # 1. Create Queued Task Record
        new_task = IntakeEvaluationTaskModel(
            task_type="EMBEDDING",
            status="QUEUED",
            stage="QUEUED",
            title_hint=f"Application {application_id} Vector Embedding",
        )
        session.add(new_task)
        await session.commit()
        task_id = new_task.id

    # 2. Acquire Priority 2 Slot
    async with concurrency_manager.acquire(provider_id, max_concurrency, priority=2):
        # 3. Short transaction: Update to Processing
        async with AsyncSessionLocal() as session_proc:
            db_task = await session_proc.get(IntakeEvaluationTaskModel, task_id)
            if db_task:
                db_task.status = "PROCESSING"
                db_task.stage = "EMBEDDING"
                await session_proc.commit()

        try:
            # 4. Short transaction: Generate and persist embedding
            async with AsyncSessionLocal() as embedding_session:
                await generate_and_save_application_embedding(
                    embedding_session,
                    application_id=application_id,
                    skip_llm_summary=skip_llm_summary,
                )
            logger.info(
                "Background vector embedding updated for Application ID %d",
                application_id,
            )

            # 5. Short transaction: Mark as Completed
            async with AsyncSessionLocal() as session_done:
                db_task = await session_done.get(IntakeEvaluationTaskModel, task_id)
                if db_task:
                    db_task.status = "COMPLETED"
                    db_task.stage = "COMPLETE"
                    await session_done.commit()
        except Exception as err:
            logger.warning(
                "Background vector embedding failed for Application ID %d: %s",
                application_id,
                err,
            )

            # 6. Short transaction: Mark as Failed
            async with AsyncSessionLocal() as session_err:
                db_task = await session_err.get(IntakeEvaluationTaskModel, task_id)
                if db_task:
                    db_task.status = "FAILED"
                    db_task.error_message = str(err)
                    await session_err.commit()
