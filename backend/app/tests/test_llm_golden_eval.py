"""Opt-in live LM Studio benchmark suite (run explicitly with RUN_LLM_EVAL=1)."""

import os

import pytest

from app.tests.golden.system_design_golden import GOLDEN_SYSTEM_DESIGN_SCENARIOS
from scripts.eval_system_design_llm import run_single_scenario


@pytest.mark.llm_eval
@pytest.mark.skipif(
    os.getenv("RUN_LLM_EVAL") != "1",
    reason="Live LM Studio golden eval is opt-in (set RUN_LLM_EVAL=1).",
)
@pytest.mark.parametrize(
    "scenario", GOLDEN_SYSTEM_DESIGN_SCENARIOS, ids=lambda s: s["id"]
)
def test_golden_system_design_llm_calibration(scenario):
    """Run live LM Studio golden evaluation per scenario."""
    res = run_single_scenario(scenario)
    assert res["passed"], (
        f"Golden scenario '{scenario['id']}' failed: {res['failures']}"
    )
