import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.llm_factory import (
    get_active_llm_config_dict,
    get_task_chat_model,
    get_task_embeddings_model,
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

logger = logging.getLogger(__name__)


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
    llm = await get_task_chat_model(db, task_type="JD_EXTRACTION", temperature=0.0)
    structured_llm = llm.with_structured_output(ExtractedJobSpec)
    template_str = await get_prompt_template(db, "jd_extraction")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an expert recruitment data analyst. "
                    "Extract essential job details from raw scraped webpage markdown text or pasted specs. "
                    "Disregard navigation, cookie popups, footers, headers, ads, or legal notices. "
                    "If no job vacancy is found, set job_found to false and leave fields as 'Not Specified'."
                ),
            ),
            ("human", template_str),
        ]
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke(
        {
            "raw_webpage_data": raw_webpage_data,
            "email_content": raw_webpage_data,
        }
    )

    if not isinstance(result, ExtractedJobSpec):
        result = ExtractedJobSpec.model_validate(result)
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
    structured_llm = llm.with_structured_output(EmailExtractionResult)
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
    result = await chain.ainvoke({"email_content": formatted_content})
    if isinstance(result, EmailExtractionResult):
        return result
    return EmailExtractionResult.model_validate(result)


async def assess_job_posting(
    db: AsyncSession,
    job_description: str,
    candidate_skills: list[str] | None = None,
    candidate_cv: str | None = None,
    candidate_domain_breakdown: str | None = None,
    programmatic_baseline: int = 0,
) -> JobAssessmentResult:
    """
    Evaluates a job posting / JD against candidate CV for pre-application qualification,
    strict terminology gap mapping, and granular resume tailoring strategy.
    """
    llm = await get_task_chat_model(db, task_type="ASSESSMENT", temperature=0.2)
    structured_llm = llm.with_structured_output(JobAssessmentResult)
    template_str = await get_prompt_template(db, "assessment")

    cv_text = candidate_cv
    if not cv_text:
        skills_str = (
            ", ".join(candidate_skills)
            if candidate_skills
            else "General Full-Stack / Software Engineering Profile"
        )
        cv_text = f"Candidate Technical Skills:\n{skills_str}"

    domain_text = (
        candidate_domain_breakdown
        or "General / Full-Stack Experience (No active domain constraints)"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an expert technical resume writer and career coach. "
                    "Perform a granular, data-driven audit of the candidate's resume against the job description. "
                    "Never suggest skills not in the CV. Translate exact vocabulary synonyms, quantify match rate, and reframe bullet points."
                ),
            ),
            ("human", template_str),
        ]
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke(
        {
            "job_description": job_description,
            "candidate_cv": cv_text,
            "candidate_domain_breakdown": domain_text,
            "programmatic_baseline": str(programmatic_baseline),
        }
    )

    if not isinstance(result, JobAssessmentResult):
        result = JobAssessmentResult.model_validate(result)

    result.programmatic_match_score = programmatic_baseline

    # Synthesize fallback markdown_report if model omitted it
    if not result.markdown_report:
        report_lines = [
            f"# Job Match Analysis: {result.fit_score}%",
            "",
            "## 📊 Match Summary",
            result.match_summary
            or result.summary
            or "Evaluation completed against candidate profile.",
            "",
            "## ✅ Hard Matches (Your Strengths)",
            f"* **Keyword Match Rate:** {result.hard_matches.keyword_match_rate if result.hard_matches else f'{len(result.matching_skills)} core skills found'}",
            f"* **Top Alignment:** {', '.join(result.hard_matches.top_alignment) if result.hard_matches and result.hard_matches.top_alignment else ', '.join(result.matching_skills[:3]) if result.matching_skills else 'Strong core profile alignment'}",
            "",
            "## ❌ Optimization Gaps (Strict Terminology Mismatches)",
        ]
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
    structured_llm = llm.with_structured_output(CVAnonymizationResult)
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
    result = await chain.ainvoke({"resume_text": pre_scrubbed_text})
    if isinstance(result, CVAnonymizationResult):
        return result
    return CVAnonymizationResult.model_validate(result)


async def summarize_application_status(
    db: AsyncSession, events_timeline: list[dict[str, Any]]
) -> ApplicationSummaryResult:
    """Synthesizes a narrative status snapshot from timeline events using LangChain SUMMARIZATION model."""
    llm = await get_task_chat_model(db, task_type="SUMMARIZATION", temperature=0.1)
    structured_llm = llm.with_structured_output(ApplicationSummaryResult)
    events_str = json.dumps(events_timeline, indent=2)
    template_str = await get_prompt_template(db, "summarization")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You summarize job application timelines for embeddings."),
            ("human", template_str),
        ]
    )

    chain = prompt | structured_llm
    result = await chain.ainvoke({"events_str": events_str})
    if isinstance(result, ApplicationSummaryResult):
        return result
    return ApplicationSummaryResult.model_validate(result)


async def generate_embedding(db: AsyncSession, text_input: str) -> list[float]:
    """Generates vector embedding for input text using configured LangChain EMBEDDING model."""
    if isinstance(text_input, str):
        cleaned_text = text_input.strip()
    elif isinstance(text_input, (dict, list)):
        cleaned_text = json.dumps(text_input)
    else:
        cleaned_text = str(text_input).strip() if text_input is not None else ""

    if not cleaned_text:
        cleaned_text = "Job Application"

    embeddings = await get_task_embeddings_model(db)

    # Local OpenAI-compatible servers (such as LM Studio / Ollama) often strictly require
    # an array of strings in the 'input' JSON payload (e.g. {"input": ["..."], "model": "..."}).
    # Trying aembed_documents([cleaned_text]) first satisfies array input requirement.
    try:
        doc_vectors = await embeddings.aembed_documents([cleaned_text])
        if doc_vectors and len(doc_vectors) > 0 and len(doc_vectors[0]) > 0:
            return doc_vectors[0]
    except Exception as doc_err:
        logger.debug(
            "aembed_documents attempt failed, trying aembed_query: %s", doc_err
        )

    return await embeddings.aembed_query(cleaned_text)


async def generate_nudge_email(db: AsyncSession, application_id: int) -> str | None:
    """Generates a nudge email using the 'email_nudge_draft' prompt template."""
    stmt = (
        select(ApplicationModel)
        .options(selectinload(ApplicationModel.company))
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    application = res.scalar_one_or_none()

    if not application:
        return None

    llm = await get_task_chat_model(db, task_type="SUMMARIZATION", temperature=0.7)
    template_str = await get_prompt_template(db, "email_nudge_draft")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template_str),
        ]
    )
    chain = prompt | llm
    result = await chain.ainvoke({
        "company": application.company.name if application.company else "the company",
        "position": application.position or "the role",
        "status": application.status
    })

    return result.content if hasattr(result, "content") else str(result)

async def generate_email_reply_draft(db: AsyncSession, action_item_id: int) -> str | None:
    """Generates a draft reply to an email associated with an action item."""
    from app.models.applications import ActionItemModel

    stmt = (
        select(ActionItemModel)
        .options(
            selectinload(ActionItemModel.event),
            selectinload(ActionItemModel.application).selectinload(ApplicationModel.company)
        )
        .where(ActionItemModel.id == action_item_id)
    )
    res = await db.execute(stmt)
    action_item = res.scalar_one_or_none()

    if not action_item or not action_item.application:
        return None

    application = action_item.application
    email_event = action_item.event

    if not email_event:
        # If no specific event is linked, try to get the latest event with action_required
        events_stmt = (
            select(ApplicationEventModel)
            .where(ApplicationEventModel.email_application_id == application.id)
            .where(ApplicationEventModel.email_action_required == True)
            .order_by(ApplicationEventModel.email_received_at.desc())
        )
        events_res = await db.execute(events_stmt)
        email_event = events_res.scalar_one_or_none()

    if not email_event:
        return None

    # Get candidate profile context
    profile_stmt = select(CandidateProfileModel).where(CandidateProfileModel.is_active == True)
    profile_res = await db.execute(profile_stmt)
    profile = profile_res.scalar_one_or_none()

    profile_text = "No profile available."
    if profile:
        profile_text = f"Summary: {profile.summary}\nSkills: {profile.extracted_skills}\nExperience: {profile.years_of_experience} years"

    email_content = email_event.email_raw_body or email_event.email_summary or "No email content"

    llm = await get_task_chat_model(db, task_type="SUMMARIZATION", temperature=0.7)
    template_str = await get_prompt_template(db, "email_reply_draft")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template_str),
        ]
    )
    chain = prompt | llm
    result = await chain.ainvoke({
        "company": application.company.name if application.company else "the company",
        "position": application.position or "the role",
        "email_content": email_content,
        "candidate_profile": profile_text
    })

    return result.content if hasattr(result, "content") else str(result)


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

    vector = await generate_embedding(db, str(content_to_embed))

    emb_stmt = select(ApplicationEmbeddingModel).where(
        ApplicationEmbeddingModel.email_application_id == application_id
    )
    emb_res = await db.execute(emb_stmt)
    embedding_record = emb_res.scalar_one_or_none()

    metadata_payload = {
        "company": comp_name,
        "position": application.position,
        "status": application.status,
        "updated_at": application.updated_at.isoformat()
        if application.updated_at
        else None,
    }

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

    if not get_setting("ENABLE_EMBEDDINGS", True):
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
        async with AsyncSessionLocal() as processing_session:
            # 3. Update to Processing
            db_task = await processing_session.get(IntakeEvaluationTaskModel, task_id)
            if db_task:
                db_task.status = "PROCESSING"
                db_task.stage = "EMBEDDING"
                await processing_session.commit()

            try:
                await generate_and_save_application_embedding(
                    processing_session,
                    application_id=application_id,
                    skip_llm_summary=skip_llm_summary,
                )
                logger.info(
                    "Background vector embedding updated for Application ID %d",
                    application_id,
                )

                # 4. On Success: Complete
                if db_task:
                    db_task.status = "COMPLETED"
                    db_task.stage = "COMPLETE"
                    await processing_session.commit()
            except Exception as err:
                logger.warning(
                    "Background vector embedding failed for Application ID %d: %s",
                    application_id,
                    err,
                )

                # 5. On Failure
                if db_task:
                    db_task.status = "FAILED"
                    db_task.error_message = str(err)
                    await processing_session.commit()
