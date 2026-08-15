import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model, get_task_embeddings_model
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
import httpx
from langchain.chat_models import init_chat_model
from app.core.llm_factory import _clean_base_url, _resolve_provider
from app.schemas.ai_config import (
    AIProviderCreate,
    AIProviderModelsResponse,
    AIProviderRead,
    AIProviderTestResponse,
    AIProviderUpdate,
    AITaskBindingCreate,
    AITaskBindingRead,
    AITaskBindingUpdate,
    AITaskTestResponse,
    DiscoveredModel,
    mask_secret,
)

CURATED_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-4o-mini", "gpt-4o", "o3-mini", "text-embedding-3-small", "text-embedding-3-large"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
    "google_genai": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "text-embedding-004"],
    "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "text-embedding-004"],
    "ollama": ["llama3.2", "llama3.1", "qwen2.5", "mistral", "nomic-embed-text", "bge-m3"],
    "openrouter": ["meta-llama/llama-3.3-70b-instruct", "anthropic/claude-3.5-sonnet", "openai/gpt-4o-mini"],
    "custom": ["qwen3.5-4b", "llama3.1", "mistral-7b"],
}


async def _fetch_models_from_endpoint(provider: AIProviderModel) -> list[DiscoveredModel]:
    p_type = provider.provider_type.lower()
    base_url = _clean_base_url(provider.base_url)
    discovered: list[str] = []

    if base_url:
        headers: dict[str, str] = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        async with httpx.AsyncClient(timeout=3.5) as client:
            try:
                if p_type == "ollama":
                    url = f"{base_url}/api/tags" if not base_url.endswith("/api") else f"{base_url}/tags"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("models", []):
                            if "name" in m:
                                discovered.append(m["name"])
                else:
                    url = f"{base_url}/models" if not base_url.endswith("/models") else base_url
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("data", []):
                            if "id" in m:
                                discovered.append(m["id"])
            except Exception as e:
                logger.warning("Live model probe skipped/failed for provider '%s': %s", provider.name, e)

    models_out: list[DiscoveredModel] = []
    seen = set()
    for m in discovered:
        if m not in seen:
            seen.add(m)
            models_out.append(DiscoveredModel(id=m, name=m, is_discovered=True))

    curated = CURATED_MODELS.get(p_type, CURATED_MODELS["custom"])
    for m in curated:
        if m not in seen:
            seen.add(m)
            models_out.append(DiscoveredModel(id=m, name=m, is_discovered=False))

    return models_out


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Provider Registry & Task Bindings"])


def _to_provider_read(p: AIProviderModel) -> AIProviderRead:
    return AIProviderRead(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        base_url=p.base_url,
        api_key_masked=mask_secret(p.api_key),
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _to_binding_read(b: AITaskBindingModel) -> AITaskBindingRead:
    return AITaskBindingRead(
        id=b.id,
        task_type=b.task_type,
        provider_id=b.provider_id,
        provider_name=b.provider.name if b.provider else None,
        provider_type=b.provider.provider_type if b.provider else None,
        model_name=b.model_name,
        temperature=b.temperature,
        max_tokens=b.max_tokens,
        top_p=b.top_p,
        embedding_dimensions=b.embedding_dimensions,
        extra_kwargs=b.extra_kwargs or {},
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


@router.post("/providers", response_model=AIProviderRead, status_code=status.HTTP_201_CREATED)
async def create_ai_provider(
    payload: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
) -> AIProviderRead:
    provider = AIProviderModel(
        name=payload.name.strip(),
        provider_type=payload.provider_type.strip().lower(),
        base_url=payload.base_url.strip() if payload.base_url else None,
        api_key=payload.api_key.strip() if payload.api_key else None,
        is_active=payload.is_active,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
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

    data = payload.model_dump(exclude_unset=True)
    for field, val in data.items():
        if field in ("name", "provider_type", "base_url", "api_key") and isinstance(val, str):
            val = val.strip() or None
        setattr(provider, field, val)

    await db.commit()
    await db.refresh(provider)
    return _to_provider_read(provider)


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

    # Check for active task bindings
    binding_check = select(AITaskBindingModel).where(AITaskBindingModel.provider_id == provider_id)
    bindings = (await db.execute(binding_check)).scalars().all()
    if bindings:
        bound_tasks = [b.task_type for b in bindings]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete provider '{provider.name}': it is referenced by task bindings: {bound_tasks}.",
        )

    await db.delete(provider)
    await db.commit()
    return {"message": f"AI Provider '{provider.name}' deleted successfully."}


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

    # First check if there's an active binding using this provider
    binding_stmt = select(AITaskBindingModel).where(AITaskBindingModel.provider_id == provider_id)
    binding_res = await db.execute(binding_stmt)
    binding = binding_res.scalars().first()

    p_type = provider.provider_type.lower()
    resolved_prov = _resolve_provider(p_type)
    model_to_use = binding.model_name if binding else (CURATED_MODELS.get(p_type, ["gpt-4o-mini"])[0])
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
        response = await model.ainvoke([HumanMessage(content="Respond with 'OK' to verify connectivity.")])
        content = response.content if isinstance(response.content, str) else str(response.content)

        return AIProviderTestResponse(
            status="success",
            provider_name=provider.name,
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            response=content.strip(),
        )
    except Exception as err:
        logger.error("Provider test probe failed for %s: %s", provider.name, err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider probe failed for '{provider.name}' ({provider.provider_type}): {str(err)}",
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
async def list_ai_task_bindings(db: AsyncSession = Depends(get_db)) -> list[AITaskBindingRead]:
    stmt = (
        select(AITaskBindingModel)
        .options(joinedload(AITaskBindingModel.provider))
        .order_by(AITaskBindingModel.task_type.asc())
    )
    res = await db.execute(stmt)
    bindings = res.scalars().all()
    return [_to_binding_read(b) for b in bindings]


@router.put("/bindings/{task_type}", response_model=AITaskBindingRead, status_code=status.HTTP_200_OK)
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

    stmt = select(AITaskBindingModel).where(AITaskBindingModel.task_type == task_type_norm)
    res = await db.execute(stmt)
    binding = res.scalar_one_or_none()

    if not binding:
        binding = AITaskBindingModel(
            task_type=task_type_norm,
            provider_id=payload.provider_id,
            model_name=payload.model_name.strip(),
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
            embedding_dimensions=payload.embedding_dimensions,
            extra_kwargs=payload.extra_kwargs or {},
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
        binding.extra_kwargs = payload.extra_kwargs or {}
        binding.is_active = payload.is_active

    await db.commit()
    await db.refresh(binding)
    binding.provider = provider
    return _to_binding_read(binding)


@router.delete("/bindings/{task_type}", status_code=status.HTTP_200_OK)
async def delete_ai_task_binding(
    task_type: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    task_type_norm = task_type.strip().upper()
    stmt = delete(AITaskBindingModel).where(AITaskBindingModel.task_type == task_type_norm)
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task binding for '{task_type_norm}' not found.",
        )

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
            chat_model = await get_task_chat_model(db, task_type=task_type_norm, max_tokens=15)
            response = await chat_model.ainvoke([HumanMessage(content="Respond with 'OK' to verify connectivity.")])
            content = response.content if isinstance(response.content, str) else str(response.content)
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
        logger.error("Task binding test failed for %s: %s", task_type_norm, err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Task binding test failed for '{task_type_norm}' ({provider.provider_type} / {binding.model_name}): {str(err)}",
        )
