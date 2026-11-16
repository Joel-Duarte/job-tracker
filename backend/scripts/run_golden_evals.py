"""Unified concurrency-aware local LLM golden evaluation runner across all pipelines.

Supports:
- `--pipeline all|system_design|jd_extraction|assessment|email_extraction|cover_letter|application_qa`
- `--concurrency N` (defaults to `LLM_EVAL_CONCURRENCY`, then active AI provider `max_concurrency`, e.g. 3)
- `--benchmark` (runs existing `benchmark_service` capacity probe before golden cases)

Usage:
    cd backend
    PYTHONPATH=. uv run python scripts/run_golden_evals.py --pipeline all
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.llm import (
    assess_job_posting,
    extract_email_info,
    extract_job_spec,
    generate_application_answers,
    generate_cover_letter,
)
from app.tests.golden.eval_config import DEFAULT_API_BASE, resolve_eval_concurrency
from app.tests.golden.pipeline_golden import GOLDEN_PIPELINE_SCENARIOS
from app.tests.golden.system_design_golden import GOLDEN_SYSTEM_DESIGN_SCENARIOS
from scripts.eval_system_design_llm import run_single_scenario as run_sd_scenario

ALL_PIPELINES = (
    "system_design",
    "jd_extraction",
    "assessment",
    "email_extraction",
    "cover_letter",
    "application_qa",
)


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


async def evaluate_pipeline_scenario(
    scenario: dict[str, Any], db: AsyncSession
) -> dict[str, Any]:
    """Run one non-SD golden scenario against the real async service & active LLM."""
    t0 = time.time()
    pipeline = scenario["pipeline"]
    failures: list[str] = []
    details: dict[str, Any] = {}

    if pipeline == "jd_extraction":
        res = await extract_job_spec(
            db,
            scenario["raw_webpage_data"],
            title_hint=scenario.get("title_hint"),
            page_title=scenario.get("page_title"),
        )
        details = {
            "job_found": res.job_found,
            "skills_count": len(res.extracted_skills),
            "salary_min": res.salary_min,
            "salary_max": res.salary_max,
        }
        if bool(res.job_found) != bool(scenario["expect_job_found"]):
            failures.append(
                f"Expected job_found={scenario['expect_job_found']}, got {res.job_found}"
            )
        if scenario["expect_job_found"]:
            skills_blob = " ".join(res.extracted_skills).lower()
            req_any = scenario.get("required_skills_any") or []
            if req_any and not any(s.lower() in skills_blob for s in req_any):
                failures.append(
                    f"None of {req_any} found in extracted_skills={res.extracted_skills}"
                )
            exp_min = scenario.get("expected_salary_min")
            exp_max = scenario.get("expected_salary_max")
            if exp_min is not None and res.salary_min != exp_min:
                failures.append(f"Expected salary_min={exp_min}, got {res.salary_min}")
            if exp_max is not None and res.salary_max != exp_max:
                failures.append(f"Expected salary_max={exp_max}, got {res.salary_max}")
            exp_cur = scenario.get("expected_currency")
            if exp_cur and (res.currency or "").upper() != exp_cur.upper():
                failures.append(f"Expected currency={exp_cur}, got {res.currency!r}")
            exp_per = scenario.get("expected_salary_period")
            if exp_per and (res.salary_period or "").upper() != exp_per.upper():
                failures.append(
                    f"Expected salary_period={exp_per}, got {res.salary_period!r}"
                )
            for field_name in scenario.get("must_be_null_if_unstated") or []:
                if getattr(res, field_name, None):
                    failures.append(
                        f"Expected '{field_name}' to stay null when unstated, got {getattr(res, field_name)!r}"
                    )

    elif pipeline == "assessment":
        res = await assess_job_posting(
            db,
            job_description=scenario["job_description"],
            candidate_skills=scenario.get("candidate_skills"),
            candidate_cv=scenario.get("candidate_cv"),
            candidate_spoken_languages=scenario.get("candidate_spoken_languages"),
            candidate_years_of_experience=scenario.get("candidate_years_of_experience"),
            programmatic_baseline=scenario.get("programmatic_baseline"),
            matching_skills=scenario.get("matching_skills"),
            missing_skills=scenario.get("missing_skills"),
        )
        lang_res = res.language_match
        details = {
            "fit_score": res.fit_score,
            "recommendation": res.recommendation,
            "seniority_fit": res.seniority_fit,
            "lang_matched": lang_res.is_matched if lang_res else None,
            "missing_mandatory_langs": lang_res.missing_mandatory if lang_res else [],
            "critical_risks": res.critical_risks,
        }
        if (
            res.fit_score < scenario["min_score"]
            or res.fit_score > scenario["max_score"]
        ):
            failures.append(
                f"fit_score {res.fit_score} out of [{scenario['min_score']}, {scenario['max_score']}]"
            )
        allowed_recs = scenario.get("allowed_recommendations") or []
        if allowed_recs and res.recommendation not in allowed_recs:
            failures.append(
                f"recommendation '{res.recommendation}' not in {allowed_recs}"
            )
        exp_seniority = scenario.get("expected_seniority_fit")
        if exp_seniority and (res.seniority_fit or "").upper() != exp_seniority.upper():
            failures.append(
                f"Expected seniority_fit={exp_seniority}, got {res.seniority_fit!r}"
            )
        exp_lang_match = scenario.get("expect_language_matched")
        if exp_lang_match is not None and lang_res is not None:
            if bool(lang_res.is_matched) != bool(exp_lang_match):
                failures.append(
                    f"Expected language_match.is_matched={exp_lang_match}, got {lang_res.is_matched} (missing={lang_res.missing_mandatory})"
                )
        if "expect_missing_mandatory_langs" in scenario and lang_res is not None:
            if (lang_res.missing_mandatory or []) != scenario[
                "expect_missing_mandatory_langs"
            ]:
                failures.append(
                    f"Expected missing_mandatory={scenario['expect_missing_mandatory_langs']}, got {lang_res.missing_mandatory}"
                )
        req_missing_langs = scenario.get("expect_missing_mandatory_any") or []
        if req_missing_langs and lang_res is not None:
            mm_blob = " ".join(
                (lang_res.missing_mandatory or []) + (res.critical_risks or [])
            ).lower()
            if not any(t.lower() in mm_blob for t in req_missing_langs):
                failures.append(
                    f"Expected any of {req_missing_langs} in missing_mandatory/risks, got {lang_res.missing_mandatory}"
                )
        banned_risks = scenario.get("banned_risk_substrings") or []
        if banned_risks:
            risk_blob = " ".join(
                (res.critical_risks or [])
                + (res.cons or [])
                + ([lang_res.warning] if lang_res and lang_res.warning else [])
                + (lang_res.missing_mandatory if lang_res else [])
            ).lower()
            for b in banned_risks:
                if b.lower() in risk_blob:
                    failures.append(f"Banned false risk leaked: '{b}'")
        gap_terms = scenario.get("expect_gap_terms_any") or []
        if gap_terms:
            gap_blob = " ".join(
                (res.missing_skills or [])
                + (res.critical_risks or [])
                + (res.cons or [])
                + [res.match_summary or ""]
            ).lower()
            if not any(term.lower() in gap_blob for term in gap_terms):
                failures.append(
                    f"None of expected gap terms {gap_terms} surfaced in assessment gaps"
                )
        if scenario.get("ban_pseudo_risks"):
            for r in res.critical_risks or []:
                rl = str(r).strip().lower()
                if rl.startswith("no critical risk") or rl == "none":
                    failures.append(f"Pseudo-risk leaked: {r!r}")

    elif pipeline == "email_extraction":
        res = await extract_email_info(
            db,
            scenario["email_content"],
            sender=scenario.get("sender"),
            subject=scenario.get("subject"),
            date=scenario.get("date"),
        )
        details = {
            "email_type": res.email_type,
            "company": res.company,
            "status": res.status,
            "action_required": res.action_required,
            "due_date": res.due_date,
        }
        if bool(res.action_required) != bool(scenario["expect_action_required"]):
            failures.append(
                f"Expected action_required={scenario['expect_action_required']}, got {res.action_required}"
            )
        exp_company = scenario.get("expect_company")
        if exp_company and exp_company.lower() not in (res.company or "").lower():
            failures.append(f"Expected company '{exp_company}', got {res.company!r}")
        exp_status = scenario.get("expected_status_any") or []
        if exp_status and (res.status or "").upper() not in [
            s.upper() for s in exp_status
        ]:
            failures.append(f"Expected status in {exp_status}, got {res.status!r}")
        for banned_st in scenario.get("banned_status_values") or []:
            if (res.status or "").upper() == banned_st.upper():
                failures.append(
                    f"Thread-isolation leak: got banned status {res.status!r}"
                )
        for fld in scenario.get("expect_non_empty_fields") or []:
            if not getattr(res, fld, None):
                failures.append(f"Expected non-empty '{fld}', got None/empty")
        for fld in scenario.get("expect_null_fields") or []:
            if getattr(res, fld, None) not in (None, ""):
                failures.append(f"Expected null '{fld}', got {getattr(res, fld)!r}")

    elif pipeline == "cover_letter":
        text = await generate_cover_letter(
            db,
            company_name=scenario["company_name"],
            position=scenario["position"],
            job_description=scenario["job_description"],
            candidate_cv=scenario["candidate_cv"],
            company_research=scenario.get("company_research"),
        )
        low = text.lower()
        details = {"length": len(text)}
        if len(text.strip()) < 100:
            failures.append(
                f"Cover letter suspiciously short ({len(text.strip())} chars)"
            )
        must_any = scenario.get("must_include_any") or []
        if must_any and not any(t.lower() in low for t in must_any):
            failures.append(f"None of grounded terms {must_any} found in cover letter")
        for bad in scenario.get("must_not_claim_unverified") or []:
            if bad.lower() in low:
                failures.append(f"Fabricated unverified claim detected: '{bad}'")
        if scenario.get("ban_unverified_percentages"):
            pct_hits = re.findall(r"\b\d+(?:\.\d+)?%", text)
            if pct_hits:
                failures.append(
                    f"Fabricated unverified percentage metric(s): {pct_hits}"
                )

    elif pipeline == "application_qa":
        answers = await generate_application_answers(
            db,
            company_name=scenario["company_name"],
            position=scenario["position"],
            job_description=scenario["job_description"],
            candidate_cv=scenario["candidate_cv"],
            questions=scenario["questions"],
            company_research=scenario.get("company_research"),
        )
        details = {"answers_count": len(answers)}
        if len(answers) < len(scenario["questions"]):
            failures.append(
                f"Expected {len(scenario['questions'])} answers, got {len(answers)}"
            )
        else:
            a1 = str(answers[0].get("answer") or "")
            a1_low = a1.lower()
            if not any(
                t.lower() in a1_low for t in scenario.get("q1_must_include_any") or []
            ):
                failures.append("Answer 1 did not cite any grounded CV/research term")
            max_w = scenario.get("max_words_q1")
            if max_w is not None and len(a1.split()) > int(max_w):
                failures.append(
                    f"Answer 1 exceeded max_words_q1={max_w}: got {len(a1.split())} words"
                )
            if scenario.get("ban_unverified_percentages"):
                pct_hits = re.findall(r"\b\d+(?:\.\d+)?%", a1)
                if pct_hits:
                    failures.append(
                        f"Answer 1 fabricated unverified percentage metric(s): {pct_hits}"
                    )
            if len(answers) >= 2:
                a2_low = str(answers[1].get("answer") or "").lower()
                gap_any = scenario.get("q2_must_acknowledge_gap_any") or []
                if gap_any and not any(t in a2_low for t in gap_any):
                    failures.append(
                        f"Answer 2 did not honestly acknowledge missing gap: {a2_low[:200]}"
                    )
                for bad in scenario.get("q2_must_not_claim") or []:
                    if bad.lower() in a2_low:
                        failures.append(
                            f"Answer 2 fabricated unverified claim: '{bad}'"
                        )
    else:
        failures.append(f"Unknown pipeline '{pipeline}'")

    return {
        "id": scenario["id"],
        "pipeline": pipeline,
        "passed": len(failures) == 0,
        "elapsed_secs": round(time.time() - t0, 1),
        "details": details,
        "failures": failures,
    }


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
        help="Pipeline(s) to evaluate: all, system_design, jd_extraction, assessment, email_extraction, cover_letter, application_qa",
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
            f"[{tag}] {res['pipeline']:17s} | {res['id']:34s} | {res['elapsed_secs']:5.1f}s | {res['details']}"
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
