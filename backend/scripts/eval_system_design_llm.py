"""Opt-in live Local LM Studio golden benchmark runner for System Design prompts.

Usage:
    cd backend
    uv run python scripts/eval_system_design_llm.py
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from typing import Any

from app.tests.golden.system_design_golden import GOLDEN_SYSTEM_DESIGN_SCENARIOS

BASE = "http://127.0.0.1:10555/api/v1/system-design"


def _http_json(
    path: str, method: str = "GET", body: dict[str, Any] | None = None
) -> dict[str, Any] | list[Any]:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw.strip() else {}


def _poll_session(sid: int, timeout: float = 180.0) -> tuple[dict[str, Any], float]:
    t0 = time.time()
    while time.time() - t0 < timeout:
        sess = _http_json(f"/sessions/{sid}")
        assert isinstance(sess, dict)
        if sess.get("active_task_status") in (None, "COMPLETED", "FAILED"):
            return sess, time.time() - t0
        time.sleep(2.0)
    raise TimeoutError(f"Session {sid} background task exceeded {timeout}s")


def run_single_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    """Run one golden scenario end-to-end against the live Docker API / LM Studio backend."""
    ch = _http_json(f"/challenges/{scenario['challenge_slug']}")
    assert isinstance(ch, dict)
    sess = _http_json(
        "/sessions",
        "POST",
        {
            "challenge_id": ch["id"],
            "mode": "ADAPTIVE",
            "variant_id": scenario["variant_id"],
        },
    )
    assert isinstance(sess, dict)
    sid = int(sess["id"])
    failures: list[str] = []

    try:
        _http_json(
            f"/sessions/{sid}/requirements/reveal",
            "POST",
            {"lock_and_proceed": True},
        )
        _http_json(
            f"/sessions/{sid}/diagrams/canvas",
            "POST",
            {
                "nodes": scenario["nodes"],
                "edges": scenario["edges"],
                "notes": scenario["canvas_notes"],
            },
        )
        _http_json(f"/sessions/{sid}/review", "POST", {"use_web_search": False})
        s_rev, rev_secs = _poll_session(sid)
        if s_rev.get("active_task_status") == "FAILED":
            failures.append(f"Review task failed: {s_rev.get('active_task_error')}")
            rev = {}
        else:
            revs = s_rev.get("architecture_reviews") or []
            rev = revs[-1] if revs else {}

        missing_text = " ".join(rev.get("missing_components") or []).lower()
        complexity_text = " ".join(rev.get("unnecessary_complexity") or []).lower()
        for bad_term in scenario.get("forbidden_false_missing", []):
            if bad_term.lower() in missing_text:
                failures.append(
                    f"False missing component penalty: '{bad_term}' in {rev.get('missing_components')}"
                )
        for bad_term in scenario.get("forbidden_false_complexity", []):
            if bad_term.lower() in complexity_text:
                failures.append(
                    f"False complexity penalty: '{bad_term}' in {rev.get('unnecessary_complexity')}"
                )

        _http_json(
            f"/sessions/{sid}/defence/message",
            "POST",
            {"message": scenario["defence_answer"]},
        )
        _http_json(f"/sessions/{sid}/evaluate", "POST")
        s_eval, eval_secs = _poll_session(sid)
        score = float(s_eval.get("overall_score") or 0.0)
        rating = str(s_eval.get("readiness_rating") or "")
        if s_eval.get("active_task_status") == "FAILED" or not s_eval.get(
            "final_evaluation"
        ):
            failures.append(f"Evaluation failed: {s_eval.get('active_task_error')}")
        else:
            if (
                score < scenario["min_final_score"]
                or score > scenario["max_final_score"]
            ):
                failures.append(
                    f"Score {score} out of expected band [{scenario['min_final_score']}, {scenario['max_final_score']}]"
                )

        return {
            "id": scenario["id"],
            "title": scenario["title"],
            "passed": len(failures) == 0,
            "score": score,
            "rating": rating,
            "rev_secs": round(rev_secs, 1),
            "eval_secs": round(eval_secs, 1),
            "missing_components": rev.get("missing_components") or [],
            "unnecessary_complexity": rev.get("unnecessary_complexity") or [],
            "failures": failures,
        }
    finally:
        try:
            _http_json(f"/sessions/{sid}", "DELETE")
        except Exception:
            pass


async def _main() -> int:
    results = []
    for scenario in GOLDEN_SYSTEM_DESIGN_SCENARIOS:
        res = await asyncio.to_thread(run_single_scenario, scenario)
        status_tag = "PASS" if res["passed"] else "FAIL"
        print(
            f"[{status_tag}] {res['id']:30s} score={res['score']:5.1f} ({res['rating']}) "
            f"rev={res['rev_secs']}s eval={res['eval_secs']}s"
        )
        if res["failures"]:
            for err in res["failures"]:
                print(f"       -> {err}")
        results.append(res)

    passed = sum(1 for r in results if r["passed"])
    print(f"\nGolden Eval Summary: {passed}/{len(results)} passed.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
