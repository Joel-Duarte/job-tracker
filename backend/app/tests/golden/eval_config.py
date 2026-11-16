"""Shared configuration and hardware-concurrency resolver for local LLM golden evaluations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_API_BASE = os.getenv(
    "LLM_EVAL_BASE_URL", "http://127.0.0.1:10555/api/v1"
).rstrip("/")


def api_json(
    path: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    base_url: str = DEFAULT_API_BASE,
    timeout: float = 180.0,
) -> Any:
    """Perform a synchronous JSON HTTP call against the running backend API."""
    url = f"{base_url}{path if path.startswith('/') else '/' + path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}


def fetch_active_provider(base_url: str = DEFAULT_API_BASE) -> dict[str, Any] | None:
    """Return the active AI provider record from the running backend, or None if unreachable."""
    try:
        providers = api_json("/ai/providers", base_url=base_url, timeout=10.0)
    except Exception:
        return None
    if not isinstance(providers, list) or not providers:
        return None
    active = [p for p in providers if isinstance(p, dict) and p.get("is_active")]
    return active[0] if active else providers[0]


def run_provider_benchmark(
    provider_id: int,
    *,
    base_url: str = DEFAULT_API_BASE,
    mode: str = "quick",
) -> dict[str, Any]:
    """Invoke the existing multi-factor hardware capacity benchmark endpoint on the provider."""
    res = api_json(
        f"/ai/providers/{provider_id}/benchmark",
        method="POST",
        body={"mode": mode},
        base_url=base_url,
        timeout=300.0,
    )
    assert isinstance(res, dict)
    return res


def resolve_eval_concurrency(
    *,
    explicit_concurrency: int | None = None,
    base_url: str = DEFAULT_API_BASE,
    run_benchmark: bool = False,
) -> dict[str, Any]:
    """
    Resolve golden-eval concurrency in order:
      1. Explicit CLI flag (`--concurrency`)
      2. Env var `LLM_EVAL_CONCURRENCY` (also reads local dev preference)
      3. Optional `--benchmark` (`POST /ai/providers/{id}/benchmark`) calibration
      4. Active provider's persisted `max_concurrency` (currently 3 on Local LM Studio)
      5. Safe fallback of 1
    """
    provider = fetch_active_provider(base_url=base_url)
    benchmark_result: dict[str, Any] | None = None

    if run_benchmark and provider and provider.get("id") is not None:
        benchmark_result = run_provider_benchmark(
            int(provider["id"]), base_url=base_url
        )

    if explicit_concurrency is not None and explicit_concurrency >= 1:
        return {
            "concurrency": int(explicit_concurrency),
            "source": "cli",
            "provider": provider,
            "benchmark": benchmark_result,
        }

    env_val = str(os.getenv("LLM_EVAL_CONCURRENCY") or "").strip()
    if env_val.isdigit() and int(env_val) >= 1:
        return {
            "concurrency": int(env_val),
            "source": "env:LLM_EVAL_CONCURRENCY",
            "provider": provider,
            "benchmark": benchmark_result,
        }

    if (
        benchmark_result
        and int(benchmark_result.get("recommended_max_concurrency") or 0) >= 1
    ):
        return {
            "concurrency": int(benchmark_result["recommended_max_concurrency"]),
            "source": "benchmark_service",
            "provider": provider,
            "benchmark": benchmark_result,
        }

    if provider and int(provider.get("max_concurrency") or 0) >= 1:
        return {
            "concurrency": int(provider["max_concurrency"]),
            "source": f"provider:{provider.get('name', 'active')}",
            "provider": provider,
            "benchmark": benchmark_result,
        }

    return {
        "concurrency": 1,
        "source": "fallback",
        "provider": provider,
        "benchmark": benchmark_result,
    }
