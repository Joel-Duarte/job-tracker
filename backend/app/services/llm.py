import json
import logging
from typing import Any
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
from app.schemas.llm import ApplicationSummaryResult, EmailExtractionResult

logger = logging.getLogger(__name__)


async def get_active_llm_config(db: AsyncSession) -> dict[str, Any]:
    """Backward compatibility helper returning active LLM config dictionary."""
    return await get_active_llm_config_dict(db)


async def extract_email_info(db: AsyncSession, email_content: str) -> EmailExtractionResult:
    """Extracts structured job application metadata from email body using LangChain EXTRACTION model."""
    llm = await get_task_chat_model(db, task_type="EXTRACTION")
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


async def summarize_application_status(
    db: AsyncSession, events_timeline: list[dict[str, Any]]
) -> ApplicationSummaryResult:
    """Synthesizes a narrative status snapshot from timeline events using LangChain SUMMARIZATION model."""
    llm = await get_task_chat_model(db, task_type="SUMMARIZATION")
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
    embeddings = await get_task_embeddings_model(db)
    return await embeddings.aembed_query(text_input)


async def generate_and_save_application_embedding(
    db: AsyncSession, application_id: int
) -> ApplicationEmbeddingModel:
    """Summarizes application timeline and creates/updates 768-dim vector embedding record."""
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

    events_timeline: list[dict[str, Any]] = []
    for event in application.events:
        events_timeline.append({
            "event_type": event.email_event_type,
            "received_at": event.email_received_at.isoformat() if event.email_received_at else None,
            "subject": event.email_subject,
            "summary": event.email_summary,
            "status_after_event": event.email_status_after_event,
        })

    summary_result = await summarize_application_status(db, events_timeline)

    content_to_embed = getattr(summary_result, "snapshot", None)
    if content_to_embed is None:
        for alt_field in ("summary", "overview", "summary_text", "application_summary", "result", "text"):
            content_to_embed = getattr(summary_result, alt_field, None)
            if content_to_embed is not None:
                break

    if content_to_embed is None:
        raise ValueError("Unable to extract snapshot or summary text from ApplicationSummaryResult.")

    vector = await generate_embedding(db, content_to_embed)

    emb_stmt = select(ApplicationEmbeddingModel).where(
        ApplicationEmbeddingModel.email_application_id == application_id
    )
    emb_res = await db.execute(emb_stmt)
    embedding_record = emb_res.scalar_one_or_none()

    metadata_payload = {
        "company": application.company.name if application.company else None,
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