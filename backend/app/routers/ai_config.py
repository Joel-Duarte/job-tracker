import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config_manager import load_settings, save_settings
from app.core.database import get_db
from app.core.llm_factory import (
    _clean_base_url,
    _resolve_provider,
    clear_embeddings_cache,
    get_task_chat_model,
    get_task_embeddings_model,
)
from app.core.security import verify_admin_access
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.schemas.ai_config import (
    AIHealthStatusRead,
    AIProviderCreate,
    AIProviderModelsResponse,
    AIProviderRead,
    AIProviderTestResponse,
    AIProviderUpdate,
    AITaskBindingCreate,
    AITaskBindingRead,
    AITaskTestResponse,
    DiscoveredModel,
    ModelProbeRequest,
    ModelProbeResponse,
    PricingRateBatchUpdate,
    PricingRateRead,
    UsageOverviewRead,
    mask_secret,
)
from app.schemas.global_settings import GlobalSettingsRead, GlobalSettingsUpdate
from app.services.postgres_tracer import PostgresTracer

EMBEDDING_KEYWORDS = ("embed", "nomic", "bge", "minilm", "gte", "e5", "bert", "mxbai")


def _is_embedding_model(model_name: str) -> bool:
    low = model_name.lower()
    return any(kw in low for kw in EMBEDDING_KEYWORDS)


def _is_reasoning_model(model_name: str) -> bool:
    low = model_name.lower()
    return "think" in low or "reason" in low or "-r1" in low


CURATED_MODELS: dict[str, list[str]] = {
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "o3-mini",
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
    ],
    "anthropic": [
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ],
    "google_genai": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "text-embedding-004",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "text-embedding-004",
    ],
    "ollama": [
        "llama3.2",
        "llama3.1",
        "qwen2.5",
        "mistral",
        "deepseek-r1",
        "nomic-embed-text",
        "bge-m3",
        "all-minilm",
        "mxbai-embed-large",
    ],
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct",
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o-mini",
        "deepseek/deepseek-r1",
    ],
    "custom": [
        "qwen3.5-4b",
        "llama3.1",
        "mistral-7b",
        "nomic-embed-text",
        "bge-m3",
        "text-embedding-3-small",
    ],
}


async def _fetch_models_from_endpoint(
    provider: AIProviderModel,
) -> list[DiscoveredModel]:
    p_type = provider.provider_type.lower()
    base_url = _clean_base_url(provider.base_url)
    discovered: list[dict] = []

    if base_url:
        headers: dict[str, str] = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        async with httpx.AsyncClient(timeout=3.5) as client:
            try:
                if p_type == "ollama":
                    url = (
                        f"{base_url}/api/tags"
                        if not base_url.endswith("/api")
                        else f"{base_url}/tags"
                    )
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("models", []):
                            if "name" in m:
                                is_emb = _is_embedding_model(m["name"])
                                if (
                                    "details" in m
                                    and m["details"].get("family") == "bert"
                                ):
                                    is_emb = True
                                discovered.append(
                                    {"id": m["name"], "is_embedding": is_emb}
                                )
                else:
                    url = (
                        f"{base_url}/models"
                        if not base_url.endswith("/models")
                        else base_url
                    )
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("data", []):
                            if "id" in m:
                                is_emb = _is_embedding_model(m["id"])
                                # Check for capability flags common in LM Studio or vLLM
                                if (
                                    m.get("type") == "embeddings"
                                    or m.get("object") == "embedding"
                                ):
                                    is_emb = True
                                discovered.append(
                                    {"id": m["id"], "is_embedding": is_emb}
                                )
            except Exception as e:
                logger.warning(
                    "Live model probe skipped/failed for provider '%s': %s",
                    provider.name,
                    e,
                )

    models_out: list[DiscoveredModel] = []
    seen = set()
    for m in discovered:
        m_id = m["id"]
        if m_id not in seen:
            seen.add(m_id)
            models_out.append(
                DiscoveredModel(
                    id=m_id,
                    name=m_id,
                    is_discovered=True,
                    is_embedding=m["is_embedding"],
                    is_reasoning=_is_reasoning_model(m_id),
                )
            )

    curated = CURATED_MODELS.get(p_type, CURATED_MODELS["custom"])
    for m in curated:
        if m not in seen:
            seen.add(m)
            models_out.append(
                DiscoveredModel(
                    id=m,
                    name=m,
                    is_discovered=False,
                    is_embedding=_is_embedding_model(m),
                    is_reasoning=_is_reasoning_model(m),
                )
            )

    return models_out


logger = logging.getLogger(__name__)

config_ai_router = APIRouter(tags=["AI Health Monitoring"])

_HEALTH_CACHE: tuple[float, AIHealthStatusRead] | None = None
_HEALTH_CACHE_TTL = 15.0


def invalidate_ai_health_cache() -> None:
    global _HEALTH_CACHE
    _HEALTH_CACHE = None


async def check_ai_provider_health(db: AsyncSession) -> AIHealthStatusRead:
    global _HEALTH_CACHE
    now = time.monotonic()
    if _HEALTH_CACHE is not None:
        cached_time, cached_read = _HEALTH_CACHE
        if now - cached_time < _HEALTH_CACHE_TTL:
            return cached_read

    try:
        # 1. Resolve Global Default Task Binding
        global_binding_stmt = (
            select(AITaskBindingModel)
            .options(joinedload(AITaskBindingModel.provider))
            .where(
                AITaskBindingModel.task_type == "GLOBAL_DEFAULT",
                AITaskBindingModel.is_active.is_(True),
            )
        )
        global_binding = (await db.execute(global_binding_stmt)).scalar_one_or_none()
    except Exception as db_err:
        logger.warning("Database query failed during AI health check: %s", db_err)
        return AIHealthStatusRead(
            status="unconfigured",
            latency_ms=0.0,
            provider_name=None,
            error_message="Database unavailable",
        )

    if (
        not global_binding
        or not global_binding.provider
        or not global_binding.provider.is_active
    ):
        return AIHealthStatusRead(
            status="unconfigured",
            latency_ms=0.0,
            provider_name=None,
        )

    provider = global_binding.provider
    model_name = global_binding.model_name

    # 2. Resolve Active Fallback Provider
    fallback_stmt = select(AIProviderModel).where(
        AIProviderModel.id != provider.id,
        AIProviderModel.is_active.is_(True),
    )
    all_fallback_providers = (await db.execute(fallback_stmt)).scalars().all()

    fallback_provider = next(
        (p for p in all_fallback_providers if getattr(p, "is_fallback", False)),
        all_fallback_providers[0] if all_fallback_providers else None,
    )

    fallback_provider_id = fallback_provider.id if fallback_provider else None
    fallback_provider_name = fallback_provider.name if fallback_provider else None

    # 3. Fast Ping Probe (strict 3.0-second timeout)
    p_type = provider.provider_type.lower()
    base_url = _clean_base_url(provider.base_url)
    api_key = provider.api_key or ""

    start_time = time.perf_counter()
    status_str = "offline"
    latency_ms = 0.0
    error_message = None

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            probe_url = None
            if p_type == "ollama":
                probe_url = (
                    f"{base_url}/api/tags"
                    if base_url and not base_url.endswith("/api")
                    else (
                        f"{base_url}/tags"
                        if base_url
                        else "http://localhost:11434/api/tags"
                    )
                )
            elif base_url:
                probe_url = (
                    f"{base_url}/models"
                    if not base_url.endswith("/models")
                    else base_url
                )
            elif p_type == "anthropic":
                probe_url = "https://api.anthropic.com/v1/messages"
            elif p_type in ("google_genai", "gemini"):
                probe_url = "https://generativelanguage.googleapis.com"
            else:
                probe_url = "https://api.openai.com/v1/models"

            resp = await client.get(probe_url, headers=headers)
            elapsed = time.perf_counter() - start_time
            latency_ms = round(elapsed * 1000, 1)

            if 200 <= resp.status_code < 300:
                if latency_ms < 800.0:
                    status_str = "healthy"
                elif latency_ms <= 2500.0:
                    status_str = "degraded"
                else:
                    status_str = "offline"
                    error_message = f"Latency {latency_ms}ms exceeded 2500ms threshold."
            else:
                status_str = "offline"
                error_message = f"Provider returned HTTP status {resp.status_code}"
    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        status_str = "offline"
        error_message = "Connection timed out after 3.0s"
    except Exception as err:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        status_str = "offline"
        error_message = str(err)

    res_status = AIHealthStatusRead(
        status=status_str,
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        model_name=model_name,
        latency_ms=latency_ms,
        error_message=error_message,
        fallback_provider_id=fallback_provider_id,
        fallback_provider_name=fallback_provider_name,
    )
    _HEALTH_CACHE = (time.monotonic(), res_status)
    return res_status


@config_ai_router.get("/config/ai/health", response_model=AIHealthStatusRead)
@config_ai_router.get("/ai/health", response_model=AIHealthStatusRead)
async def get_ai_health_endpoint(
    db: AsyncSession = Depends(get_db),
) -> AIHealthStatusRead:
    return await check_ai_provider_health(db)


router = APIRouter(
    prefix="/ai",
    tags=["AI Provider Registry & Task Bindings"],
    dependencies=[Depends(verify_admin_access)],
)


@router.get("/global-settings", response_model=GlobalSettingsRead)
async def get_global_settings(
    db: AsyncSession = Depends(get_db),
) -> GlobalSettingsRead:
    settings = await load_settings(db)
    return GlobalSettingsRead(
        ENABLE_EMBEDDINGS=settings.get("enable_embeddings", False),
        AGENT_CHAT_RETENTION_DAYS=settings.get("agent_chat_retention_days", 7),
        ENABLE_AUTO_COVER_LETTER=settings.get("enable_auto_cover_letter", False),
        COVER_LETTER_MATCH_THRESHOLD=settings.get("cover_letter_match_threshold", 70),
        COVER_LETTER_LENGTH=settings.get("cover_letter_length", "standard"),
        ENABLE_EMAIL_INTAKE=settings.get("enable_email_intake", False),
        HAS_COMPLETED_ONBOARDING=settings.get("has_completed_onboarding", False),
    )


@router.patch("/global-settings", response_model=GlobalSettingsRead)
async def update_global_settings(
    payload: GlobalSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> GlobalSettingsRead:
    settings = await load_settings(db)
    if payload.ENABLE_EMBEDDINGS is not None:
        settings["enable_embeddings"] = payload.ENABLE_EMBEDDINGS
    if payload.AGENT_CHAT_RETENTION_DAYS is not None:
        settings["agent_chat_retention_days"] = payload.AGENT_CHAT_RETENTION_DAYS
    if payload.ENABLE_AUTO_COVER_LETTER is not None:
        settings["enable_auto_cover_letter"] = payload.ENABLE_AUTO_COVER_LETTER
    if payload.COVER_LETTER_MATCH_THRESHOLD is not None:
        settings["cover_letter_match_threshold"] = payload.COVER_LETTER_MATCH_THRESHOLD
    if payload.COVER_LETTER_LENGTH is not None:
        settings["cover_letter_length"] = payload.COVER_LETTER_LENGTH
    if payload.ENABLE_EMAIL_INTAKE is not None:
        settings["enable_email_intake"] = payload.ENABLE_EMAIL_INTAKE
    if payload.HAS_COMPLETED_ONBOARDING is not None:
        settings["has_completed_onboarding"] = payload.HAS_COMPLETED_ONBOARDING
    await save_settings(settings, db)
    return GlobalSettingsRead(
        ENABLE_EMBEDDINGS=settings.get("enable_embeddings", False),
        AGENT_CHAT_RETENTION_DAYS=settings.get("agent_chat_retention_days", 7),
        ENABLE_AUTO_COVER_LETTER=settings.get("enable_auto_cover_letter", False),
        COVER_LETTER_MATCH_THRESHOLD=settings.get("cover_letter_match_threshold", 70),
        COVER_LETTER_LENGTH=settings.get("cover_letter_length", "standard"),
        ENABLE_EMAIL_INTAKE=settings.get("enable_email_intake", False),
        HAS_COMPLETED_ONBOARDING=settings.get("has_completed_onboarding", False),
    )


def _to_provider_read(p: AIProviderModel) -> AIProviderRead:
    return AIProviderRead(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        base_url=p.base_url,
        api_key_masked=mask_secret(p.api_key),
        max_concurrency=getattr(p, "max_concurrency", 1) or 1,
        is_active=p.is_active,
        is_fallback=getattr(p, "is_fallback", False) or False,
        input_cost_per_million=getattr(p, "input_cost_per_million", 0.0) or 0.0,
        output_cost_per_million=getattr(p, "output_cost_per_million", 0.0) or 0.0,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _to_binding_read(b: AITaskBindingModel) -> AITaskBindingRead:
    extra = b.extra_kwargs or {}
    reasoning = extra.get("reasoning_effort", "none")
    custom_extra_body = extra.get("custom_extra_body")
    return AITaskBindingRead(
        id=b.id,
        task_type=b.task_type,
        provider_id=b.provider_id,
        provider_name=b.provider.name if b.provider else None,
        provider_type=b.provider.provider_type if b.provider else None,
        model_name=b.model_name,
        temperature=b.temperature,
        reasoning_effort=reasoning,
        custom_extra_body=custom_extra_body,
        max_tokens=b.max_tokens,
        top_p=b.top_p,
        embedding_dimensions=b.embedding_dimensions,
        extra_kwargs=extra,
        is_active=b.is_active,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


# ---------------------------------------------------------
# AI Providers
# ---------------------------------------------------------


@router.get("/providers", response_model=list[AIProviderRead])
async def list_ai_providers(db: AsyncSession = Depends(get_db)) -> list[AIProviderRead]:
    stmt = select(AIProviderModel).order_by(AIProviderModel.id.asc())
    res = await db.execute(stmt)
    providers = res.scalars().all()
    return [_to_provider_read(p) for p in providers]


@router.post(
    "/providers", response_model=AIProviderRead, status_code=status.HTTP_201_CREATED
)
async def create_ai_provider(
    payload: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
) -> AIProviderRead:
    if payload.is_fallback:
        stmt = select(AIProviderModel).where(AIProviderModel.is_fallback.is_(True))
        existing_fallbacks = (await db.execute(stmt)).scalars().all()
        for ef in existing_fallbacks:
            ef.is_fallback = False

    provider = AIProviderModel(
        name=payload.name.strip(),
        provider_type=payload.provider_type.strip().lower(),
        base_url=payload.base_url.strip() if payload.base_url else None,
        api_key=payload.api_key.strip() if payload.api_key else None,
        max_concurrency=payload.max_concurrency
        if payload.max_concurrency is not None
        else 1,
        is_active=payload.is_active,
        is_fallback=payload.is_fallback,
        input_cost_per_million=payload.input_cost_per_million or 0.0,
        output_cost_per_million=payload.output_cost_per_million or 0.0,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    clear_embeddings_cache()
    invalidate_ai_health_cache()
    return _to_provider_read(provider)


@router.patch("/providers/{provider_id}", response_model=AIProviderRead)
async def update_ai_provider(
    provider_id: int,
    payload: AIProviderUpdate,
    db: AsyncSession = Depends(get_db),
) -> AIProviderRead:
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Provider with ID {provider_id} not found.",
        )

    if payload.is_fallback is True:
        reset_stmt = select(AIProviderModel).where(
            AIProviderModel.id != provider_id, AIProviderModel.is_fallback.is_(True)
        )
        existing_fallbacks = (await db.execute(reset_stmt)).scalars().all()
        for ef in existing_fallbacks:
            ef.is_fallback = False

    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        if field in ("name", "provider_type", "base_url", "api_key") and isinstance(
            val, str
        ):
            val = val.strip() or None
        setattr(provider, field, val)

    await db.commit()
    await db.refresh(provider)
    clear_embeddings_cache()
    invalidate_ai_health_cache()
    return _to_provider_read(provider)


@router.post(
    "/providers/{provider_id}/probe-model",
    response_model=ModelProbeResponse,
)
async def probe_model_capabilities(
    provider_id: int,
    payload: ModelProbeRequest,
    db: AsyncSession = Depends(get_db),
) -> ModelProbeResponse:
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Provider with ID {provider_id} not found.",
        )

    model_name = payload.model_name.strip()
    model_lower = model_name.lower()
    p_type = (provider.provider_type or "openai").lower()
    base_url = _clean_base_url(provider.base_url)

    is_reasoning = _is_reasoning_model(model_name)
    supports_reasoning_effort = False
    supports_chat_template_kwargs = False
    supports_thinking_config = False
    recommended_reasoning_effort = "none"
    recommended_extra_body = None
    detected_tags = []
    notes_list = []

    # 1. Architecture heuristics
    if any(
        k in model_lower for k in ("deepseek-r1", "r1-distill", "qwq", "deepseek_r1")
    ):
        is_reasoning = True
        detected_tags.append("<think>")
        notes_list.append("DeepSeek-R1 / QwQ reasoning architecture detected.")
        recommended_extra_body = {"chat_template_kwargs": {"thinking": False}}
        supports_chat_template_kwargs = True
        supports_reasoning_effort = True
    elif any(k in model_lower for k in ("o1", "o3", "o3-mini")):
        is_reasoning = True
        supports_reasoning_effort = True
        recommended_reasoning_effort = "low"
        notes_list.append("OpenAI o-series reasoning model detected.")
    elif "thinking" in model_lower or "flash-thinking" in model_lower:
        is_reasoning = True
        supports_thinking_config = True
        notes_list.append("Gemini / Google thinking model detected.")
    elif "sonnet-3-7" in model_lower or "claude-3-7" in model_lower:
        is_reasoning = True
        notes_list.append("Anthropic Claude 3.7 hybrid reasoning model detected.")

    # 2. Provider-specific probes
    if p_type == "ollama" and base_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                show_url = (
                    f"{base_url}/api/show"
                    if not base_url.endswith("/api")
                    else f"{base_url}/show"
                )
                resp = await client.post(show_url, json={"name": model_name})
                if resp.status_code == 200:
                    data = resp.json()
                    template = data.get("template", "")
                    if "<think>" in template or "think" in template.lower():
                        is_reasoning = True
                        if "<think>" not in detected_tags:
                            detected_tags.append("<think>")
                        supports_chat_template_kwargs = True
                        recommended_extra_body = {
                            "chat_template_kwargs": {"thinking": False}
                        }
                        notes_list.append("Ollama Modelfile contains <think> tags.")
        except Exception as e:
            logger.debug("Ollama probe failed: %s", e)
    elif p_type in ("openai", "openrouter") and base_url:
        # Check local / LM Studio / vLLM capabilities
        is_local = any(
            h in base_url
            for h in (
                "localhost",
                "127.0.0.1",
                "192.168.",
                "0.0.0.0",
                "10.",
                "172.",
            )
        )
        if is_local:
            try:
                # Test 1-token probe with reasoning_effort
                headers = {"Authorization": f"Bearer {provider.api_key or 'local'}"}
                probe_url = (
                    f"{base_url}/chat/completions"
                    if not base_url.endswith("/chat/completions")
                    else base_url
                )
                probe_payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                    "reasoning_effort": "low",
                }
                async with httpx.AsyncClient(timeout=6.0) as client:
                    resp = await client.post(
                        probe_url, json=probe_payload, headers=headers
                    )
                    if resp.status_code == 200:
                        supports_reasoning_effort = True
                        notes_list.append(
                            "Server natively accepts `reasoning_effort` parameter."
                        )
                    elif resp.status_code == 400 and "reasoning_effort" in resp.text:
                        supports_reasoning_effort = False
            except Exception as e:
                logger.debug("Local reasoning_effort probe failed: %s", e)

    notes = " ".join(notes_list) if notes_list else "Standard completion model."

    return ModelProbeResponse(
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        model_name=model_name,
        is_reasoning_model=is_reasoning,
        supported_reasoning_modes=["none", "low", "medium", "high", "custom"],
        supports_reasoning_effort=supports_reasoning_effort,
        supports_chat_template_kwargs=supports_chat_template_kwargs,
        supports_thinking_config=supports_thinking_config,
        recommended_reasoning_effort=recommended_reasoning_effort,
        recommended_extra_body=recommended_extra_body,
        detected_tags=detected_tags,
        notes=notes,
    )


@router.delete("/providers/{provider_id}", status_code=status.HTTP_200_OK)
async def delete_ai_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Provider with ID {provider_id} not found.",
        )

    # Check total available providers
    all_providers_stmt = select(AIProviderModel).where(
        AIProviderModel.id != provider_id
    )
    remaining_providers = (await db.execute(all_providers_stmt)).scalars().all()
    if not remaining_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the only configured AI provider. At least one provider must remain.",
        )

    # Determine fallback provider (prefer existing GLOBAL_DEFAULT provider if not the one being deleted)
    global_binding_stmt = select(AITaskBindingModel).where(
        AITaskBindingModel.task_type == "GLOBAL_DEFAULT"
    )
    global_binding = (await db.execute(global_binding_stmt)).scalar_one_or_none()

    fallback_provider = next(
        (
            p
            for p in remaining_providers
            if global_binding and p.id == global_binding.provider_id
        ),
        remaining_providers[0],
    )

    # Automatically re-assign any tasks referencing this provider to the fallback provider
    binding_check = select(AITaskBindingModel).where(
        AITaskBindingModel.provider_id == provider_id
    )
    bindings = (await db.execute(binding_check)).scalars().all()
    rebound_tasks = []
    for b in bindings:
        b.provider_id = fallback_provider.id
        rebound_tasks.append(b.task_type)

    await db.delete(provider)
    await db.commit()
    clear_embeddings_cache()
    invalidate_ai_health_cache()
    logger.info(
        "Deleted AI Provider '%s' (ID: %d). Reassigned tasks %s to '%s' (ID: %d).",
        provider.name,
        provider_id,
        rebound_tasks,
        fallback_provider.name,
        fallback_provider.id,
    )
    return {
        "message": f"AI Provider '{provider.name}' deleted. Re-assigned {len(rebound_tasks)} task binding(s) to '{fallback_provider.name}'."
    }


@router.post("/providers/{provider_id}/test", response_model=AIProviderTestResponse)
async def test_ai_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
) -> AIProviderTestResponse:
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Provider with ID {provider_id} not found.",
        )

    # 1. Check if there's an active binding using this provider
    binding_stmt = select(AITaskBindingModel).where(
        AITaskBindingModel.provider_id == provider_id
    )
    binding_res = await db.execute(binding_stmt)
    binding = binding_res.scalars().first()

    # 2. Probe endpoint for discovered models if any
    discovered_models = await _fetch_models_from_endpoint(provider)
    live_models = [m.id for m in discovered_models if m.is_discovered]

    p_type = provider.provider_type.lower()
    resolved_prov = _resolve_provider(p_type)

    if binding:
        model_to_use = binding.model_name
    elif live_models:
        model_to_use = live_models[0]
    else:
        model_to_use = CURATED_MODELS.get(p_type, ["gpt-4o-mini"])[0]

    base_url = _clean_base_url(provider.base_url)
    api_key = provider.api_key or "dummy-key"

    try:
        init_kwargs = {
            "model": model_to_use,
            "model_provider": resolved_prov,
            "temperature": 0.0,
            "max_tokens": 10,
        }
        if base_url:
            init_kwargs["base_url"] = base_url
        if api_key:
            init_kwargs["api_key"] = api_key

        model = init_chat_model(**init_kwargs)
        response = await model.ainvoke(
            [HumanMessage(content="Respond with 'OK' to verify connectivity.")],
            config={"callbacks": [PostgresTracer()]},
        )
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        return AIProviderTestResponse(
            status="success",
            provider_name=provider.name,
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            response=f"Verified model '{model_to_use}': {content.strip()}",
        )
    except Exception as err:
        err_str = str(err)
        # Check if the server is online but responded that no model is loaded or requested model is missing
        if (
            "No models loaded" in err_str
            or "no model loaded" in err_str.lower()
            or "does not exist" in err_str.lower()
        ):
            if live_models:
                models_hint = f"Discovered models on server: {', '.join(live_models)}."
            else:
                models_hint = "Server is online, but no model is currently loaded into memory. Please load a model in LM Studio / Ollama."

            return AIProviderTestResponse(
                status="success",
                provider_name=provider.name,
                provider_type=provider.provider_type,
                base_url=provider.base_url,
                response=f"Endpoint reached ({models_hint})",
            )

        logger.error(
            "Provider test probe failed for %s: %s", provider.name, err, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider probe failed for '{provider.name}' ({provider.provider_type}): {err_str}",
        )


@router.get("/providers/{provider_id}/models", response_model=AIProviderModelsResponse)
async def list_provider_models(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
) -> AIProviderModelsResponse:
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Provider with ID {provider_id} not found.",
        )

    models = await _fetch_models_from_endpoint(provider)
    return AIProviderModelsResponse(
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        models=models,
    )


# ---------------------------------------------------------
# Task Bindings
# ---------------------------------------------------------


@router.get("/bindings", response_model=list[AITaskBindingRead])
async def list_ai_task_bindings(
    db: AsyncSession = Depends(get_db),
) -> list[AITaskBindingRead]:
    stmt = (
        select(AITaskBindingModel)
        .options(joinedload(AITaskBindingModel.provider))
        .order_by(AITaskBindingModel.task_type.asc())
    )
    res = await db.execute(stmt)
    bindings = res.scalars().all()
    return [_to_binding_read(b) for b in bindings]


@router.put(
    "/bindings/{task_type}",
    response_model=AITaskBindingRead,
    status_code=status.HTTP_200_OK,
)
async def set_ai_task_binding(
    task_type: str,
    payload: AITaskBindingCreate,
    db: AsyncSession = Depends(get_db),
) -> AITaskBindingRead:
    task_type_norm = task_type.strip().upper()

    # Validate provider exists
    prov_stmt = select(AIProviderModel).where(AIProviderModel.id == payload.provider_id)
    prov_res = await db.execute(prov_stmt)
    provider = prov_res.scalar_one_or_none()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI Provider with ID {payload.provider_id} not found.",
        )

    stmt = select(AITaskBindingModel).where(
        AITaskBindingModel.task_type == task_type_norm
    )
    res = await db.execute(stmt)
    binding = res.scalar_one_or_none()

    extra = dict(payload.extra_kwargs or {})
    if payload.reasoning_effort is not None:
        extra["reasoning_effort"] = payload.reasoning_effort.strip().lower()
    if payload.custom_extra_body is not None:
        extra["custom_extra_body"] = payload.custom_extra_body

    if not binding:
        binding = AITaskBindingModel(
            task_type=task_type_norm,
            provider_id=payload.provider_id,
            model_name=payload.model_name.strip(),
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
            embedding_dimensions=payload.embedding_dimensions,
            extra_kwargs=extra,
            is_active=payload.is_active,
        )
        db.add(binding)
    else:
        binding.provider_id = payload.provider_id
        binding.model_name = payload.model_name.strip()
        binding.temperature = payload.temperature
        binding.max_tokens = payload.max_tokens
        binding.top_p = payload.top_p
        binding.embedding_dimensions = payload.embedding_dimensions
        binding.extra_kwargs = extra
        binding.is_active = payload.is_active

    await db.commit()
    await db.refresh(binding)
    binding.provider = provider
    clear_embeddings_cache()
    invalidate_ai_health_cache()
    return _to_binding_read(binding)


@router.delete("/bindings/{task_type}", status_code=status.HTTP_200_OK)
async def delete_ai_task_binding(
    task_type: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    task_type_norm = task_type.strip().upper()
    stmt = delete(AITaskBindingModel).where(
        AITaskBindingModel.task_type == task_type_norm
    )
    result = await db.execute(stmt)
    await db.commit()

    deleted_count = getattr(result, "rowcount", 0) or 0
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task binding for '{task_type_norm}' not found.",
        )

    clear_embeddings_cache()
    invalidate_ai_health_cache()
    return {"message": f"Task binding for '{task_type_norm}' removed."}


@router.post("/bindings/{task_type}/test", response_model=AITaskTestResponse)
async def test_ai_task_binding(
    task_type: str,
    db: AsyncSession = Depends(get_db),
) -> AITaskTestResponse:
    task_type_norm = task_type.strip().upper()

    stmt = (
        select(AITaskBindingModel)
        .options(joinedload(AITaskBindingModel.provider))
        .where(AITaskBindingModel.task_type == task_type_norm)
    )
    res = await db.execute(stmt)
    binding = res.scalar_one_or_none()

    if not binding or not binding.provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task binding '{task_type_norm}' is not configured in the AI Registry.",
        )

    provider = binding.provider

    try:
        if task_type_norm == "EMBEDDING":
            emb_model = await get_task_embeddings_model(db)
            vector = await emb_model.aembed_query("Connectivity verification probe.")
            return AITaskTestResponse(
                status="success",
                task_type=task_type_norm,
                provider_name=provider.name,
                provider_type=provider.provider_type,
                model_name=binding.model_name,
                base_url=provider.base_url,
                response=f"Generated embedding vector of dimension {len(vector)}.",
            )
        else:
            chat_model = await get_task_chat_model(
                db, task_type=task_type_norm, max_tokens=15
            )
            response = await chat_model.ainvoke(
                [HumanMessage(content="Respond with 'OK' to verify connectivity.")],
                config={"callbacks": [PostgresTracer()]},
            )
            content = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
            return AITaskTestResponse(
                status="success",
                task_type=task_type_norm,
                provider_name=provider.name,
                provider_type=provider.provider_type,
                model_name=binding.model_name,
                base_url=provider.base_url,
                response=content.strip(),
            )
    except Exception as err:
        logger.error(
            "Task binding test failed for %s: %s", task_type_norm, err, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Task binding test failed for '{task_type_norm}' ({provider.provider_type} / {binding.model_name}): {err!s}",
        )


@router.get("/pricing-rates", response_model=list[PricingRateRead])
async def get_pricing_rates_endpoint() -> list[PricingRateRead]:
    from app.services.pricing_service import get_all_pricing_rates

    return [PricingRateRead(**item) for item in get_all_pricing_rates()]


@router.put("/pricing-rates", response_model=list[PricingRateRead])
async def update_pricing_rates_endpoint(
    payload: PricingRateBatchUpdate,
) -> list[PricingRateRead]:
    from app.services.pricing_service import (
        get_all_pricing_rates,
        update_pricing_rate_override,
    )

    for item in payload.rates:
        update_pricing_rate_override(
            key=item.key,
            input_cost=item.input_cost_per_million,
            output_cost=item.output_cost_per_million,
        )
    return [PricingRateRead(**r) for r in get_all_pricing_rates()]


@router.post("/pricing-rates/reset", response_model=list[PricingRateRead])
async def reset_pricing_rates_endpoint() -> list[PricingRateRead]:
    from app.services.pricing_service import reset_pricing_rates

    return [PricingRateRead(**item) for item in reset_pricing_rates()]


@router.get("/usage-overview", response_model=UsageOverviewRead)
async def get_usage_overview_endpoint(
    db: AsyncSession = Depends(get_db),
) -> UsageOverviewRead:
    from datetime import UTC, datetime

    from app.models.diagnostics import TraceEventModel
    from app.services.pricing_service import (
        calculate_comparative_provider_costs,
        extract_usage_from_payload,
    )

    now = datetime.now(UTC)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    stmt = select(TraceEventModel).where(TraceEventModel.event_type != "health_check")
    result = await db.execute(stmt)
    records = result.scalars().all()

    monthly_tokens = 0
    monthly_prompt_tokens = 0
    monthly_completion_tokens = 0
    monthly_spend = 0.0
    monthly_savings = 0.0

    all_time_tokens = 0
    all_time_spend = 0.0
    all_time_savings = 0.0

    local_calls = 0
    total_calls = 0
    assessment_cost_total = 0.0
    assessment_calls = 0

    task_breakdown: dict[str, dict[str, Any]] = {}

    for r in records:
        payload = r.payload or {}
        usage = extract_usage_from_payload(payload)
        t_tokens = usage["total_tokens"]
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        cost = usage["estimated_cost"]
        savings = usage["estimated_savings"]
        is_local = usage["is_local"]

        if t_tokens > 0 or r.category == "llm":
            total_calls += 1
            if is_local:
                local_calls += 1

            all_time_tokens += t_tokens
            all_time_spend += cost
            all_time_savings += savings

            # Timestamp check for current month
            t_time = r.timestamp
            if t_time and t_time.tzinfo is None:
                t_time = t_time.replace(tzinfo=UTC)

            if t_time and t_time >= start_of_month:
                monthly_tokens += t_tokens
                monthly_prompt_tokens += p_tokens
                monthly_completion_tokens += c_tokens
                monthly_spend += cost
                monthly_savings += savings

            # Group by task name / event type
            task_name = (
                payload.get("task_type")
                or payload.get("name")
                or r.event_type
                or "General LLM"
            )
            if task_name not in task_breakdown:
                task_breakdown[task_name] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "savings_usd": 0.0,
                }
            task_breakdown[task_name]["calls"] += 1
            task_breakdown[task_name]["tokens"] += t_tokens
            task_breakdown[task_name]["cost_usd"] = round(
                task_breakdown[task_name]["cost_usd"] + cost, 4
            )
            task_breakdown[task_name]["savings_usd"] = round(
                task_breakdown[task_name]["savings_usd"] + savings, 4
            )

            if (
                "assessment" in task_name.lower()
                or "eval" in task_name.lower()
                or "fit" in task_name.lower()
            ):
                assessment_calls += 1
                assessment_cost_total += cost

    local_pct = (
        round((local_calls / total_calls * 100.0), 1) if total_calls > 0 else 0.0
    )
    avg_assessment_cost = (
        round(assessment_cost_total / assessment_calls, 4)
        if assessment_calls > 0
        else (round(all_time_spend / total_calls, 4) if total_calls > 0 else 0.0)
    )

    # Check active providers to dynamically synchronize with latest configured rates
    prov_stmt = select(AIProviderModel).where(AIProviderModel.is_active.is_(True))
    providers_res = await db.execute(prov_stmt)
    active_providers = providers_res.scalars().all()

    primary_provider = next(
        (p for p in active_providers if not p.is_fallback),
        active_providers[0] if active_providers else None,
    )

    if primary_provider is not None:
        p_in = (
            primary_provider.input_cost_per_million
            if primary_provider.input_cost_per_million is not None
            else 0.0
        )
        p_out = (
            primary_provider.output_cost_per_million
            if primary_provider.output_cost_per_million is not None
            else 0.0
        )
        is_prov_local = primary_provider.provider_type.lower() in (
            "ollama",
            "local",
        ) or (p_in == 0.0 and p_out == 0.0)

        if is_prov_local:
            monthly_spend = 0.0
            monthly_savings = round(
                (monthly_prompt_tokens * 0.15 / 1_000_000.0)
                + (monthly_completion_tokens * 0.60 / 1_000_000.0),
                4,
            )
            if monthly_tokens > 0 and monthly_savings == 0.0:
                monthly_savings = round(monthly_tokens * 0.0001, 4)
            local_pct = 100.0
        else:
            monthly_spend = round(
                (monthly_prompt_tokens * p_in / 1_000_000.0)
                + (monthly_completion_tokens * p_out / 1_000_000.0),
                4,
            )
            monthly_savings = 0.0
            local_pct = 0.0

    comparative = calculate_comparative_provider_costs(
        monthly_input_tokens=monthly_prompt_tokens,
        monthly_output_tokens=monthly_completion_tokens,
        current_spend_usd=monthly_spend,
        is_current_local=(local_pct >= 50.0),
    )

    return UsageOverviewRead(
        monthly_tokens=monthly_tokens,
        monthly_spend_usd=round(monthly_spend, 4),
        monthly_savings_usd=round(monthly_savings, 4),
        all_time_tokens=all_time_tokens,
        all_time_spend_usd=round(all_time_spend, 4),
        all_time_savings_usd=round(all_time_savings, 4),
        local_inference_percentage=local_pct,
        total_llm_calls=total_calls,
        avg_cost_per_assessment=avg_assessment_cost,
        task_breakdown=task_breakdown,
        comparative_costs=comparative,
    )
