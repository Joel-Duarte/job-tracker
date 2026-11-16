"""Opt-in live LM Studio benchmark suite (run explicitly with RUN_LLM_EVAL=1)."""

import os

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.prompt_eval_service import evaluate_pipeline_scenario
from app.tests.golden.pipeline_golden import GOLDEN_PIPELINE_SCENARIOS
from app.tests.golden.system_design_golden import GOLDEN_SYSTEM_DESIGN_SCENARIOS
from scripts.eval_system_design_llm import run_single_scenario
from scripts.run_golden_evals import resolve_async_db_url


@pytest.mark.llm_eval
@pytest.mark.skipif(
    os.getenv("RUN_LLM_EVAL") != "1",
    reason="Live LM Studio golden eval is opt-in (set RUN_LLM_EVAL=1).",
)
@pytest.mark.parametrize(
    "scenario", GOLDEN_SYSTEM_DESIGN_SCENARIOS, ids=lambda s: s["id"]
)
def test_golden_system_design_llm_calibration(scenario):
    """Run live LM Studio golden evaluation per System Design scenario."""
    res = run_single_scenario(scenario)
    assert res["passed"], (
        f"Golden scenario '{scenario['id']}' failed: {res['failures']}"
    )


@pytest.mark.llm_eval
@pytest.mark.skipif(
    os.getenv("RUN_LLM_EVAL") != "1",
    reason="Live LM Studio golden eval is opt-in (set RUN_LLM_EVAL=1).",
)
@pytest.mark.parametrize("scenario", GOLDEN_PIPELINE_SCENARIOS, ids=lambda s: s["id"])
@pytest.mark.asyncio
async def test_golden_pipeline_llm_calibration(scenario):
    """Run live LM Studio golden evaluation across core LLM pipelines."""
    engine = create_async_engine(resolve_async_db_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            res = await evaluate_pipeline_scenario(scenario, db)
    finally:
        await engine.dispose()
    assert res["passed"], (
        f"Golden pipeline '{scenario['id']}' failed: {res['failures']}"
    )
