import logging
from typing import Any

import httpx
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class FailoverChatModel(Runnable[Any, Any]):
    """
    Transparent failover wrapper around primary and secondary LangChain BaseChatModel instances.
    Catches connection refusals, timeouts, and network failures on the primary provider,
    logs diagnostic telemetry in trace_events, and re-routes invocation seamlessly to the fallback provider.
    """

    FAILOVER_ERRORS = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.NetworkError,
        httpx.TimeoutException,
        ConnectionRefusedError,
        TimeoutError,
        OSError,
    )

    def __init__(
        self,
        primary_model: Any,
        fallback_model: Any | None = None,
        primary_name: str = "Primary AI Provider",
        fallback_name: str | None = None,
    ):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.primary_name = primary_name
        self.fallback_name = fallback_name or "Fallback Provider"

    def _should_failover(self, exc: Exception) -> bool:
        if isinstance(exc, self.FAILOVER_ERRORS):
            return True
        exc_str = str(exc).lower()
        failover_keywords = [
            "connection refused",
            "connecterror",
            "connection error",
            "timed out",
            "timeout",
            "failed to connect",
            "could not connect",
        ]
        return any(kw in exc_str for kw in failover_keywords)

    async def _log_failover_telemetry(self, err_msg: str) -> None:
        try:
            import uuid

            import app.core.database as db_module
            from app.models.diagnostics import TraceEventModel

            message = f"Primary provider '{self.primary_name}' unreachable. Automatic failover routed task to '{self.fallback_name}'"
            async with db_module.AsyncSessionLocal() as session:
                trace = TraceEventModel(
                    run_id=f"failover_{uuid.uuid4().hex[:12]}",
                    category="llm",
                    event_type="provider_failover",
                    payload={
                        "message": message,
                        "primary_provider": self.primary_name,
                        "fallback_provider": self.fallback_name,
                        "error_detail": err_msg,
                    },
                )
                session.add(trace)
                await session.commit()
        except Exception as e:
            logger.warning("Failed to record failover trace event: %s", e)

    async def ainvoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        try:
            return await self.primary_model.ainvoke(input, config=config, **kwargs)
        except Exception as exc:
            if self.fallback_model and self._should_failover(exc):
                await self._log_failover_telemetry(str(exc))
                logger.warning(
                    "Primary provider '%s' unreachable (%s). Automatic failover routed task to '%s'",
                    self.primary_name,
                    exc,
                    self.fallback_name,
                )
                return await self.fallback_model.ainvoke(input, config=config, **kwargs)
            raise

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        try:
            return self.primary_model.invoke(input, config=config, **kwargs)
        except Exception as exc:
            if self.fallback_model and self._should_failover(exc):
                logger.warning(
                    "Primary provider '%s' unreachable (%s). Automatic failover routed task to '%s'",
                    self.primary_name,
                    exc,
                    self.fallback_name,
                )
                return self.fallback_model.invoke(input, config=config, **kwargs)
            raise

    def stream(self, input: Any, config: Any = None, **kwargs: Any):
        if not self.fallback_model:
            yield from self.primary_model.stream(input, config=config, **kwargs)
            return

        yielded = False
        try:
            for chunk in self.primary_model.stream(input, config=config, **kwargs):
                yielded = True
                yield chunk
        except Exception as exc:
            if not yielded and self._should_failover(exc):
                logger.warning(
                    "Primary provider '%s' unreachable (%s). Automatic failover streaming from '%s'",
                    self.primary_name,
                    exc,
                    self.fallback_name,
                )
                yield from self.fallback_model.stream(input, config=config, **kwargs)
            else:
                raise

    async def astream(self, input: Any, config: Any = None, **kwargs: Any):
        if not self.fallback_model:
            async for chunk in self.primary_model.astream(
                input, config=config, **kwargs
            ):
                yield chunk
            return

        yielded = False
        try:
            async for chunk in self.primary_model.astream(
                input, config=config, **kwargs
            ):
                yielded = True
                yield chunk
        except Exception as exc:
            if not yielded and self._should_failover(exc):
                await self._log_failover_telemetry(str(exc))
                logger.warning(
                    "Primary provider '%s' unreachable (%s). Automatic failover streaming from '%s'",
                    self.primary_name,
                    exc,
                    self.fallback_name,
                )
                async for chunk in self.fallback_model.astream(
                    input, config=config, **kwargs
                ):
                    yield chunk
            else:
                raise

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        bound_primary = self.primary_model.bind_tools(tools, **kwargs)
        bound_fallback = (
            self.fallback_model.bind_tools(tools, **kwargs)
            if self.fallback_model
            else None
        )
        return FailoverChatModel(
            primary_model=bound_primary,
            fallback_model=bound_fallback,
            primary_name=self.primary_name,
            fallback_name=self.fallback_name,
        )

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        struct_primary = self.primary_model.with_structured_output(schema, **kwargs)
        struct_fallback = (
            self.fallback_model.with_structured_output(schema, **kwargs)
            if self.fallback_model
            else None
        )
        return FailoverChatModel(
            primary_model=struct_primary,
            fallback_model=struct_fallback,
            primary_name=self.primary_name,
            fallback_name=self.fallback_name,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.primary_model, name)


_EMBEDDINGS_CACHE: dict[tuple, Embeddings] = {}


def clear_embeddings_cache() -> None:
    """Clears cached Embeddings model instances."""
    _EMBEDDINGS_CACHE.clear()


def _get_cached_embeddings_model(init_kwargs: dict[str, Any]) -> Embeddings:
    """Returns cached Embeddings model instance or initializes and caches a new one."""
    cache_key = tuple(sorted((k, str(v)) for k, v in init_kwargs.items()))
    if cache_key in _EMBEDDINGS_CACHE:
        return _EMBEDDINGS_CACHE[cache_key]

    instance = init_embeddings(**init_kwargs)
    _EMBEDDINGS_CACHE[cache_key] = instance
    return instance


UNCONFIGURED_PROVIDER = "openai"
UNCONFIGURED_MODEL = "gpt-4o-mini"
UNCONFIGURED_EMBEDDING_MODEL = "text-embedding-3-small"

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
    url = url.removesuffix("/embeddings")
    return url


async def get_active_llm_config_dict(db: AsyncSession | None = None) -> dict[str, Any]:
    """Retrieves runtime LLM configuration from the database."""
    if db is None:
        try:
            import app.core.database as db_module

            async with db_module.AsyncSessionLocal() as session:
                return await get_active_llm_config_dict(session)
        except Exception as err:
            logger.warning("Failed loading database AI configuration: %s", err)

    if db is not None:
        try:
            from app.models.ai_providers import AITaskBindingModel
            from app.models.llm import LLMConfigModel

            binding_stmt = (
                select(AITaskBindingModel)
                .options(joinedload(AITaskBindingModel.provider))
                .where(
                    AITaskBindingModel.task_type == "GLOBAL_DEFAULT",
                    AITaskBindingModel.is_active,
                )
            )
            binding = (await db.execute(binding_stmt)).scalar_one_or_none()
            if binding and binding.provider and binding.provider.is_active:
                return {
                    "source": "database",
                    "provider_name": binding.provider.provider_type,
                    "api_base": binding.provider.base_url,
                    "api_key": binding.provider.api_key,
                    "model_name": binding.model_name,
                    "embedding_model_name": UNCONFIGURED_EMBEDDING_MODEL,
                    "temperature": binding.temperature,
                    "top_k": None,
                    "top_p": binding.top_p,
                    "max_tokens": binding.max_tokens,
                    "agent_model_name": binding.model_name,
                    "agent_temperature": binding.temperature,
                    "agent_top_k": None,
                    "agent_top_p": binding.top_p,
                    "agent_max_tokens": binding.max_tokens,
                    "agent_max_recursions": 15,
                }

            stmt = select(LLMConfigModel).where(LLMConfigModel.is_active)
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
                    or UNCONFIGURED_EMBEDDING_MODEL,
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
        "source": "unconfigured",
        "provider_name": UNCONFIGURED_PROVIDER,
        "api_base": None,
        "api_key": None,
        "model_name": UNCONFIGURED_MODEL,
        "embedding_model_name": UNCONFIGURED_EMBEDDING_MODEL,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 1.0,
        "max_tokens": None,
        "agent_model_name": UNCONFIGURED_MODEL,
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
    model = cfg.get("embedding_model_name", UNCONFIGURED_EMBEDDING_MODEL)
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
    return _get_cached_embeddings_model(init_kwargs)


TASK_RECOMMENDED_DEFAULTS = {
    "JD_EXTRACTION": {
        "temperature": 0.0,
        "reasoning_effort": "none",
        "max_tokens": None,
    },
    "EXTRACTION": {
        "temperature": 0.1,
        "reasoning_effort": "none",
        "max_tokens": None,
    },
    "ASSESSMENT": {
        "temperature": 0.2,
        "reasoning_effort": "none",
        "max_tokens": None,
    },
    "INTERVIEW_GUIDE": {
        "temperature": 0.3,
        "reasoning_effort": "none",
        "max_tokens": None,
    },
    "COVER_LETTER": {
        "temperature": 0.3,
        "reasoning_effort": "none",
        "max_tokens": None,
    },
    "AGENT": {"temperature": 0.2, "reasoning_effort": "none", "max_tokens": None},
}


async def get_task_chat_model(
    db: AsyncSession | None = None,
    task_type: str = "EXTRACTION",
    **override_kwargs: Any,
) -> BaseChatModel:
    """
    Dynamically loads and initializes a LangChain BaseChatModel based on task binding configuration.
    The Global Default Model sets only the Provider and Model Name.
    Task-specific parameters (temperature, max_tokens, reasoning_effort) are kept independent per task.
    """
    task_defaults = TASK_RECOMMENDED_DEFAULTS.get(
        task_type,
        {"temperature": 0.2, "reasoning_effort": "none", "max_tokens": None},
    )

    if db is not None:
        try:
            from app.models.ai_providers import AITaskBindingModel

            stmt = (
                select(AITaskBindingModel)
                .options(joinedload(AITaskBindingModel.provider))
                .where(
                    AITaskBindingModel.task_type.in_([task_type, "GLOBAL_DEFAULT"]),
                    AITaskBindingModel.is_active,
                )
            )
            res = await db.execute(stmt)
            bindings = res.scalars().all()

            # Prefer the exact task_type match, otherwise fallback to GLOBAL_DEFAULT
            exact_binding = next(
                (b for b in bindings if b.task_type == task_type), None
            )
            global_binding = next(
                (b for b in bindings if b.task_type == "GLOBAL_DEFAULT"), None
            )

            # 1. Resolve Provider and Model Name (Exact override takes precedence, otherwise Global Default)
            target_provider = None
            target_model_name = None

            if (
                exact_binding
                and exact_binding.provider
                and exact_binding.provider.is_active
                and exact_binding.model_name
            ):
                extra = dict(exact_binding.extra_kwargs or {})
                if not extra.get("use_global_default", False):
                    target_provider = exact_binding.provider
                    target_model_name = exact_binding.model_name

            if not target_provider or not target_model_name:
                if (
                    global_binding
                    and global_binding.provider
                    and global_binding.provider.is_active
                ):
                    target_provider = global_binding.provider
                    target_model_name = global_binding.model_name

            # 2. Resolve Parameters (Temperature, Max Tokens, Top P, Reasoning Effort)
            # These are ALWAYS task-specific, never polluted by global default
            if exact_binding:
                temperature = (
                    exact_binding.temperature
                    if exact_binding.temperature is not None
                    else task_defaults["temperature"]
                )
                top_p = exact_binding.top_p
                max_tokens = exact_binding.max_tokens
                extra = dict(exact_binding.extra_kwargs or {})
                reasoning = extra.get(
                    "reasoning_effort", task_defaults["reasoning_effort"]
                )
            else:
                temperature = task_defaults["temperature"]
                top_p = None
                max_tokens = task_defaults["max_tokens"]
                reasoning = task_defaults["reasoning_effort"]

            if target_provider and target_provider.is_active and target_model_name:
                provider_type = _resolve_provider(target_provider.provider_type)
                base_url = _clean_base_url(target_provider.base_url)
                api_key = target_provider.api_key or "dummy-key"

                init_kwargs: dict[str, Any] = {
                    "model": target_model_name,
                    "model_provider": provider_type,
                    "temperature": temperature,
                    "timeout": 300.0,
                }

                if base_url:
                    init_kwargs["base_url"] = base_url
                if api_key:
                    init_kwargs["api_key"] = api_key
                if top_p is not None:
                    init_kwargs["top_p"] = top_p
                if max_tokens is not None and max_tokens > 0:
                    init_kwargs["max_tokens"] = max_tokens

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
                            or max_tokens
                            or 0
                        )
                        if current_max <= budget:
                            init_kwargs["max_tokens"] = budget + 1024
                            override_kwargs.pop("max_tokens", None)
                    elif provider_type in ("google_genai", "gemini"):
                        budget = (
                            1024
                            if reasoning == "low"
                            else (2048 if reasoning == "medium" else 4096)
                        )
                        init_kwargs.setdefault("extra_body", {})["thinking_config"] = {
                            "thinking_budget": budget
                        }

                clean_overrides = {
                    k: v
                    for k, v in override_kwargs.items()
                    if not (k == "max_tokens" and v is None)
                }
                init_kwargs.update(clean_overrides)
                primary_chat = init_chat_model(**init_kwargs)

                # Query secondary active fallback provider if available
                fallback_chat = None
                fallback_name = None
                try:
                    from app.models.ai_providers import AIProviderModel

                    fb_stmt = select(AIProviderModel).where(
                        AIProviderModel.id != target_provider.id,
                        AIProviderModel.is_active.is_(True),
                    )
                    all_fb = (await db.execute(fb_stmt)).scalars().all()
                    fallback_prov = next(
                        (p for p in all_fb if getattr(p, "is_fallback", False)),
                        all_fb[0] if all_fb else None,
                    )
                    if fallback_prov:
                        fb_type = _resolve_provider(fallback_prov.provider_type)
                        fb_base_url = _clean_base_url(fallback_prov.base_url)
                        fb_api_key = fallback_prov.api_key or "dummy-key"
                        fb_model_name = "gpt-4o-mini"
                        if getattr(fallback_prov, "task_bindings", None):
                            matching_b = next(
                                (
                                    b
                                    for b in fallback_prov.task_bindings
                                    if b.task_type == task_type
                                ),
                                fallback_prov.task_bindings[0]
                                if fallback_prov.task_bindings
                                else None,
                            )
                            if matching_b and matching_b.model_name:
                                fb_model_name = matching_b.model_name

                        fb_init_kwargs: dict[str, Any] = {
                            "model": fb_model_name,
                            "model_provider": fb_type,
                            "temperature": temperature,
                            "timeout": 300.0,
                        }
                        if fb_base_url:
                            fb_init_kwargs["base_url"] = fb_base_url
                        if fb_api_key:
                            fb_init_kwargs["api_key"] = fb_api_key
                        fb_init_kwargs.update(clean_overrides)
                        fallback_chat = init_chat_model(**fb_init_kwargs)
                        fallback_name = fallback_prov.name
                except Exception as fb_err:
                    logger.warning(
                        "Failed initializing secondary fallback provider model: %s",
                        fb_err,
                    )

                return FailoverChatModel(
                    primary_model=primary_chat,
                    fallback_model=fallback_chat,
                    primary_name=target_provider.name,
                    fallback_name=fallback_name,
                )
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
                    AITaskBindingModel.is_active,
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
                return _get_cached_embeddings_model(init_kwargs)
        except Exception as err:
            logger.warning(
                "Failed loading EMBEDDING task binding, falling back: %s", err
            )

    return await get_embeddings_model(db, **override_kwargs)
