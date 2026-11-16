"""Smart local CI gate: runs affected golden LLM evals only when prompts or LLM logic changed.

Never runs in remote CI without keys; checks local git diff, resolves concurrency from the active
provider (e.g. max_concurrency=3), and executes only impacted pipeline golden benchmarks.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from app.services.prompt_eval_service import (
    ALL_PIPELINES,
)
from app.services.prompt_eval_service import (
    PROMPT_TO_PIPELINE as PROMPT_KEY_TO_PIPELINE,
)
from app.tests.golden.eval_config import DEFAULT_API_BASE, fetch_active_provider
from scripts.run_golden_evals import run_golden_suite

REPO_ROOT = Path(__file__).resolve().parents[2]

FILE_TO_PIPELINES: dict[str, tuple[str, ...]] = {
    "backend/app/core/prompts.py": ALL_PIPELINES,
    "backend/app/core/llm_factory.py": ALL_PIPELINES,
    "backend/app/services/llm.py": (
        "jd_extraction",
        "assessment",
        "email_extraction",
        "cover_letter",
        "application_qa",
        "cv_anonymization",
    ),
    "backend/app/schemas/llm.py": (
        "jd_extraction",
        "assessment",
        "email_extraction",
        "cover_letter",
        "application_qa",
        "cv_anonymization",
    ),
    "backend/app/services/role_alignment_dossier_service.py": (
        "role_alignment_dossier",
    ),
    "backend/app/services/interview_simulator_service.py": (
        "interview_star_eval",
        "interview_mc_generator",
        "interview_mc_eval",
        "interview_drilldown",
        "interview_question_gen",
    ),
    "backend/app/services/llm_judge.py": ("llm_judge",),
    "backend/app/services/agent_tools.py": ("agent_system",),
    "backend/app/routers/agent_chat.py": ("agent_system",),
    "backend/app/tests/golden/pipeline_golden.py": tuple(
        p for p in ALL_PIPELINES if p != "system_design"
    ),
    "backend/app/tests/golden/datasets/fake_personas.json": (
        "assessment",
        "cover_letter",
        "application_qa",
        "role_alignment_dossier",
        "llm_judge",
        "interview_mc_generator",
        "interview_question_gen",
    ),
    "backend/app/tests/golden/datasets/jd_extraction.json": ("jd_extraction",),
    "backend/app/tests/golden/datasets/assessment.json": ("assessment",),
    "backend/app/tests/golden/datasets/email_extraction.json": ("email_extraction",),
    "backend/app/tests/golden/datasets/cover_letter.json": ("cover_letter",),
    "backend/app/tests/golden/datasets/application_qa.json": ("application_qa",),
    "backend/app/tests/golden/datasets/cv_anonymization.json": ("cv_anonymization",),
    "backend/app/tests/golden/datasets/role_alignment_dossier.json": (
        "role_alignment_dossier",
    ),
    "backend/app/tests/golden/datasets/interview_star_eval.json": (
        "interview_star_eval",
    ),
    "backend/app/tests/golden/datasets/interview_mc_generator.json": (
        "interview_mc_generator",
    ),
    "backend/app/tests/golden/datasets/interview_mc_eval.json": ("interview_mc_eval",),
    "backend/app/tests/golden/datasets/interview_drilldown.json": (
        "interview_drilldown",
    ),
    "backend/app/tests/golden/datasets/interview_question_gen.json": (
        "interview_question_gen",
    ),
    "backend/app/tests/golden/datasets/llm_judge.json": ("llm_judge",),
    "backend/app/tests/golden/datasets/agent_system.json": ("agent_system",),
    "backend/app/tests/golden/datasets/system_design_interviewer.json": (
        "system_design_interviewer",
    ),
    "backend/app/tests/golden/datasets/system_design_coach.json": (
        "system_design_coach",
    ),
    "backend/app/services/system_design_service.py": (
        "system_design",
        "system_design_interviewer",
        "system_design_coach",
    ),
    "backend/app/services/diagram_catalog.py": ("system_design", "system_design_coach"),
    "backend/app/services/system_design_seed.py": (
        "system_design",
        "system_design_interviewer",
        "system_design_coach",
    ),
    "backend/app/tests/golden/system_design_golden.py": ("system_design",),
}


def detect_changed_files(
    *, base_ref: str | None = None, staged: bool = False
) -> list[str]:
    """Return repository-relative changed file paths."""
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only"]
    elif base_ref:
        cmd = ["git", "diff", "--name-only", f"{base_ref}...HEAD"]
    else:
        cmd = ["git", "status", "--porcelain"]
    out = subprocess.check_output(cmd, cwd=REPO_ROOT, text=True)
    files: list[str] = []
    for line in out.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if not staged and not base_ref:
            # porcelain format: 'XY path' or 'XY old -> new'
            raw = raw[3:] if len(line) > 3 else raw
            if " -> " in raw:
                raw = raw.split(" -> ", 1)[1]
        files.append(raw.strip())
    return files


def infer_impacted_pipelines(
    changed_files: list[str],
    *,
    prompt_diff_text: str | None = None,
) -> list[str]:
    """Determine minimal set of golden pipelines impacted by changed files."""
    impacted: set[str] = set()
    for path in changed_files:
        norm = path.replace("\\", "/").lstrip("./")
        mapped = FILE_TO_PIPELINES.get(norm)
        if not mapped:
            continue
        if norm == "backend/app/core/prompts.py" and prompt_diff_text is not None:
            narrowed = _narrow_prompt_diff_pipelines(prompt_diff_text)
            if narrowed:
                impacted.update(narrowed)
                continue
        impacted.update(mapped)
    return sorted(impacted)


def _narrow_prompt_diff_pipelines(diff_text: str) -> set[str]:
    """Extract specific pipeline names when prompts.py diff touches identifiable prompt sections."""
    hits: set[str] = set()
    low = diff_text.lower()
    for key, pipeline in PROMPT_KEY_TO_PIPELINE.items():
        if key in low:
            hits.add(pipeline)
    return hits


def run_gate(
    *,
    base_ref: str | None = None,
    staged: bool = False,
    force_all: bool = False,
    allow_offline: bool = False,
    explicit_concurrency: int | None = None,
    run_benchmark: bool = False,
    base_url: str = DEFAULT_API_BASE,
) -> int:
    """Evaluate git diff and execute required golden evals locally when needed."""
    if os.getenv("SKIP_LLM_EVAL") == "1":
        print("[local-llm-gate] SKIP_LLM_EVAL=1 set -> skipping live golden evals.")
        return 0
    if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
        print(
            "[local-llm-gate] Remote CI environment detected (no local LLM keys) -> skipping live golden evals."
        )
        return 0

    if force_all:
        impacted = list(ALL_PIPELINES)
    else:
        changed = detect_changed_files(base_ref=base_ref, staged=staged)
        prompt_diff: str | None = None
        if "backend/app/core/prompts.py" in changed:
            diff_cmd = ["git", "diff"]
            if staged:
                diff_cmd.append("--cached")
            elif base_ref:
                diff_cmd.append(f"{base_ref}...HEAD")
            diff_cmd.extend(["-U25", "--", "backend/app/core/prompts.py"])
            prompt_diff = subprocess.check_output(diff_cmd, cwd=REPO_ROOT, text=True)
        impacted = infer_impacted_pipelines(changed, prompt_diff_text=prompt_diff)

    if not impacted:
        print(
            "[local-llm-gate] No prompt or LLM service files changed -> skipping golden evals."
        )
        return 0

    provider = fetch_active_provider(base_url=base_url)
    if provider is None:
        msg = (
            f"[local-llm-gate] Backend API ({base_url}) or local LM Studio is offline."
        )
        if allow_offline:
            print(f"{msg} --allow-offline set; passing without live eval.")
            return 0
        print(
            f"{msg} Start Docker/LM Studio or bypass explicitly with SKIP_LLM_EVAL=1."
        )
        return 1

    print(
        f"[local-llm-gate] Prompt/LLM changes detected -> running golden pipelines: {impacted}"
    )
    summary: dict[str, Any] = asyncio.run(
        run_golden_suite(
            pipelines=impacted,
            explicit_concurrency=explicit_concurrency,
            run_benchmark=run_benchmark,
            api_base_url=base_url,
        )
    )
    print(
        f"[local-llm-gate] Concurrency={summary['concurrency']} ({summary['concurrency_source']})"
    )
    for res in summary["results"]:
        tag = "PASS" if res["passed"] else "FAIL"
        print(
            f"  [{tag}] {res['pipeline']:17s} | {res['id']:34s} | {res['elapsed_secs']:5.1f}s"
        )
        for err in res.get("failures") or []:
            print(f"         -> {err}")
    print(
        f"[local-llm-gate] Summary: {summary['passed']}/{summary['total']} passed in {summary['wall_secs']}s."
    )
    return 0 if summary["all_passed"] else 1


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Local prompt-change golden eval gate."
    )
    parser.add_argument("--staged", action="store_true", help="Inspect staged changes")
    parser.add_argument(
        "--base", default=None, help="Git base ref (e.g. origin/master)"
    )
    parser.add_argument("--all", action="store_true", help="Force all golden pipelines")
    parser.add_argument(
        "--allow-offline",
        action="store_true",
        help="Do not fail if backend/LM Studio is not currently running locally",
    )
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    return run_gate(
        base_ref=args.base,
        staged=args.staged,
        force_all=args.all,
        allow_offline=args.allow_offline,
        explicit_concurrency=args.concurrency,
        run_benchmark=args.benchmark,
    )


if __name__ == "__main__":
    raise SystemExit(_main())
