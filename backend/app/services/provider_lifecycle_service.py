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
    base_url: str | None,
    provider_type: str | None = None,
    engine_type: str | None = None,
    response_headers: Any | None = None,
) -> str:
    """Detects engine identifier: lmstudio, ollama, vllm, sglang, or generic.

    Manual engine_type strictly overrides heuristic detection.
    """
    if engine_type and engine_type.lower() not in ("auto", "none", ""):
        return engine_type.lower()

    p_type = (provider_type or "").lower()
    if p_type == "ollama":
        return "ollama"

    # API Fingerprint detection via HTTP headers if available
    if response_headers:
        server_header = ""
        if hasattr(response_headers, "get"):
            server_header = (response_headers.get("server") or "").lower()
        if "lmstudio" in server_header:
            return "lmstudio"
        if "ollama" in server_header:
            return "ollama"
        if "vllm" in server_header:
            return "vllm"
        if "sglang" in server_header:
            return "sglang"

    if not base_url:
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

    # If it's a private network IP or localhost with an OpenAI-compatible/custom type,
    # default to local lmstudio engine for lifecycle support
    is_private_ip = (
        "127.0.0.1" in url_low
        or "localhost" in url_low
        or "192.168." in url_low
        or "10." in url_low
        or "172.16." in url_low
    )
    if is_private_ip and p_type in ("openai", "custom", "local"):
        return "lmstudio"

    return "generic"


async def release_engine_vram(
    base_url: str | None,
    model_name: str | None = None,
    api_key: str | None = None,
    provider_type: str | None = None,
    engine_type: str | None = None,
    candidate_models: list[str] | None = None,
) -> dict[str, Any]:
    """Dispatches engine-specific sleep or unload HTTP call to free GPU VRAM."""
    clean_url = _clean_base_url(base_url) if base_url else ""
    engine = detect_provider_engine(clean_url, provider_type, engine_type)

    parsed = urlparse(clean_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else clean_url

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if engine == "lmstudio":
                # 1. Discover loaded models in LM Studio to resolve instance_id
                loaded_instances: list[dict[str, str]] = []

                # Probe native LM Studio 0.4.0+ API
                try:
                    list_resp = await client.get(
                        f"{root_url}/api/v1/models", headers=headers
                    )
                    if list_resp.status_code == 200:
                        data = list_resp.json()
                        models_list = data.get("models") or data.get("data") or []
                        for m in models_list:
                            if not isinstance(m, dict):
                                continue
                            key = m.get("key") or m.get("id") or ""
                            insts = m.get("loaded_instances")
                            if insts and isinstance(insts, list):
                                for inst in insts:
                                    inst_id = inst.get("id") or key
                                    if inst_id:
                                        loaded_instances.append(
                                            {"instance_id": inst_id, "id": key}
                                        )
                            elif m.get("instance_id") or m.get("state") == "loaded":
                                inst_id = m.get("instance_id") or key
                                if inst_id:
                                    loaded_instances.append(
                                        {"instance_id": inst_id, "id": key}
                                    )
                except Exception as list_err:
                    logger.debug("GET /api/v1/models failed: %s", list_err)

                # Fallback: probe /api/v0/models where state == 'loaded'
                if not loaded_instances:
                    try:
                        list_v0 = await client.get(
                            f"{root_url}/api/v0/models", headers=headers
                        )
                        if list_v0.status_code == 200:
                            data_v0 = list_v0.json()
                            for item in data_v0.get("data") or []:
                                if item.get("state") == "loaded":
                                    inst_id = item.get("id")
                                    if inst_id:
                                        loaded_instances.append(
                                            {"instance_id": inst_id, "id": inst_id}
                                        )
                    except Exception as list_v0_err:
                        logger.debug("GET /api/v0/models failed: %s", list_v0_err)

                # If no models are loaded in LM Studio, VRAM is already free
                if not loaded_instances:
                    return {
                        "success": True,
                        "engine": "lmstudio",
                        "message": "LM Studio VRAM is already clear (no models currently loaded).",
                    }

                # 2. Select target instance to unload (strictly matching target/candidate models)
                target_instances: list[str] = []
                pool_to_check: list[str] = []
                if model_name:
                    pool_to_check.append(model_name)
                if candidate_models:
                    for cm in candidate_models:
                        if cm not in pool_to_check:
                            pool_to_check.append(cm)

                def _matches(target: str, entry: dict[str, str]) -> bool:
                    t_clean = target.lower().strip()
                    t_base = t_clean.replace(":", "-").replace("/", "-")
                    m_id = entry["id"].lower()
                    i_id = entry["instance_id"].lower()
                    m_base = m_id.replace(":", "-").replace("/", "-")
                    i_base = i_id.replace(":", "-").replace("/", "-")
                    return (
                        t_clean in m_id
                        or m_id in t_clean
                        or t_clean in i_id
                        or i_id in t_clean
                        or t_base in m_base
                        or m_base in t_base
                        or t_base in i_base
                        or i_base in t_base
                    )

                for target in pool_to_check:
                    for entry in loaded_instances:
                        if (
                            _matches(target, entry)
                            and entry["instance_id"] not in target_instances
                        ):
                            target_instances.append(entry["instance_id"])

                # If no target matched any loaded model, but only 1 model is loaded in LM Studio
                # and no explicit model_name was mandated:
                if (
                    not target_instances
                    and len(loaded_instances) == 1
                    and not model_name
                ):
                    target_instances.append(loaded_instances[0]["instance_id"])

                if not target_instances:
                    loaded_names = [e["id"] for e in loaded_instances]
                    return {
                        "success": True,
                        "engine": "lmstudio",
                        "message": f"Model '{model_name or 'target'}' is not currently loaded in LM Studio (loaded: {', '.join(loaded_names)}).",
                    }

                # 3. Dispatch native POST /api/v1/models/unload with instance_id
                unloaded_names: list[str] = []
                for inst_id in target_instances:
                    native_url = f"{root_url}/api/v1/models/unload"
                    payload = {"instance_id": inst_id}
                    try:
                        resp = await client.post(
                            native_url, json=payload, headers=headers
                        )
                        text_body = resp.text if hasattr(resp, "text") else ""
                        is_unexpected = (
                            "unexpected endpoint" in text_body.lower()
                            or "unexpected method" in text_body.lower()
                        )
                        if resp.status_code in (200, 204) and not is_unexpected:
                            unloaded_names.append(inst_id)
                            continue
                    except Exception as post_err:
                        logger.debug(
                            "POST /api/v1/models/unload failed for %s: %s",
                            inst_id,
                            post_err,
                        )

                if unloaded_names:
                    return {
                        "success": True,
                        "engine": "lmstudio",
                        "message": f"Model '{', '.join(unloaded_names)}' unloaded from LM Studio VRAM",
                    }
                else:
                    return {
                        "success": False,
                        "engine": "lmstudio",
                        "message": f"LM Studio did not unload model '{model_name or 'active'}'. Verify LM Studio server status.",
                    }

            elif engine == "ollama":
                # 1. Discover loaded models in Ollama via GET /api/ps
                loaded_models: list[str] = []
                try:
                    ps_resp = await client.get(f"{root_url}/api/ps", headers=headers)
                    if ps_resp.status_code == 200:
                        ps_data = ps_resp.json()
                        for m in ps_data.get("models", []):
                            m_name = m.get("name") or m.get("model") or ""
                            if m_name:
                                loaded_models.append(m_name)
                except Exception as ps_err:
                    logger.debug("GET /api/ps failed in Ollama: %s", ps_err)

                # If no models are running in Ollama, VRAM is already clear
                if not loaded_models and model_name is None:
                    return {
                        "success": True,
                        "engine": "ollama",
                        "message": "Ollama VRAM is already clear (no models currently loaded).",
                    }

                # 2. Select models to unload
                pool_to_check: list[str] = []
                if model_name:
                    pool_to_check.append(model_name)
                if candidate_models:
                    for cm in candidate_models:
                        if cm not in pool_to_check:
                            pool_to_check.append(cm)

                target_models: list[str] = []

                def _ollama_matches(target: str, loaded: str) -> bool:
                    t_clean = target.lower().strip()
                    l_clean = loaded.lower().strip()
                    t_tag = t_clean.split(":")[0]
                    l_tag = l_clean.split(":")[0]
                    return (
                        t_clean == l_clean
                        or t_tag == l_tag
                        or t_clean in l_clean
                        or l_clean in t_clean
                    )

                for target in pool_to_check:
                    for loaded in loaded_models:
                        if (
                            _ollama_matches(target, loaded)
                            and loaded not in target_models
                        ):
                            target_models.append(loaded)

                # If no candidates matched running models, but models are running and no explicit model was requested, target running models
                if not target_models:
                    if loaded_models and not model_name:
                        target_models.extend(loaded_models)
                    elif model_name:
                        target_models.append(model_name)

                # 3. Unload target models via POST /api/generate with keep_alive: 0
                unloaded: list[str] = []
                for mod in target_models:
                    try:
                        generate_url = f"{root_url}/api/generate"
                        payload = {"model": mod, "keep_alive": 0}
                        resp = await client.post(
                            generate_url, json=payload, headers=headers
                        )
                        if resp.status_code in (200, 204):
                            unloaded.append(mod)
                    except Exception as gen_err:
                        logger.debug(
                            "Failed unloading Ollama model %s: %s", mod, gen_err
                        )

                if unloaded:
                    return {
                        "success": True,
                        "engine": "ollama",
                        "message": f"Model '{', '.join(unloaded)}' unloaded from Ollama VRAM",
                    }
                else:
                    return {
                        "success": False,
                        "engine": "ollama",
                        "message": f"Ollama could not unload models: {', '.join(target_models) if target_models else 'none'}",
                    }

            elif engine == "vllm":
                # Check if vLLM supports sleep mode or is already sleeping
                try:
                    sleep_check = await client.get(
                        f"{root_url}/is_sleeping", headers=headers, timeout=2.0
                    )
                    if sleep_check.status_code == 200:
                        is_sleeping = (
                            sleep_check.json()
                            if isinstance(sleep_check.json(), bool)
                            else sleep_check.json().get("is_sleeping", False)
                        )
                        if is_sleeping:
                            return {
                                "success": True,
                                "engine": "vllm",
                                "message": "vLLM is already in sleep mode (GPU VRAM offloaded).",
                            }
                except Exception:
                    pass

                # Dispatch sleep mode (Level 1: Offloads weights to RAM, discards KV cache)
                sleep_url = f"{root_url}/sleep"
                resp = await client.post(
                    f"{sleep_url}?level=1", json={"level": 1}, headers=headers
                )
                if resp.status_code in (200, 204):
                    return {
                        "success": True,
                        "engine": "vllm",
                        "message": "vLLM sleep mode activated (weights offloaded to RAM).",
                    }
                else:
                    return {
                        "success": False,
                        "engine": "vllm",
                        "message": f"vLLM sleep mode returned HTTP {resp.status_code}",
                    }

            elif engine == "sglang":
                # Dispatch memory release or cache flush
                release_url = f"{root_url}/release_memory"
                try:
                    resp = await client.post(release_url, headers=headers)
                    if resp.status_code in (200, 204):
                        return {
                            "success": True,
                            "engine": "sglang",
                            "message": "SGLang GPU memory release dispatched successfully.",
                        }
                except Exception:
                    pass

                # Fallback to flush_cache
                flush_url = f"{root_url}/flush_cache"
                try:
                    resp_flush = await client.post(flush_url, headers=headers)
                    if resp_flush.status_code in (200, 204):
                        return {
                            "success": True,
                            "engine": "sglang",
                            "message": "SGLang cache flushed successfully.",
                        }
                except Exception:
                    pass

                return {
                    "success": False,
                    "engine": "sglang",
                    "message": "Could not dispatch memory release or cache flush to SGLang.",
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


async def release_provider_vram(
    provider_id: int,
    db: AsyncSession,
    model_name: str | None = None,
) -> dict[str, Any]:
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

    target_model = model_name
    if not target_model:
        # Prioritize GLOBAL_DEFAULT binding
        global_bind = next(
            (b for b in bindings if b.task_type == "GLOBAL_DEFAULT" and b.model_name),
            None,
        )
        if global_bind:
            target_model = global_bind.model_name
        else:
            # Fall back to any generative task binding, strictly ignoring EMBEDDING
            gen_bind = next(
                (b for b in bindings if b.task_type != "EMBEDDING" and b.model_name),
                None,
            )
            if gen_bind:
                target_model = gen_bind.model_name
            elif bindings:
                target_model = bindings[0].model_name

    candidate_models = [
        b.model_name for b in bindings if b.model_name and b.task_type != "EMBEDDING"
    ]

    return await release_engine_vram(
        base_url=provider.base_url,
        model_name=target_model,
        candidate_models=candidate_models,
        api_key=provider.api_key,
        provider_type=provider.provider_type,
        engine_type=getattr(provider, "engine_type", None),
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
    engine = detect_provider_engine(
        clean_url,
        provider.provider_type,
        getattr(provider, "engine_type", None),
    )

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
                # Check /api/v1/models (native LM Studio 0.4.0+)
                try:
                    resp_v1 = await client.get(
                        f"{root_url}/api/v1/models", headers=headers
                    )
                    if resp_v1.status_code == 200:
                        data = resp_v1.json()
                        loaded_models = []
                        for m in data.get("models", []):
                            for inst in m.get("loaded_instances", []):
                                loaded_models.append(inst.get("id") or m.get("key"))
                        is_loaded = len(loaded_models) > 0
                        return {
                            "provider_id": provider_id,
                            "provider_name": provider.name,
                            "engine": "lmstudio",
                            "status": "ACTIVE" if is_loaded else "SLEEPING",
                            "is_loaded": is_loaded,
                            "active_model": loaded_models[0] if is_loaded else None,
                            "vram_allocated_mb": 4096 if is_loaded else 0,
                        }
                except Exception:
                    pass

                # Fallback: check /api/v0/models where state == 'loaded'
                try:
                    resp_v0 = await client.get(
                        f"{root_url}/api/v0/models", headers=headers
                    )
                    if resp_v0.status_code == 200:
                        data_v0 = resp_v0.json()
                        loaded_models = [
                            d.get("id")
                            for d in data_v0.get("data", [])
                            if d.get("state") == "loaded"
                        ]
                        is_loaded = len(loaded_models) > 0
                        return {
                            "provider_id": provider_id,
                            "provider_name": provider.name,
                            "engine": "lmstudio",
                            "status": "ACTIVE" if is_loaded else "SLEEPING",
                            "is_loaded": is_loaded,
                            "active_model": loaded_models[0] if is_loaded else None,
                            "vram_allocated_mb": 4096 if is_loaded else 0,
                        }
                except Exception:
                    pass

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
                        "active_model": models[0].get("name") if loaded else None,
                        "vram_allocated_mb": vram,
                    }

            elif engine == "vllm":
                # Probe /is_sleeping endpoint in vLLM
                try:
                    sleep_resp = await client.get(
                        f"{root_url}/is_sleeping", headers=headers, timeout=2.0
                    )
                    if sleep_resp.status_code == 200:
                        is_sleeping = (
                            sleep_resp.json()
                            if isinstance(sleep_resp.json(), bool)
                            else sleep_resp.json().get("is_sleeping", False)
                        )
                        return {
                            "provider_id": provider_id,
                            "provider_name": provider.name,
                            "engine": "vllm",
                            "status": "SLEEPING" if is_sleeping else "ACTIVE",
                            "is_loaded": not is_sleeping,
                            "active_model": None,
                            "vram_allocated_mb": 0 if is_sleeping else 8192,
                        }
                except Exception:
                    pass

                # Fallback: check /v1/models
                models_resp = await client.get(
                    f"{root_url}/v1/models", headers=headers, timeout=2.0
                )
                if models_resp.status_code == 200:
                    m_data = models_resp.json().get("data", [])
                    return {
                        "provider_id": provider_id,
                        "provider_name": provider.name,
                        "engine": "vllm",
                        "status": "ACTIVE",
                        "is_loaded": True,
                        "active_model": m_data[0].get("id") if m_data else None,
                        "vram_allocated_mb": 8192,
                    }

            elif engine == "sglang":
                # Probe /get_model_info or /v1/models in SGLang
                try:
                    info_resp = await client.get(
                        f"{root_url}/get_model_info", headers=headers, timeout=2.0
                    )
                    if info_resp.status_code == 200:
                        info_data = info_resp.json()
                        model_id = (
                            info_data.get("model_path")
                            or info_data.get("model")
                            or None
                        )
                        return {
                            "provider_id": provider_id,
                            "provider_name": provider.name,
                            "engine": "sglang",
                            "status": "ACTIVE",
                            "is_loaded": True,
                            "active_model": model_id,
                            "vram_allocated_mb": 8192,
                        }
                except Exception:
                    pass

                models_resp = await client.get(
                    f"{root_url}/v1/models", headers=headers, timeout=2.0
                )
                if models_resp.status_code == 200:
                    m_data = models_resp.json().get("data", [])
                    return {
                        "provider_id": provider_id,
                        "provider_name": provider.name,
                        "engine": "sglang",
                        "status": "ACTIVE",
                        "is_loaded": True,
                        "active_model": m_data[0].get("id") if m_data else None,
                        "vram_allocated_mb": 8192,
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
