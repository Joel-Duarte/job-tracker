import json
import logging
from typing import Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.llm_factory import (
    get_active_llm_config_dict,
    get_chat_model,
    get_embeddings_model,
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
    Uses SCRAPER_PARSER task binding with temperature=0.0 and reasoning disabled.
    """
    llm = await get_task_chat_model(db, task_type="SCRAPER_PARSER", temperature=0.0)
    structured_llm = llm.with_structured_output(ExtractedJobSpec)
    template_str = await get_prompt_template(db, "jd_extraction")

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert recruitment data analyst. "
            "Extract essential job details from raw scraped webpage markdown text or pasted specs. "
            "Disregard navigation, cookie popups, footers, headers, ads, or legal notices. "
            "If no job vacancy is found, set job_found to false and leave fields as 'Not Specified'."
        )),
        ("human", template_str),
    ])

    chain = prompt | structured_llm
    result = await chain.ainvoke({"raw_webpage_data": raw_webpage_data})

    if not isinstance(result, ExtractedJobSpec):
        result = ExtractedJobSpec.model_validate(result)
    return result


async def extract_email_info(db: AsyncSession, email_content: str) -> EmailExtractionResult:
    """Extracts structured job application metadata from email body using LangChain EXTRACTION model."""
    llm = await get_task_chat_model(db, task_type="EXTRACTION", temperature=0.2)
    structured_llm = llm.with_structured_output(EmailExtractionResult)
    template_str = await get_prompt_template(db, "extraction")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You parse job application emails into structured data."),
        ("human", template_str),
    ])

    chain = prompt | structured_llm
    result = await chain.ainvoke({"email_content": email_content})
    if isinstance(result, EmailExtractionResult):
        return result
    return EmailExtractionResult.model_validate(result)


async def assess_job_posting(
    db: AsyncSession,
    job_description: str,
    candidate_skills: Optional[List[str]] = None,
    programmatic_baseline: int = 0,
) -> JobAssessmentResult:
    """Evaluates a job posting / JD for pre-application qualification and keyword fit."""
    llm = await get_task_chat_model(db, task_type="EXTRACTION", temperature=0.2)
    structured_llm = llm.with_structured_output(JobAssessmentResult)
    template_str = await get_prompt_template(db, "assessment")

    skills_str = ", ".join(candidate_skills) if candidate_skills else "General Full-Stack / Software Engineering Profile"

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You evaluate job descriptions and output structured pre-application assessments."),
        ("human", template_str),
    ])

    chain = prompt | structured_llm
    result = await chain.ainvoke({
        "job_description": job_description,
        "candidate_skills": skills_str,
        "programmatic_baseline": str(programmatic_baseline),
    })

    if not isinstance(result, JobAssessmentResult):
        result = JobAssessmentResult.model_validate(result)

    result.programmatic_match_score = programmatic_baseline
    return result


async def anonymize_and_parse_cv(db: AsyncSession, raw_cv_text: str) -> CVAnonymizationResult:
    """De-identifies candidate resume (scrubs names/companies, converts dates to durations, extracts skills)."""
    llm = await get_task_chat_model(db, task_type="EXTRACTION", temperature=0.2)
    structured_llm = llm.with_structured_output(CVAnonymizationResult)
    template_str = await get_prompt_template(db, "cv_anonymization")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You de-identify resumes and extract structured canonical skills."),
        ("human", template_str),
    ])

    chain = prompt | structured_llm
    result = await chain.ainvoke({"resume_text": raw_cv_text})
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

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You summarize job application timelines for embeddings."),
        ("human", template_str),
    ])

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
        logger.debug("aembed_documents attempt failed, trying aembed_query: %s", doc_err)

    return await embeddings.aembed_query(cleaned_text)


async def generate_and_save_application_embedding(
    db: AsyncSession,
    application_id: int,
    skip_llm_summary: bool = False,
) -> ApplicationEmbeddingModel:
    """
    Creates or updates 768-dim vector embedding record for an application.
    If skip_llm_summary is True (e.g. manual status transition, user apply, or non-email change),
    it generates the embedding directly from structured metadata without invoking the LLM.
    AI timeline summarization is reserved for real incoming email events.
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
        else (application.created_at.strftime("%Y-%m-%d") if application.created_at else "Recent")
    )

    has_email_events = any(getattr(e, "source_channel", "") == "EMAIL" for e in (application.events or []))

    content_to_embed = None

    # Only run LLM summarization if not skipped and there are actual email events
    if not skip_llm_summary and has_email_events:
        events_timeline: list[dict[str, Any]] = []
        for event in application.events:
            events_timeline.append({
                "event_type": event.email_event_type,
                "received_at": event.email_received_at.isoformat() if event.email_received_at else None,
                "subject": event.email_subject,
                "summary": event.email_summary,
                "status_after_event": event.email_status_after_event,
            })

        try:
            summary_result = await summarize_application_status(db, events_timeline)
            content_to_embed = getattr(summary_result, "snapshot", None)
            if not content_to_embed:
                for alt_field in ("summary", "overview", "summary_text", "application_summary", "result", "text"):
                    content_to_embed = getattr(summary_result, alt_field, None)
                    if content_to_embed:
                        break
        except Exception as sum_err:
            logger.warning("Summarization failed before embedding, generating fallback text: %s", sum_err)

    # Fast programmatic structured snapshot for manual actions or fallback
    if not content_to_embed or not str(content_to_embed).strip():
        event_lines = [
            f"- [{e.email_event_type}{f' ({e.email_received_at.strftime('%Y-%m-%d')})' if e.email_received_at else ''}] {e.email_summary or ''}"
            for e in (application.events or [])
        ]
        timeline_text = "\n".join(event_lines) if event_lines else "Initial application recorded."
        content_to_embed = (
            f"Job Application: {application.position} at {comp_name}.\n"
            f"Status: {application.status}.\n"
            f"Date: {date_str}.\n"
            f"Activity & Updates:\n{timeline_text}"
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
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
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
    Uses an isolated AsyncSessionLocal so that it can run safely in BackgroundTasks without blocking HTTP response.
    """
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            await generate_and_save_application_embedding(
                session,
                application_id=application_id,
                skip_llm_summary=skip_llm_summary,
            )
            logger.info("Background vector embedding updated for Application ID %d", application_id)
        except Exception as err:
            logger.warning("Background vector embedding failed for Application ID %d: %s", application_id, err)