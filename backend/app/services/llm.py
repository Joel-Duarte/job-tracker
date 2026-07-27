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

litellm.suppress_debug_info = True


def _get_llm_response_text(response: Any) -> str:
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


def _resolve_formatted_model(provider_name: Optional[str], raw_model_name: str) -> str:
    if provider_name and provider_name != "env_default" and "/" not in raw_model_name:
        return f"{provider_name}/{raw_model_name}"
    return raw_model_name


async def get_active_llm_config(db: AsyncSession) -> Dict[str, Any]:
    try:
        from app.models.llm import LLMConfigModel
        
        stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
        res = await db.execute(stmt)
        db_config = res.scalar_one_or_none()

        if db_config:
            provider = db_config.provider_name
            return {
                "provider_name": provider,
                "model": _resolve_formatted_model(provider, db_config.model_name),
                "api_base": db_config.api_base,
                "api_key": db_config.api_key,
                "temperature": db_config.temperature,
                "top_k": db_config.top_k,
                "top_p": db_config.top_p,
                "max_tokens": db_config.max_tokens,
                "embedding_model": db_config.embedding_model_name or getattr(settings, "LLM_EMBEDDING_MODEL_NAME", getattr(settings, "EMBEDDING_MODEL_NAME", None)),
                "agent_model": _resolve_formatted_model(provider, db_config.agent_model_name) if db_config.agent_model_name else _resolve_formatted_model(provider, db_config.model_name),
                "agent_temperature": db_config.agent_temperature,
                "agent_top_k": db_config.agent_top_k,
                "agent_top_p": db_config.agent_top_p,
                "agent_max_tokens": db_config.agent_max_tokens,
                "agent_max_recursions": db_config.agent_max_recursions,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch LLM config from DB, using fallback .env settings: {e}")

    env_provider = getattr(settings, "LLM_PROVIDER_NAME", "custom")
    env_model = settings.LLM_MODEL_NAME
    return {
        "provider_name": env_provider,
        "model": _resolve_formatted_model(env_provider, env_model),
        "api_base": settings.LLM_API_BASE,
        "api_key": settings.LLM_API_KEY,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1.0,
        "max_tokens": None,
        "embedding_model": getattr(settings, "LLM_EMBEDDING_MODEL_NAME", getattr(settings, "EMBEDDING_MODEL_NAME", None)),
        "agent_model": _resolve_formatted_model(env_provider, env_model),
        "agent_temperature": 0.2,
        "agent_top_k": 50,
        "agent_top_p": 1.0,
        "agent_max_tokens": None,
        "agent_max_recursions": 15,
    }


async def extract_email_info(db: AsyncSession, email_content: str) -> EmailExtractionResult:
    cfg = await get_active_llm_config(db)
    template = await get_prompt_template(db, "extraction")
    prompt = template.format(email_content=email_content)

    kwargs: Dict[str, Any] = {
        "model": cfg["model"],
        "api_base": cfg["api_base"],
        "api_key": cfg["api_key"],
        "messages": [
            {"role": "system", "content": "You parse job application emails into structured data."},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "response_format": EmailExtractionResult,
    }
    if cfg["top_k"] is not None:
        kwargs["top_k"] = cfg["top_k"]
    if cfg["max_tokens"] is not None:
        kwargs["max_tokens"] = cfg["max_tokens"]

    response = await litellm.acompletion(**kwargs)
    content = _get_llm_response_text(response)
    return EmailExtractionResult.model_validate_json(content)


async def summarize_application_status(
    db: AsyncSession, events_timeline: List[Dict[str, Any]]
) -> ApplicationSummaryResult:
    cfg = await get_active_llm_config(db)
    events_str = json.dumps(events_timeline, indent=2)
    template = await get_prompt_template(db, "summarization")
    prompt = template.format(events_str=events_str)

    kwargs: Dict[str, Any] = {
        "model": cfg["model"],
        "api_base": cfg["api_base"],
        "api_key": cfg["api_key"],
        "messages": [
            {"role": "system", "content": "You summarize job application timelines for embeddings."},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "response_format": ApplicationSummaryResult,
    }
    if cfg["top_k"] is not None:
        kwargs["top_k"] = cfg["top_k"]
    if cfg["max_tokens"] is not None:
        kwargs["max_tokens"] = cfg["max_tokens"]

    response = await litellm.acompletion(**kwargs)
    content = _get_llm_response_text(response)
    return ApplicationSummaryResult.model_validate_json(content)


async def generate_embedding(
    db: AsyncSession, text_input: str
) -> List[float]:
    cfg = await get_active_llm_config(db)
    
    kwargs: Dict[str, Any] = {
        "model": cfg["embedding_model"],
        "input": [text_input],
    }
    
    if cfg.get("api_base"):
        kwargs["api_base"] = cfg["api_base"]
    if cfg.get("api_key"):
        kwargs["api_key"] = cfg["api_key"]

    response = await litellm.aembedding(**kwargs)
    return response.data[0]["embedding"]


async def generate_and_save_application_embedding(
    db: AsyncSession, application_id: int
) -> ApplicationEmbeddingModel:
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

    events_timeline = []
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