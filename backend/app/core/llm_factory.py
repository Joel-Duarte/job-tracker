import logging
from typing import Any
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER_MAP = {
    "custom": "openai",
    "lmstudio": "openai",
    "vllm": "openai",
    "local": "openai",
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "ollama": "ollama",
    "google": "google_genai",
    "gemini": "google_genai",
    "google_genai": "google_genai",
    "openrouter": "openai",
}


def _resolve_provider(provider_name: str | None) -> str:
    if not provider_name:
        return "openai"
    normalized = provider_name.strip().lower()
    return PROVIDER_MAP.get(normalized, normalized)


def _clean_base_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.rstrip("/")
    if url.endswith("/embeddings"):
        url = url[: -len("/embeddings")]
    return url


async def get_active_llm_config_dict(db: AsyncSession | None = None) -> dict[str, Any]:
    """Retrieves legacy LLM configuration from DB with fallback to settings (.env)."""
    if db is not None:
        try:
            from app.models.llm import LLMConfigModel

            stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
            res = await db.execute(stmt)
            db_config = res.scalar_one_or_none()

            if db_config:
                return {
                    "source": "database",
                    "provider_name": db_config.provider_name,
                    "api_base": db_config.api_base,
                    "api_key": db_config.api_key,
                    "model_name": db_config.model_name,
                    "embedding_model_name": db_config.embedding_model_name
                    or settings.EMBEDDING_MODEL_NAME,
                    "temperature": db_config.temperature,
                    "top_k": db_config.top_k,
                    "top_p": db_config.top_p,
                    "max_tokens": db_config.max_tokens,
                    "agent_model_name": db_config.agent_model_name
                    or db_config.model_name,
                    "agent_temperature": db_config.agent_temperature,
                    "agent_top_k": db_config.agent_top_k,
                    "agent_top_p": db_config.agent_top_p,
                    "agent_max_tokens": db_config.agent_max_tokens,
                    "agent_max_recursions": db_config.agent_max_recursions,
                }
        except Exception as err:
            logger.warning("Failed to fetch legacy LLM config from DB: %s", err)

    return {
        "source": ".env",
        "provider_name": settings.LLM_PROVIDER_NAME,
        "api_base": settings.LLM_API_BASE,
        "api_key": settings.LLM_API_KEY,
        "model_name": settings.LLM_MODEL_NAME,
        "embedding_model_name": settings.EMBEDDING_MODEL_NAME,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1.0,
        "max_tokens": None,
        "agent_model_name": settings.LLM_MODEL_NAME,
        "agent_temperature": 0.2,
        "agent_top_k": 50,
        "agent_top_p": 1.0,
        "agent_max_tokens": None,
        "agent_max_recursions": 15,
    }


async def get_chat_model(
    db: AsyncSession | None = None,
    is_agent: bool = False,
    **override_kwargs: Any,
) -> BaseChatModel:
    """Fallback initialization of LangChain BaseChatModel from legacy/env config."""
    cfg = await get_active_llm_config_dict(db)

    provider = _resolve_provider(cfg.get("provider_name"))
    model = cfg.get("agent_model_name") if is_agent else cfg.get("model_name")
    temperature = (
        cfg.get("agent_temperature") if is_agent else cfg.get("temperature", 0.7)
    )
    api_base = _clean_base_url(cfg.get("api_base"))
    api_key = cfg.get("api_key") or "dummy-key"
    top_p = cfg.get("agent_top_p") if is_agent else cfg.get("top_p")
    max_tokens = cfg.get("agent_max_tokens") if is_agent else cfg.get("max_tokens")

    init_kwargs: dict[str, Any] = {
        "model": model,
        "model_provider": provider,
        "temperature": temperature,
        "timeout": 300.0,
    }

    if api_base:
        init_kwargs["base_url"] = api_base
    if api_key:
        init_kwargs["api_key"] = api_key
    if top_p is not None:
        init_kwargs["top_p"] = top_p
    if max_tokens is not None:
        init_kwargs["max_tokens"] = max_tokens

    init_kwargs.update(override_kwargs)
    return init_chat_model(**init_kwargs)


async def get_embeddings_model(
    db: AsyncSession | None = None,
    **override_kwargs: Any,
) -> Embeddings:
    """Fallback initialization of LangChain Embeddings from legacy/env config."""
    cfg = await get_active_llm_config_dict(db)

    provider = _resolve_provider(cfg.get("provider_name"))
    model = cfg.get("embedding_model_name", settings.EMBEDDING_MODEL_NAME)
    api_base = _clean_base_url(cfg.get("api_base"))
    api_key = cfg.get("api_key") or "dummy-key"

    init_kwargs: dict[str, Any] = {
        "model": model,
        "provider": provider,
    }

    if api_base:
        init_kwargs["base_url"] = api_base
    if api_key:
        init_kwargs["api_key"] = api_key

    # Strict string array compatibility for local providers (LM Studio / Ollama)
    if provider == "openai":
        init_kwargs["check_embedding_ctx_length"] = False
        init_kwargs["tiktoken_enabled"] = False

    init_kwargs.update(override_kwargs)
    return init_embeddings(**init_kwargs)


async def get_task_chat_model(
    db: AsyncSession | None = None,
    task_type: str = "EXTRACTION",
    **override_kwargs: Any,
) -> BaseChatModel:
    """
    Dynamically loads and initializes a LangChain BaseChatModel based on task binding configuration.
    Cascades gracefully to legacy/env config if task binding is not configured.
    """
    if db is not None:
        try:
            from app.models.ai_providers import AITaskBindingModel

            stmt = (
                select(AITaskBindingModel)
                .options(joinedload(AITaskBindingModel.provider))
                .where(
                    AITaskBindingModel.task_type == task_type,
                    AITaskBindingModel.is_active == True,
                )
            )
            res = await db.execute(stmt)
            binding = res.scalar_one_or_none()

            if binding and binding.provider and binding.provider.is_active:
                provider_type = _resolve_provider(binding.provider.provider_type)
                base_url = _clean_base_url(binding.provider.base_url)
                api_key = binding.provider.api_key or "dummy-key"

                init_kwargs: dict[str, Any] = {
                    "model": binding.model_name,
                    "model_provider": provider_type,
                    "temperature": binding.temperature,
                    "timeout": 300.0,
                }

                if base_url:
                    init_kwargs["base_url"] = base_url
                if api_key:
                    init_kwargs["api_key"] = api_key
                if binding.top_p is not None:
                    init_kwargs["top_p"] = binding.top_p
                if binding.max_tokens is not None and binding.max_tokens > 0:
                    init_kwargs["max_tokens"] = binding.max_tokens

                extra = dict(binding.extra_kwargs or {})
                reasoning = extra.get("reasoning_effort", "none")

                # Configure reasoning / thinking mode across model families
                if reasoning and reasoning.lower() != "none":
                    if provider_type in ("openai", "openrouter"):
                        init_kwargs.setdefault("extra_body", {})["reasoning_effort"] = (
                            reasoning.lower()
                        )
                    elif provider_type == "anthropic":
                        budget = (
                            1024
                            if reasoning == "low"
                            else (2048 if reasoning == "medium" else 4096)
                        )
                        init_kwargs["thinking"] = {
                            "type": "enabled",
                            "budget_tokens": budget,
                        }
                        init_kwargs["temperature"] = 1.0

                        # Anthropic requires max_tokens > budget_tokens
                        current_max = (
                            init_kwargs.get("max_tokens")
                            or override_kwargs.get("max_tokens")
                            or binding.max_tokens
                            or 0
                        )
                        if current_max <= budget:
                            init_kwargs["max_tokens"] = budget + 1024
                            if "max_tokens" in override_kwargs:
                                del override_kwargs["max_tokens"]
                    elif provider_type in ("google_genai", "gemini"):
                        budget = (
                            1024
                            if reasoning == "low"
                            else (2048 if reasoning == "medium" else 4096)
                        )
                        init_kwargs.setdefault("extra_body", {})["thinking_config"] = {
                            "thinking_budget": budget
                        }

                # Apply remaining extra kwargs if provided
                for k, v in extra.items():
                    if k != "reasoning_effort":
                        init_kwargs[k] = v

                # Filter out max_tokens=None from override_kwargs if passed
                clean_overrides = {
                    k: v
                    for k, v in override_kwargs.items()
                    if not (k == "max_tokens" and v is None)
                }
                init_kwargs.update(clean_overrides)
                return init_chat_model(**init_kwargs)
        except Exception as err:
            logger.warning(
                "Failed loading task binding '%s', falling back: %s", task_type, err
            )

    is_agent_flag = task_type in ("AGENT_REASONING",)
    default_temp = None
    if task_type in ("JD_EXTRACTION", "EXTRACTION"):
        default_temp = 0.0
    elif task_type in ("ASSESSMENT",):
        default_temp = 0.2

    if default_temp is not None and "temperature" not in override_kwargs:
        override_kwargs["temperature"] = default_temp

    return await get_chat_model(db, is_agent=is_agent_flag, **override_kwargs)


async def get_task_embeddings_model(
    db: AsyncSession | None = None,
    **override_kwargs: Any,
) -> Embeddings:
    """
    Dynamically loads and initializes a LangChain Embeddings model from 'EMBEDDING' task binding.
    Cascades gracefully to legacy/env config if task binding is not configured.
    """
    if db is not None:
        try:
            from app.models.ai_providers import AITaskBindingModel

            stmt = (
                select(AITaskBindingModel)
                .options(joinedload(AITaskBindingModel.provider))
                .where(
                    AITaskBindingModel.task_type == "EMBEDDING",
                    AITaskBindingModel.is_active == True,
                )
            )
            res = await db.execute(stmt)
            binding = res.scalar_one_or_none()

            if binding and binding.provider and binding.provider.is_active:
                provider_type = _resolve_provider(binding.provider.provider_type)
                base_url = _clean_base_url(binding.provider.base_url)
                api_key = binding.provider.api_key or "dummy-key"

                init_kwargs: dict[str, Any] = {
                    "model": binding.model_name,
                    "provider": provider_type,
                }

                if provider_type == "openai":
                    init_kwargs["check_embedding_ctx_length"] = False
                    init_kwargs["tiktoken_enabled"] = False

                if base_url:
                    init_kwargs["base_url"] = base_url
                if api_key:
                    init_kwargs["api_key"] = api_key

                init_kwargs.update(override_kwargs)
                return init_embeddings(**init_kwargs)
        except Exception as err:
            logger.warning(
                "Failed loading EMBEDDING task binding, falling back: %s", err
            )

    return await get_embeddings_model(db, **override_kwargs)
