import json
import logging
from typing import Any, Dict, List, Optional
import litellm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.prompts import get_prompt_template
from app.models.applications import ApplicationEmbeddingModel, ApplicationModel
from app.schemas.llm import ApplicationSummaryResult, EmailExtractionResult

logger = logging.getLogger(__name__)

# Suppress noisy debug logs from litellm if needed
litellm.suppress_debug_info = True


def _get_llm_response_text(response: Any) -> str:
    """
    Safely extract text content from a LiteLLM response object.
    Handles both standard completion responses and streaming wrappers.
    """
    if hasattr(response, "output_text"):
        output_text = getattr(response, "output_text")
        if output_text is not None:
            return output_text

    if hasattr(response, "message"):
        message = getattr(response, "message")
        if hasattr(message, "content"):
            return getattr(message, "content")

    if hasattr(response, "choices"):
        choices = getattr(response, "choices")
        if choices:
            first_choice = choices[0]
            if hasattr(first_choice, "message"):
                message = getattr(first_choice, "message")
                if hasattr(message, "content"):
                    return getattr(message, "content")

    if hasattr(response, "text"):
        text = getattr(response, "text")
        if text is not None:
            return text

    raise ValueError("Unable to extract text from LiteLLM response.")


async def get_active_llm_config(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetches the active LLM configuration from the database.
    If no active DB record exists, falls back to .env settings.
    """
    try:
        from app.models.llm import LLMConfigModel  # Lazy import to avoid circular dependency
        
        stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
        res = await db.execute(stmt)
        db_config = res.scalar_one_or_none()

        if db_config:
            return {
                "model": db_config.model_name,
                "api_base": db_config.api_base,
                "api_key": db_config.api_key,
                "embedding_model": db_config.embedding_model_name or settings.EMBEDDING_MODEL_NAME,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch LLM config from DB, using fallback .env settings: {e}")

    # Fallback to .env settings
    return {
        "model": settings.LLM_MODEL_NAME,
        "api_base": settings.LLM_API_BASE,
        "api_key": settings.LLM_API_KEY,
        "embedding_model": getattr(settings, "LLM_EMBEDDING_MODEL_NAME", settings.EMBEDDING_MODEL_NAME),
    }


async def extract_email_info(db: AsyncSession, email_content: str) -> EmailExtractionResult:
    """
    Fetches prompt template from DB and parses email content 
    into structured Pydantic format via LiteLLM.
    """
    cfg = await get_active_llm_config(db)
    template = await get_prompt_template(db, "extraction")
    prompt = template.format(email_content=email_content)

    response = await litellm.acompletion(
        model=cfg["model"],
        api_base=cfg["api_base"],
        api_key=cfg["api_key"],
        messages=[
            {"role": "system", "content": "You parse job application emails into structured data."},
            {"role": "user", "content": prompt},
        ],
        response_format=EmailExtractionResult,
    )

    content = _get_llm_response_text(response)
    return EmailExtractionResult.model_validate_json(content)


async def summarize_application_status(
    db: AsyncSession, events_timeline: List[Dict[str, Any]]
) -> ApplicationSummaryResult:
    """
    Fetches summarization prompt template from DB and generates 
    a application snapshot using LiteLLM.
    """
    cfg = await get_active_llm_config(db)
    events_str = json.dumps(events_timeline, indent=2)
    template = await get_prompt_template(db, "summarization")
    prompt = template.format(events_str=events_str)

    response = await litellm.acompletion(
        model=cfg["model"],
        api_base=cfg["api_base"],
        api_key=cfg["api_key"],
        messages=[
            {"role": "system", "content": "You summarize job application timelines for embeddings."},
            {"role": "user", "content": prompt},
        ],
        response_format=ApplicationSummaryResult,
    )

    content = _get_llm_response_text(response)
    return ApplicationSummaryResult.model_validate_json(content)


async def generate_embedding(
    db: AsyncSession, text_input: str
) -> List[float]:
    """
    Generates vector embeddings via LiteLLM using active model settings.
    """
    cfg = await get_active_llm_config(db)
    
    # LiteLLM handles standard OpenAI / custom embedding provider calls
    kwargs: Dict[str, Any] = {
        "model": cfg["embedding_model"],
        "input": [text_input],
    }
    
    # Pass api_base and api_key if present
    if cfg.get("api_base"):
        kwargs["api_base"] = cfg["api_base"]
    if cfg.get("api_key"):
        kwargs["api_key"] = cfg["api_key"]

    response = await litellm.aembedding(**kwargs)
    return response.data[0]["embedding"]


async def generate_and_save_application_embedding(
    db: AsyncSession, application_id: int
) -> ApplicationEmbeddingModel:
    """
    Summarizes application history, generates vector representation, 
    and updates/inserts record in email_application_embeddings.
    """
    # 1. Retrieve application along with eagerly loaded events and company
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

    # 2. Build structured timeline array for LLM summarization
    events_timeline = []
    for event in application.events:
        events_timeline.append({
            "event_type": event.email_event_type,
            "received_at": event.email_received_at.isoformat() if event.email_received_at else None,
            "subject": event.email_subject,
            "summary": event.email_summary,
            "status_after_event": event.email_status_after_event,
        })

    # 3. Summarize timeline using LLM
    summary_result = await summarize_application_status(db, events_timeline)
    
    # Extract text content from parsed summary object
    content_to_embed = getattr(summary_result, "snapshot", None)
    
    if content_to_embed is None:
        for alt_field in ("summary", "overview", "summary_text", "application_summary", "result", "text"):
            content_to_embed = getattr(summary_result, alt_field, None)
            if content_to_embed is not None:
                break
                
    if content_to_embed is None:
        raise ValueError("Unable to extract snapshot or summary text from ApplicationSummaryResult.")

    # 4. Generate float vector using active LLM embedding setup
    vector = await generate_embedding(db, content_to_embed)

    # 5. Insert or update embedding record in DB
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