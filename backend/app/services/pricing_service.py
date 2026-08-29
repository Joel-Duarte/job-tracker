import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default benchmark pricing rates per 1,000,000 tokens (USD)
DEFAULT_MODEL_PRICING: dict[str, dict[str, Any]] = {
    "local_baseline": {
        "key": "local_baseline",
        "display_name": "Local LLM Benchmark (Savings Baseline)",
        "provider": "local",
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "description": "Standard baseline rate (GPT-4o-mini equivalent) to estimate cloud savings for local models.",
    },
    "gpt-4o": {
        "key": "gpt-4o",
        "display_name": "OpenAI GPT-4o",
        "provider": "openai",
        "input_cost_per_million": 2.50,
        "output_cost_per_million": 10.00,
        "description": "Flagship multimodal model for complex reasoning and tasks.",
    },
    "gpt-4o-mini": {
        "key": "gpt-4o-mini",
        "display_name": "OpenAI GPT-4o Mini",
        "provider": "openai",
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "description": "Fast, cost-efficient model for intake and structured extractions.",
    },
    "gpt-4-turbo": {
        "key": "gpt-4-turbo",
        "display_name": "OpenAI GPT-4 Turbo",
        "provider": "openai",
        "input_cost_per_million": 10.00,
        "output_cost_per_million": 30.00,
        "description": "High-intelligence GPT-4 turbo generation.",
    },
    "o1": {
        "key": "o1",
        "display_name": "OpenAI o1",
        "provider": "openai",
        "input_cost_per_million": 15.00,
        "output_cost_per_million": 60.00,
        "description": "Advanced reasoning model with chain-of-thought processing.",
    },
    "o3-mini": {
        "key": "o3-mini",
        "display_name": "OpenAI o3-mini",
        "provider": "openai",
        "input_cost_per_million": 1.10,
        "output_cost_per_million": 4.40,
        "description": "STEM and reasoning-optimized compact model.",
    },
    "claude-3-5-sonnet": {
        "key": "claude-3-5-sonnet",
        "display_name": "Anthropic Claude 3.5 Sonnet",
        "provider": "anthropic",
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
        "description": "State-of-the-art coding, analysis, and nuances.",
    },
    "claude-3-5-haiku": {
        "key": "claude-3-5-haiku",
        "display_name": "Anthropic Claude 3.5 Haiku",
        "provider": "anthropic",
        "input_cost_per_million": 0.80,
        "output_cost_per_million": 4.00,
        "description": "Fast and responsive lightweight model.",
    },
    "claude-3-opus": {
        "key": "claude-3-opus",
        "display_name": "Anthropic Claude 3 Opus",
        "provider": "anthropic",
        "input_cost_per_million": 15.00,
        "output_cost_per_million": 75.00,
        "description": "High-complexity deep analytical model.",
    },
    "gemini-2.0-flash": {
        "key": "gemini-2.0-flash",
        "display_name": "Google Gemini 2.0 Flash",
        "provider": "gemini",
        "input_cost_per_million": 0.10,
        "output_cost_per_million": 0.40,
        "description": "Next-gen multimodal workhorse with sub-second speeds.",
    },
    "gemini-1.5-pro": {
        "key": "gemini-1.5-pro",
        "display_name": "Google Gemini 1.5 Pro",
        "provider": "gemini",
        "input_cost_per_million": 1.25,
        "output_cost_per_million": 5.00,
        "description": "High-context window multimodal reasoning model.",
    },
    "gemini-1.5-flash": {
        "key": "gemini-1.5-flash",
        "display_name": "Google Gemini 1.5 Flash",
        "provider": "gemini",
        "input_cost_per_million": 0.075,
        "output_cost_per_million": 0.30,
        "description": "Lightweight, highly economical Gemini model.",
    },
    "deepseek-chat": {
        "key": "deepseek-chat",
        "display_name": "DeepSeek V3 (Chat)",
        "provider": "deepseek",
        "input_cost_per_million": 0.14,
        "output_cost_per_million": 0.28,
        "description": "High-efficiency general and coding model.",
    },
    "deepseek-reasoner": {
        "key": "deepseek-reasoner",
        "display_name": "DeepSeek R1 (Reasoner)",
        "provider": "deepseek",
        "input_cost_per_million": 0.55,
        "output_cost_per_million": 2.19,
        "description": "Open-weights reasoning model with mathematical depth.",
    },
}

_custom_pricing_cache: dict[str, dict[str, Any]] = {}


def _match_pricing_key(model_name: str | None) -> str:
    """Matches a model name string (including path / provider prefixes) to a pricing key."""
    if not model_name:
        return "local_baseline"
    norm = model_name.lower().strip()

    if norm in DEFAULT_MODEL_PRICING:
        return norm

    if "o3-mini" in norm:
        return "o3-mini"
    if "o1" in norm:
        return "o1"
    if "gpt-4o-mini" in norm:
        return "gpt-4o-mini"
    if "gpt-4o" in norm:
        return "gpt-4o"
    if "gpt-4" in norm:
        return "gpt-4-turbo"
    if "claude-3-5-sonnet" in norm or "claude-3.5-sonnet" in norm:
        return "claude-3-5-sonnet"
    if "claude-3-5-haiku" in norm or "claude-3.5-haiku" in norm:
        return "claude-3-5-haiku"
    if "claude-3-opus" in norm:
        return "claude-3-opus"
    if "gemini-2.0-flash" in norm or "gemini-2-flash" in norm:
        return "gemini-2.0-flash"
    if "gemini-1.5-pro" in norm:
        return "gemini-1.5-pro"
    if "gemini-1.5-flash" in norm:
        return "gemini-1.5-flash"
    if "deepseek-reasoner" in norm or "r1" in norm:
        return "deepseek-reasoner"
    if "deepseek" in norm:
        return "deepseek-chat"

    return "local_baseline"


def get_all_pricing_rates() -> list[dict[str, Any]]:
    """Returns all current pricing rates as a list with custom overrides applied."""
    rates = []
    for key, val in DEFAULT_MODEL_PRICING.items():
        item = dict(val)
        if key in _custom_pricing_cache:
            item.update(_custom_pricing_cache[key])
        rates.append(item)
    return rates


def update_pricing_rate_override(
    key: str, input_cost: float, output_cost: float
) -> dict[str, Any]:
    """Updates custom pricing rate override in memory."""
    if key not in DEFAULT_MODEL_PRICING:
        DEFAULT_MODEL_PRICING[key] = {
            "key": key,
            "display_name": key,
            "provider": "custom",
            "input_cost_per_million": input_cost,
            "output_cost_per_million": output_cost,
            "description": "User-defined custom model rate",
        }
    _custom_pricing_cache[key] = {
        "input_cost_per_million": float(input_cost),
        "output_cost_per_million": float(output_cost),
    }
    updated = dict(DEFAULT_MODEL_PRICING[key])
    updated.update(_custom_pricing_cache[key])
    return updated


def reset_pricing_rates() -> list[dict[str, Any]]:
    """Resets custom pricing overrides to standard defaults."""
    _custom_pricing_cache.clear()
    return [dict(v) for v in DEFAULT_MODEL_PRICING.values()]


COMPARATIVE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "provider_name": "Local LLM (Ollama / LM Studio)",
        "model_name": "Local On-Device Models",
        "provider_type": "local",
        "input_cost_per_million": 0.0,
        "output_cost_per_million": 0.0,
        "is_local": True,
    },
    {
        "provider_name": "Google Gemini",
        "model_name": "Gemini 2.0 Flash",
        "provider_type": "google_genai",
        "input_cost_per_million": 0.10,
        "output_cost_per_million": 0.40,
        "is_local": False,
    },
    {
        "provider_name": "DeepSeek",
        "model_name": "DeepSeek V3",
        "provider_type": "deepseek",
        "input_cost_per_million": 0.14,
        "output_cost_per_million": 0.28,
        "is_local": False,
    },
    {
        "provider_name": "OpenAI",
        "model_name": "GPT-4o Mini",
        "provider_type": "openai",
        "input_cost_per_million": 0.15,
        "output_cost_per_million": 0.60,
        "is_local": False,
    },
    {
        "provider_name": "Anthropic",
        "model_name": "Claude 3.5 Haiku",
        "provider_type": "anthropic",
        "input_cost_per_million": 0.80,
        "output_cost_per_million": 4.00,
        "is_local": False,
    },
    {
        "provider_name": "OpenAI",
        "model_name": "GPT-4o",
        "provider_type": "openai",
        "input_cost_per_million": 2.50,
        "output_cost_per_million": 10.00,
        "is_local": False,
    },
    {
        "provider_name": "Anthropic",
        "model_name": "Claude 3.5 Sonnet",
        "provider_type": "anthropic",
        "input_cost_per_million": 3.00,
        "output_cost_per_million": 15.00,
        "is_local": False,
    },
]


def calculate_comparative_provider_costs(
    monthly_input_tokens: int = 0,
    monthly_output_tokens: int = 0,
    current_spend_usd: float = 0.0,
    is_current_local: bool = True,
) -> list[dict[str, Any]]:
    """Calculates simulated monthly cost across benchmark providers based on monthly token usage,
    computing the dollar diff and percentage difference relative to current spend.
    """
    results = []
    in_tok = (
        monthly_input_tokens
        if (monthly_input_tokens > 0 or monthly_output_tokens > 0)
        else 100_000
    )
    out_tok = (
        monthly_output_tokens
        if (monthly_input_tokens > 0 or monthly_output_tokens > 0)
        else 40_000
    )

    model_key_map = {
        "Gemini 2.0 Flash": "gemini-2.0-flash",
        "DeepSeek V3": "deepseek-chat",
        "GPT-4o Mini": "gpt-4o-mini",
        "Claude 3.5 Haiku": "claude-3-5-haiku",
        "GPT-4o": "gpt-4o",
        "Claude 3.5 Sonnet": "claude-3-5-sonnet",
        "Local On-Device Models": "local_baseline",
    }

    for bench in COMPARATIVE_BENCHMARKS:
        m_key = model_key_map.get(bench["model_name"])
        in_cost_val = bench["input_cost_per_million"]
        out_cost_val = bench["output_cost_per_million"]

        if m_key and m_key in _custom_pricing_cache and not bench["is_local"]:
            in_cost_val = _custom_pricing_cache[m_key].get(
                "input_cost_per_million", in_cost_val
            )
            out_cost_val = _custom_pricing_cache[m_key].get(
                "output_cost_per_million", out_cost_val
            )

        in_rate = in_cost_val / 1_000_000.0
        out_rate = out_cost_val / 1_000_000.0
        simulated_cost = round((in_tok * in_rate) + (out_tok * out_rate), 4)
        diff_usd = round(simulated_cost - current_spend_usd, 4)

        if simulated_cost < current_spend_usd - 0.0001:
            status = "cheaper"
            diff_pct = (
                round(
                    ((simulated_cost - current_spend_usd) / current_spend_usd) * 100.0,
                    1,
                )
                if current_spend_usd > 0
                else 0.0
            )
        elif simulated_cost > current_spend_usd + 0.0001:
            status = "more_expensive"
            diff_pct = (
                round(
                    ((simulated_cost - current_spend_usd) / current_spend_usd) * 100.0,
                    1,
                )
                if current_spend_usd > 0
                else 100.0
            )
        else:
            status = "identical"
            diff_pct = 0.0

        results.append(
            {
                "provider_name": bench["provider_name"],
                "model_name": bench["model_name"],
                "provider_type": bench["provider_type"],
                "input_cost_per_million": in_cost_val,
                "output_cost_per_million": out_cost_val,
                "simulated_cost_usd": simulated_cost,
                "diff_usd": diff_usd,
                "diff_percentage": diff_pct,
                "status": status,
                "is_local": bench["is_local"],
            }
        )
    return results


def calculate_cost_and_savings(
    model_name: str | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    is_local: bool = False,
    custom_input_cost_per_million: float | None = None,
    custom_output_cost_per_million: float | None = None,
) -> tuple[float, float]:
    """Calculates (estimated_actual_cost, estimated_cloud_savings) for a given LLM execution."""
    baseline = dict(DEFAULT_MODEL_PRICING["local_baseline"])
    if "local_baseline" in _custom_pricing_cache:
        baseline.update(_custom_pricing_cache["local_baseline"])

    baseline_in_rate = baseline.get("input_cost_per_million", 0.15) / 1_000_000.0
    baseline_out_rate = baseline.get("output_cost_per_million", 0.60) / 1_000_000.0

    if is_local:
        savings = (input_tokens * baseline_in_rate) + (
            output_tokens * baseline_out_rate
        )
        return (0.0, round(savings, 6))

    if (
        custom_input_cost_per_million is not None
        and custom_output_cost_per_million is not None
        and (custom_input_cost_per_million > 0 or custom_output_cost_per_million > 0)
    ):
        in_rate = custom_input_cost_per_million / 1_000_000.0
        out_rate = custom_output_cost_per_million / 1_000_000.0
        actual_cost = (input_tokens * in_rate) + (output_tokens * out_rate)
        return (round(actual_cost, 6), 0.0)

    matched_key = _match_pricing_key(model_name)
    rate_info = dict(DEFAULT_MODEL_PRICING.get(matched_key, baseline))
    if matched_key in _custom_pricing_cache:
        rate_info.update(_custom_pricing_cache[matched_key])

    in_rate = rate_info.get("input_cost_per_million", 0.15) / 1_000_000.0
    out_rate = rate_info.get("output_cost_per_million", 0.60) / 1_000_000.0

    actual_cost = (input_tokens * in_rate) + (output_tokens * out_rate)
    return (round(actual_cost, 6), 0.0)


def extract_usage_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts standardized token counts, model info, duration, and local status from a trace payload.
    """
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    model_name = payload.get("model_name") or payload.get("model") or ""
    is_local = payload.get("is_local", False)

    # Direct top-level fields
    if "prompt_tokens" in payload:
        prompt_tokens = int(payload["prompt_tokens"] or 0)
    if "completion_tokens" in payload:
        completion_tokens = int(payload["completion_tokens"] or 0)
    if "total_tokens" in payload:
        total_tokens = int(payload["total_tokens"] or 0)

    # LangChain usage metadata in outputs
    outputs = payload.get("outputs")
    if isinstance(outputs, dict):
        generations = outputs.get("generations")
        if isinstance(generations, list) and len(generations) > 0:
            gen_list = (
                generations[0] if isinstance(generations[0], list) else generations
            )
            for gen in gen_list:
                if isinstance(gen, dict):
                    msg = gen.get("message") or {}
                    usage_meta = msg.get("usage_metadata") or {}
                    if usage_meta:
                        prompt_tokens = max(
                            prompt_tokens, int(usage_meta.get("input_tokens", 0))
                        )
                        completion_tokens = max(
                            completion_tokens, int(usage_meta.get("output_tokens", 0))
                        )
                        total_tokens = max(
                            total_tokens, int(usage_meta.get("total_tokens", 0))
                        )

                    resp_meta = msg.get("response_metadata") or {}
                    token_usage = (
                        resp_meta.get("token_usage") or resp_meta.get("usage") or {}
                    )
                    if token_usage:
                        prompt_tokens = max(
                            prompt_tokens,
                            int(
                                token_usage.get(
                                    "prompt_tokens", token_usage.get("input_tokens", 0)
                                )
                            ),
                        )
                        completion_tokens = max(
                            completion_tokens,
                            int(
                                token_usage.get(
                                    "completion_tokens",
                                    token_usage.get("output_tokens", 0),
                                )
                            ),
                        )
                        total_tokens = max(
                            total_tokens, int(token_usage.get("total_tokens", 0))
                        )

                    if not model_name and (
                        resp_meta.get("model_name") or resp_meta.get("model")
                    ):
                        model_name = resp_meta.get("model_name") or resp_meta.get(
                            "model"
                        )

        llm_output = outputs.get("llm_output")
        if isinstance(llm_output, dict):
            token_usage = llm_output.get("token_usage") or {}
            if token_usage:
                prompt_tokens = max(
                    prompt_tokens, int(token_usage.get("prompt_tokens", 0))
                )
                completion_tokens = max(
                    completion_tokens, int(token_usage.get("completion_tokens", 0))
                )
                total_tokens = max(
                    total_tokens, int(token_usage.get("total_tokens", 0))
                )
            if not model_name and llm_output.get("model_name"):
                model_name = llm_output.get("model_name")

    extra = payload.get("extra") or {}
    inv_params = extra.get("invocation_params") or {}
    if not model_name:
        model_name = inv_params.get("model") or inv_params.get("model_name") or ""

    if not is_local:
        provider_name = (
            payload.get("provider") or payload.get("provider_type") or ""
        ).lower()
        base_url = (payload.get("base_url") or inv_params.get("base_url") or "").lower()
        if (
            "localhost" in base_url
            or "127.0.0.1" in base_url
            or "192.168." in base_url
            or ":1234" in base_url
            or ":11434" in base_url
            or provider_name in ("local", "ollama", "lmstudio", "lm_studio")
        ):
            is_local = True

    if total_tokens == 0 and (prompt_tokens > 0 or completion_tokens > 0):
        total_tokens = prompt_tokens + completion_tokens

    if total_tokens == 0:
        raw_text_len = 0
        inputs = payload.get("inputs")
        if isinstance(inputs, dict):
            raw_text_len += sum(len(str(v)) for v in inputs.values())
        if isinstance(outputs, dict):
            raw_text_len += sum(len(str(v)) for v in outputs.values())
        if raw_text_len > 0:
            total_tokens = max(1, int(raw_text_len / 4))
            prompt_tokens = int(total_tokens * 0.6)
            completion_tokens = max(1, total_tokens - prompt_tokens)

    cost, savings = calculate_cost_and_savings(
        model_name=model_name,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        is_local=is_local,
    )

    duration_seconds = 0.0
    if "duration_ms" in payload and payload["duration_ms"]:
        duration_seconds = round(float(payload["duration_ms"]) / 1000.0, 2)
    elif "duration_seconds" in payload and payload["duration_seconds"]:
        duration_seconds = round(float(payload["duration_seconds"]), 2)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "model_name": model_name,
        "is_local": is_local,
        "estimated_cost": cost,
        "estimated_savings": savings,
        "duration_seconds": duration_seconds,
    }
