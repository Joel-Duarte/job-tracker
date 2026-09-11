"""VRAM and lifecycle management for local/cloud LLM provider engines."""

import logging
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_factory import _clean_base_url
from app.models.ai_providers import AIProviderModel, AITaskBindingModel

logger = logging.getLogger(__name__)


def detect_provider_engine(
    base_url: str | None, provider_type: str | None = None
) -> str:
    """Detects engine identifier: lmstudio, ollama, vllm, sglang, or generic."""
    if not base_url:
        p_type = (provider_type or "").lower()
        if "ollama" in p_type:
            return "ollama"
        return "generic"

    url_low = base_url.lower()
    if ":1234" in url_low or "lmstudio" in url_low or "lm-studio" in url_low:
        return "lmstudio"
    if ":11434" in url_low or "ollama" in url_low:
        return "ollama"
    if ":8000" in url_low or "vllm" in url_low:
        return "vllm"
    if ":30000" in url_low or "sglang" in url_low:
        return "sglang"
    return "generic"


async def release_engine_vram(
    base_url: str | None,
    model_name: str | None = None,
    api_key: str | None = None,
    provider_type: str | None = None,
) -> dict[str, Any]:
    """Dispatches engine-specific sleep or unload HTTP call to free GPU VRAM."""
    clean_url = _clean_base_url(base_url) if base_url else ""
    engine = detect_provider_engine(clean_url, provider_type)

    parsed = urlparse(clean_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else clean_url

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if engine == "lmstudio":
                unload_url = f"{root_url}/api/v0/models/unload"
                payload = {"model": model_name} if model_name else {}
                resp = await client.post(unload_url, json=payload, headers=headers)
                if resp.status_code in (200, 204):
                    return {
                        "success": True,
                        "engine": "lmstudio",
                        "message": "Models unloaded from LM Studio VRAM",
                    }
                fallback_url = f"{root_url}/v1/models/unload"
                resp2 = await client.post(fallback_url, json=payload, headers=headers)
                return {
                    "success": resp2.status_code in (200, 204),
                    "engine": "lmstudio",
                    "message": f"LM Studio model unload dispatched: HTTP {resp2.status_code}",
                }

            elif engine == "ollama":
                generate_url = f"{root_url}/api/generate"
                payload = {"model": model_name or "", "keep_alive": 0}
                resp = await client.post(generate_url, json=payload, headers=headers)
                return {
                    "success": resp.status_code in (200, 204),
                    "engine": "ollama",
                    "message": f"Ollama keep_alive:0 dispatched: HTTP {resp.status_code}",
                }

            elif engine == "vllm":
                sleep_url = f"{root_url}/sleep"
                payload = {"level": 1}
                resp = await client.post(sleep_url, json=payload, headers=headers)
                return {
                    "success": resp.status_code in (200, 204),
                    "engine": "vllm",
                    "message": f"vLLM sleep mode dispatched: HTTP {resp.status_code}",
                }

            elif engine == "sglang":
                release_url = f"{root_url}/release_memory"
                resp = await client.post(release_url, headers=headers)
                return {
                    "success": resp.status_code in (200, 204),
                    "engine": "sglang",
                    "message": f"SGLang memory release dispatched: HTTP {resp.status_code}",
                }

            else:
                return {
                    "success": True,
                    "engine": "generic",
                    "message": "Generic/cloud provider requires no local VRAM release.",
                }
    except Exception as exc:
        logger.warning(f"Error releasing engine VRAM for base_url {base_url}: {exc}")
        return {"success": False, "engine": engine, "message": str(exc)}


async def release_provider_vram(provider_id: int, db: AsyncSession) -> dict[str, Any]:
    """Loads provider record from DB and triggers VRAM release."""
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()
    if not provider:
        raise ValueError(f"Provider with ID {provider_id} not found.")

    bind_stmt = select(AITaskBindingModel).where(
        AITaskBindingModel.provider_id == provider_id,
        AITaskBindingModel.is_active.is_(True),
    )
    bindings = (await db.execute(bind_stmt)).scalars().all()
    model_name = bindings[0].model_name if bindings else None

    return await release_engine_vram(
        base_url=provider.base_url,
        model_name=model_name,
        api_key=provider.api_key,
        provider_type=provider.provider_type,
    )


async def get_provider_vram_status(
    provider_id: int, db: AsyncSession
) -> dict[str, Any]:
    """Probes engine to check if models are loaded in VRAM or sleeping."""
    stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    res = await db.execute(stmt)
    provider = res.scalar_one_or_none()
    if not provider:
        raise ValueError(f"Provider with ID {provider_id} not found.")

    clean_url = _clean_base_url(provider.base_url) if provider.base_url else ""
    engine = detect_provider_engine(clean_url, provider.provider_type)

    if engine == "generic":
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "engine": "generic",
            "status": "ACTIVE",
            "is_loaded": True,
            "vram_allocated_mb": 0,
            "message": "Cloud provider always ready.",
        }

    parsed = urlparse(clean_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else clean_url

    headers = {}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            if engine == "lmstudio":
                resp = await client.get(f"{root_url}/api/v0/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    loaded = len(data.get("data", [])) > 0
                    return {
                        "provider_id": provider_id,
                        "provider_name": provider.name,
                        "engine": "lmstudio",
                        "status": "ACTIVE" if loaded else "SLEEPING",
                        "is_loaded": loaded,
                        "vram_allocated_mb": 4096 if loaded else 0,
                    }

            elif engine == "ollama":
                resp = await client.get(f"{root_url}/api/ps", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    loaded = len(models) > 0
                    vram = sum(m.get("size_vram", 0) for m in models) // (1024 * 1024)
                    return {
                        "provider_id": provider_id,
                        "provider_name": provider.name,
                        "engine": "ollama",
                        "status": "ACTIVE" if loaded else "SLEEPING",
                        "is_loaded": loaded,
                        "vram_allocated_mb": vram,
                    }
    except Exception as exc:
        logger.debug("Failed probing VRAM status for provider %d: %s", provider_id, exc)

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "engine": engine,
        "status": "UNKNOWN",
        "is_loaded": False,
        "vram_allocated_mb": 0,
        "message": "Could not connect to local engine status endpoint.",
    }
