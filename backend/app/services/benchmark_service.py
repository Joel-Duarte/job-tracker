"""Capacity and concurrency benchmark testing service for LLM providers."""

import asyncio
import json
import logging
import re
import time
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.benchmark_dataset import BENCHMARK_PLATFORM_JD, BENCHMARK_SENIOR_CV
from app.core.llm_factory import (
    _clean_base_url,
    _resolve_provider,
    init_chat_model,
    strip_reasoning_tags,
)
from app.core.prompts import (
    DEFAULT_PROMPTS,
    build_job_assessment_prompt,
    format_candidate_prefix,
)
from app.models.ai_providers import AIProviderModel, AITaskBindingModel

logger = logging.getLogger(__name__)


def detect_repetitive_loops(text: str, n: int = 3, threshold: float = 0.18) -> bool:
    """
    Computes n-gram repetition frequency. Repetitive sequences exceeding threshold
    indicate memory exhaustion or degenerative model loops.
    """
    if not text:
        return False
    words = re.findall(r"\b\w+\b", text.lower())
    if len(words) < 25:
        return False
    ngrams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]
    if not ngrams:
        return False
    counts = Counter(ngrams)
    most_common_count = counts.most_common(1)[0][1]
    # An n-gram appearing only 1 or 2 times in natural text/JSON is never a degenerative loop
    if most_common_count < 3:
        return False
    repetition_ratio = (most_common_count * n) / len(words)
    return repetition_ratio > threshold


def check_factual_grounding(text: str, required_skills: list[str]) -> bool:
    """
    Verifies presence of grounded technical skills from the candidate profile
    to catch generic filler hallucinations using word boundaries.
    """
    if not text or not required_skills:
        return False
    text_lower = text.lower()
    matches = 0
    for s in required_skills:
        pattern = rf"\b{re.escape(s.lower())}\b"
        if re.search(pattern, text_lower):
            matches += 1
    return matches >= 1


def validate_benchmark_quality(
    output_text: str, required_skills: list[str]
) -> dict[str, Any]:
    """
    Runs multi-factor quality gates:
    1. Degenerative loop detection
    2. Factual grounding check
    3. JSON schema validity
    """
    # 1. Strip reasoning tags (<think>...</think>) before analyzing output
    clean_text = strip_reasoning_tags(output_text)
    is_loop = detect_repetitive_loops(clean_text)
    is_grounded = check_factual_grounding(clean_text, required_skills)

    schema_valid = False
    parsed_json = None
    error_msg = None

    # 2. Robust JSON extraction (markdown fences or regex search)
    raw_json = clean_text.strip()
    if "```json" in raw_json:
        parts = raw_json.split("```json", 1)[1].split("```", 1)
        raw_json = parts[0].strip()
    elif "```" in raw_json:
        parts = raw_json.split("```", 1)[1].split("```", 1)
        raw_json = parts[0].strip()
    else:
        match = re.search(r"\{[\s\S]*\}", raw_json)
        if match:
            raw_json = match.group(0)

    try:
        parsed_dict = json.loads(raw_json)
        if (
            isinstance(parsed_dict, dict)
            and "company" in parsed_dict
            and "fit_score" in parsed_dict
        ):
            schema_valid = True
            parsed_json = parsed_dict
        else:
            schema_valid = False
            error_msg = "Missing required assessment keys ('company', 'fit_score')"
    except Exception as exc:
        schema_valid = False
        error_msg = str(exc)

    passed = (not is_loop) and is_grounded and schema_valid
    return {
        "passed": passed,
        "is_loop": is_loop,
        "is_grounded": is_grounded,
        "schema_valid": schema_valid,
        "parsed_json": parsed_json,
        "error_msg": error_msg,
    }


async def run_capacity_benchmark(
    provider_id: int,
    db: AsyncSession,
    custom_jd: str | None = None,
    is_reasoning: bool | None = None,
    mode: str = "quick",
) -> dict[str, Any]:
    """
    Executes a multi-factor quality-gated capacity benchmark probe against the provider.
    Supports 'quick' (1-pass) and 'calibrated' (3-pass average with warmup) modes.
    Ramps test from N=1 baseline up to N=5 parallel streams, measuring TTFT, throughput,
    loop detection, and schema validity. Returns optimal recommended concurrency.
    """
    start_time = time.time()
    num_passes = 3 if mode == "calibrated" else 1

    prov_stmt = select(AIProviderModel).where(AIProviderModel.id == provider_id)
    prov_res = await db.execute(prov_stmt)
    provider = prov_res.scalar_one_or_none()
    if not provider:
        raise ValueError(f"Provider {provider_id} not found.")

    bind_stmt = select(AITaskBindingModel).where(
        AITaskBindingModel.provider_id == provider_id,
        AITaskBindingModel.is_active.is_(True),
    )
    bindings = (await db.execute(bind_stmt)).scalars().all()
    assessment_binding = next(
        (b for b in bindings if b.task_type in ("JOB_ASSESSMENT", "ASSESSMENT")), None
    )
    global_binding = next(
        (b for b in bindings if b.task_type == "GLOBAL_DEFAULT"), None
    )
    chosen_binding = (
        assessment_binding or global_binding or (bindings[0] if bindings else None)
    )
    target_model_name = chosen_binding.model_name if chosen_binding else "default"

    # Auto-detect reasoning if not explicitly specified
    if is_reasoning is None:
        is_reasoning = False
        if chosen_binding:
            extra = dict(chosen_binding.extra_kwargs or {})
            re_effort = getattr(chosen_binding, "reasoning_effort", None) or extra.get(
                "reasoning_effort"
            )
            if re_effort and str(re_effort).lower() not in ("none", "null", "false"):
                is_reasoning = True
        model_lower = target_model_name.lower()
        if any(
            kw in model_lower
            for kw in ("r1", "thinking", "deepseek-r1", "qwq", "reasoning")
        ):
            is_reasoning = True

    # Prepare prefix-stabilized benchmark prompt with explicit structured JSON schema
    jd_to_use = custom_jd or BENCHMARK_PLATFORM_JD
    candidate_prefix = format_candidate_prefix(BENCHMARK_SENIOR_CV)
    sys_template = DEFAULT_PROMPTS.get("assessment", "Evaluate candidate fit.")
    base_prompt = build_job_assessment_prompt(
        system_template=sys_template,
        candidate_prefix=candidate_prefix,
        job_description=jd_to_use,
        programmatic_baseline=85,
    )
    json_instruction = (
        "\n\n--------------------------------------------------\n"
        "BENCHMARK STRUCTURED OUTPUT REQUIREMENT (STRICT JSON ONLY)\n"
        "--------------------------------------------------\n"
        "Respond strictly with a valid JSON object matching the following structure. "
        "Do NOT include conversational commentary, markdown code fences, or text outside the JSON object:\n"
        "{\n"
        '  "company": "CloudScale Infrastructure",\n'
        '  "position": "Staff Distributed Systems & Platform Engineer",\n'
        '  "fit_score": 85,\n'
        '  "match_summary": "Candidate profile demonstrates high architectural alignment with distributed systems requirements.",\n'
        '  "matching_skills": ["Python", "FastAPI", "Go", "PostgreSQL", "Kafka", "Docker", "Kubernetes", "AWS"],\n'
        '  "missing_skills": ["Rust"]\n'
        "}\n"
    )
    full_prompt = base_prompt + json_instruction
    grounding_skills = BENCHMARK_SENIOR_CV.get("skills", [])

    # Instantiate chat model targeting this specific provider directly
    provider_type = _resolve_provider(provider.provider_type)
    base_url = _clean_base_url(provider.base_url)
    api_key = provider.api_key or "dummy-key"

    init_kwargs: dict[str, Any] = {
        "model": target_model_name,
        "model_provider": provider_type,
        "temperature": 0.1,
        "timeout": 180.0,
    }
    if base_url:
        init_kwargs["base_url"] = base_url
    if api_key:
        init_kwargs["api_key"] = api_key

    # For local providers when reasoning is not active, disable thinking overhead
    if base_url and any(
        h in base_url
        for h in ("localhost", "127.0.0.1", "192.168.", "0.0.0.0", "10.", "172.")
    ):
        extra_b = init_kwargs.setdefault("extra_body", {})
        if not is_reasoning:
            extra_b.setdefault("reasoning_effort", "none")
            extra_b.setdefault("chat_template_kwargs", {"thinking": False})

    llm = init_chat_model(**init_kwargs)

    async def _execute_single_stream() -> tuple[float, float, str]:
        t0 = time.time()
        ttft = 0.0
        output_chunks = []
        try:
            async for chunk in llm.astream(full_prompt):
                if ttft == 0.0:
                    ttft = time.time() - t0
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if isinstance(content, str):
                    output_chunks.append(content)
                elif isinstance(content, list):
                    for part in content:
                        output_chunks.append(
                            part.get("text", "")
                            if isinstance(part, dict)
                            else str(part)
                        )
        except Exception:
            # Fallback to ainvoke if astream is not supported
            res = await llm.ainvoke(full_prompt)
            ttft = time.time() - t0
            output_chunks.append(res.content if hasattr(res, "content") else str(res))

        total_time = max(0.001, time.time() - t0)
        full_text = "".join(output_chunks)
        approx_tokens = max(1, len(full_text) // 4)
        tps = approx_tokens / total_time
        return tps, ttft, full_text

    # In calibrated mode: run a quick warmup probe to prime KV cache and CUDA kernels
    if mode == "calibrated":
        try:
            await _execute_single_stream()
        except Exception:
            pass

    async def _evaluate_tier_passes(
        n_slots: int,
    ) -> tuple[float, float, list[str], bool]:
        pass_speeds: list[float] = []
        pass_ttfts: list[float] = []
        all_outputs: list[str] = []

        for _ in range(num_passes):
            stream_tasks = [_execute_single_stream() for _ in range(n_slots)]
            results = await asyncio.gather(*stream_tasks, return_exceptions=True)

            valid_outputs = []
            speeds = []
            ttfts = []
            for item in results:
                if isinstance(item, tuple) and len(item) == 3:
                    s_tps, s_ttft, s_out = item
                    speeds.append(s_tps)
                    ttfts.append(s_ttft)
                    valid_outputs.append(s_out)

            if len(valid_outputs) < n_slots:
                return (
                    sum(speeds) if speeds else 0.0,
                    sum(ttfts) / max(1, len(ttfts)) if ttfts else 0.0,
                    valid_outputs,
                    False,
                )

            pass_speeds.append(sum(speeds))
            pass_ttfts.append(sum(ttfts) / n_slots)
            all_outputs.extend(valid_outputs)

        avg_agg_tps = sum(pass_speeds) / len(pass_speeds)
        avg_ttft = sum(pass_ttfts) / len(pass_ttfts)
        return avg_agg_tps, avg_ttft, all_outputs, True

    # 1. Baseline: Benchmark Single Stream (N=1)
    single_tps, single_ttft, single_outputs, single_ok = await _evaluate_tier_passes(1)
    last_single_out = single_outputs[-1] if single_outputs else ""
    q1 = validate_benchmark_quality(last_single_out, grounding_skills)

    tested_slots = [
        {
            "slots": 1,
            "aggregate_tps": round(single_tps, 1),
            "avg_ttft": round(single_ttft, 2),
            "scaling_gain_pct": 0.0,
            "quality_passed": q1["passed"] and single_ok,
            "status": "BASELINE",
        }
    ]

    recommended_slots = 1
    last_aggregate_tps = single_tps
    peak_tps = single_tps
    tier_2_tps = single_tps
    overall_quality_passed = q1["passed"] and single_ok

    # 2. Adaptive Sequential Ramping: N = 2 up to 5 parallel slots
    # Stop condition: throughput gain < 10% (plateau/diminishing returns),
    # quality gate failure, or severe latency spike.
    if q1["passed"] and single_ok:
        for n_slots in range(2, 6):
            (
                tier_agg_tps,
                avg_ttft,
                valid_outputs,
                conn_ok,
            ) = await _evaluate_tier_passes(n_slots)

            # If any stream failed at network/transport level, halt
            if not conn_ok or len(valid_outputs) < n_slots:
                tested_slots.append(
                    {
                        "slots": n_slots,
                        "aggregate_tps": round(tier_agg_tps, 1),
                        "avg_ttft": round(avg_ttft, 2),
                        "scaling_gain_pct": 0.0,
                        "quality_passed": False,
                        "status": "CONNECTION_EXHAUSTED",
                    }
                )
                break

            if n_slots == 2:
                tier_2_tps = tier_agg_tps

            # Validate quality gate across all parallel stream outputs
            qualities = [
                validate_benchmark_quality(out, grounding_skills)
                for out in valid_outputs
            ]
            tier_quality_passed = all(q["passed"] for q in qualities)

            gain_pct = round(
                ((tier_agg_tps - last_aggregate_tps) / max(0.1, last_aggregate_tps))
                * 100,
                1,
            )

            # Check stopping criteria
            if not tier_quality_passed:
                tested_slots.append(
                    {
                        "slots": n_slots,
                        "aggregate_tps": round(tier_agg_tps, 1),
                        "avg_ttft": round(avg_ttft, 2),
                        "scaling_gain_pct": gain_pct,
                        "quality_passed": False,
                        "status": "QUALITY_DEGRADED",
                    }
                )
                break

            # TTFT latency spike check (more than 2.5x baseline and > 2.5s)
            if avg_ttft > max(2.5, single_ttft * 2.5):
                tested_slots.append(
                    {
                        "slots": n_slots,
                        "aggregate_tps": round(tier_agg_tps, 1),
                        "avg_ttft": round(avg_ttft, 2),
                        "scaling_gain_pct": gain_pct,
                        "quality_passed": True,
                        "status": "LATENCY_SPIKE",
                    }
                )
                break

            # Throughput plateau check (< 10% gain over previous tier)
            if gain_pct < 10.0:
                tested_slots.append(
                    {
                        "slots": n_slots,
                        "aggregate_tps": round(tier_agg_tps, 1),
                        "avg_ttft": round(avg_ttft, 2),
                        "scaling_gain_pct": gain_pct,
                        "quality_passed": True,
                        "status": "DIMINISHING_RETURNS",
                    }
                )
                break

            # Scaling verified! Update recommended slots and continue
            recommended_slots = n_slots
            last_aggregate_tps = tier_agg_tps
            peak_tps = max(peak_tps, tier_agg_tps)
            tested_slots.append(
                {
                    "slots": n_slots,
                    "aggregate_tps": round(tier_agg_tps, 1),
                    "avg_ttft": round(avg_ttft, 2),
                    "scaling_gain_pct": gain_pct,
                    "quality_passed": True,
                    "status": "SCALING_VERIFIED",
                }
            )

    is_parallel_verified = recommended_slots >= 2
    total_exec_seconds = round(time.time() - start_time, 2)

    tier_summaries = [
        f"N={t['slots']}: {t['aggregate_tps']} tok/s ({'+' + str(t['scaling_gain_pct']) + '%' if t['slots'] > 1 else 'baseline'})"
        for t in tested_slots
    ]
    mode_label = (
        "Calibrated (3-pass average)" if mode == "calibrated" else "Quick (1-pass)"
    )
    details = (
        f"[{mode_label}] Ramped {len(tested_slots)} slot tiers: {', '.join(tier_summaries)}. "
        f"Peak throughput: {peak_tps:.1f} tok/s. "
        f"Quality gate: {'PASSED' if overall_quality_passed else 'FAILED'}. "
        f"Parallel execution verified: {'YES' if is_parallel_verified else 'NO'}."
    )

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "model_name": target_model_name,
        "single_stream_tps": round(single_tps, 1),
        "dual_stream_tps": round(tier_2_tps, 1),
        "peak_aggregate_tps": round(peak_tps, 1),
        "tested_slots": tested_slots,
        "is_parallel_verified": is_parallel_verified,
        "quality_gate_passed": overall_quality_passed,
        "recommended_max_concurrency": recommended_slots,
        "details": details,
        "execution_time_seconds": total_exec_seconds,
    }
