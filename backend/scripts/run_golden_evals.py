"""Unified concurrency-aware local LLM golden evaluation CLI runner across all pipelines.

Delegates evaluation logic to `app.services.prompt_eval_service` while resolving concurrency
via `--concurrency` -> `LLM_EVAL_CONCURRENCY` -> `--benchmark` -> active provider `max_concurrency`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.prompt_eval_service import (
    ALL_PIPELINES,
    evaluate_pipeline_scenario,
)
from app.tests.golden.eval_config import DEFAULT_API_BASE, resolve_eval_concurrency
from app.tests.golden.pipeline_golden import GOLDEN_PIPELINE_SCENARIOS
from app.tests.golden.system_design_golden import GOLDEN_SYSTEM_DESIGN_SCENARIOS
from scripts.eval_system_design_llm import run_single_scenario as run_sd_scenario


def resolve_async_db_url() -> str:
    """Resolve host/local asyncpg URL matching running Docker Postgres by default."""
    raw = os.getenv("DATABASE_URL") or os.getenv("GOLDEN_ASYNC_DB_URL")
    if raw:
        if raw.startswith("postgresql://"):
            return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
        return raw
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "10556")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "postgres")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"


async def run_golden_suite(
    *,
    pipelines: list[str] | None = None,
    explicit_concurrency: int | None = None,
    run_benchmark: bool = False,
    api_base_url: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    """Execute selected golden suites concurrently bounded by resolved LLM concurrency."""
    target_pipelines = set(pipelines or ALL_PIPELINES)
    if "all" in target_pipelines:
        target_pipelines = set(ALL_PIPELINES)

    resolved = resolve_eval_concurrency(
        explicit_concurrency=explicit_concurrency,
        base_url=api_base_url,
        run_benchmark=run_benchmark,
    )
    concurrency = max(1, int(resolved["concurrency"]))
    sem = asyncio.Semaphore(concurrency)

    sd_scenarios = (
        list(GOLDEN_SYSTEM_DESIGN_SCENARIOS)
        if "system_design" in target_pipelines
        else []
    )
    pipe_scenarios = [
        sc for sc in GOLDEN_PIPELINE_SCENARIOS if sc["pipeline"] in target_pipelines
    ]

    async def _run_sd(sc: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            t0 = time.time()
            res = await asyncio.to_thread(
                run_sd_scenario, sc, f"{api_base_url}/system-design"
            )
            return {
                "id": res["id"],
                "pipeline": "system_design",
                "passed": res["passed"],
                "elapsed_secs": round(time.time() - t0, 1),
                "details": {
                    "score": res["score"],
                    "rating": res["rating"],
                    "rev_secs": res["rev_secs"],
                    "eval_secs": res["eval_secs"],
                },
                "failures": res["failures"],
            }

    engine = create_async_engine(
        resolve_async_db_url(), pool_size=max(5, concurrency + 2)
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _run_pipe(sc: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            async with session_factory() as db:
                try:
                    return await evaluate_pipeline_scenario(sc, db)
                except Exception as exc:
                    return {
                        "id": sc["id"],
                        "pipeline": sc["pipeline"],
                        "passed": False,
                        "elapsed_secs": 0.0,
                        "details": {},
                        "failures": [f"Exception: {exc}"],
                    }

    wall_t0 = time.time()
    try:
        tasks = [_run_sd(sc) for sc in sd_scenarios] + [
            _run_pipe(sc) for sc in pipe_scenarios
        ]
        results = await asyncio.gather(*tasks)
    finally:
        await engine.dispose()

    wall_secs = round(time.time() - wall_t0, 1)
    passed_count = sum(1 for r in results if r["passed"])
    return {
        "concurrency": concurrency,
        "concurrency_source": resolved["source"],
        "benchmark": resolved.get("benchmark"),
        "pipelines": sorted(target_pipelines),
        "wall_secs": wall_secs,
        "passed": passed_count,
        "total": len(results),
        "all_passed": passed_count == len(results),
        "results": list(results),
    }


def _main() -> int:
    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(
        description="Run concurrency-aware local LLM golden evals."
    )
    parser.add_argument(
        "--pipeline",
        action="append",
        help="Pipeline(s) to evaluate: all or any name from ALL_PIPELINES",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Explicit concurrency override (defaults to LLM_EVAL_CONCURRENCY or active provider max_concurrency).",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run hardware capacity benchmark against active provider first.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Optional output path for JSON summary report.",
    )
    args = parser.parse_args()

    summary = asyncio.run(
        run_golden_suite(
            pipelines=args.pipeline or ["all"],
            explicit_concurrency=args.concurrency,
            run_benchmark=args.benchmark,
        )
    )

    print(
        f"Resolved concurrency={summary['concurrency']} (source={summary['concurrency_source']})"
    )
    if summary.get("benchmark"):
        bm = summary["benchmark"]
        print(
            f"Benchmark: recommended_max_concurrency={bm.get('recommended_max_concurrency')} "
            f"peak_tps={bm.get('peak_aggregate_tps')} quality_passed={bm.get('quality_gate_passed')}"
        )

    for res in summary["results"]:
        tag = "PASS" if res["passed"] else "FAIL"
        print(
            f"[{tag}] {res['pipeline']:26s} | {res['id']:40s} | {res['elapsed_secs']:5.1f}s | {res['details']}"
        )
        for err in res.get("failures") or []:
            print(f"       -> {err}")

    print(
        f"\nGolden Eval Summary: {summary['passed']}/{summary['total']} passed in {summary['wall_secs']}s "
        f"(concurrency={summary['concurrency']})."
    )
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())
