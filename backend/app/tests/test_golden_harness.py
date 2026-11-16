"""Deterministic unit tests for the shareable synthetic golden datasets, concurrency resolver, and prompt gate."""

from __future__ import annotations

from unittest.mock import patch

from app.tests.golden.eval_config import resolve_eval_concurrency
from app.tests.golden.pipeline_golden import FAKE_PERSONAS, GOLDEN_PIPELINE_SCENARIOS
from scripts.run_local_llm_gate import infer_impacted_pipelines


def test_shareable_fake_datasets_are_complete_and_grounded():
    """Verify synthetic JSON datasets cover all 3 personas, 5 non-SD pipelines, and human rationales."""
    assert set(FAKE_PERSONAS.keys()) == {
        "marcus_ai_backend",
        "elena_frontend_react",
        "samir_junior_ml",
    }
    assert {sc["pipeline"] for sc in GOLDEN_PIPELINE_SCENARIOS} == {
        "jd_extraction",
        "assessment",
        "email_extraction",
        "cover_letter",
        "application_qa",
    }
    used_personas = {
        sc["persona_id"] for sc in GOLDEN_PIPELINE_SCENARIOS if sc.get("persona_id")
    }
    assert used_personas == set(FAKE_PERSONAS.keys())
    for sc in GOLDEN_PIPELINE_SCENARIOS:
        assert sc.get("human_rationale"), f"Scenario {sc['id']} missing human_rationale"
        if sc.get("persona_id"):
            assert sc.get("candidate_cv")
            assert sc.get("candidate_spoken_languages")


def test_resolve_eval_concurrency_priority_order(monkeypatch):
    """Verify CLI -> LLM_EVAL_CONCURRENCY env -> benchmark -> provider.max_concurrency priority."""
    provider = {
        "id": 1,
        "name": "Local LM Studio",
        "max_concurrency": 3,
        "is_active": True,
    }

    with patch(
        "app.tests.golden.eval_config.fetch_active_provider", return_value=provider
    ):
        monkeypatch.delenv("LLM_EVAL_CONCURRENCY", raising=False)
        res_provider = resolve_eval_concurrency()
        assert res_provider["concurrency"] == 3
        assert "Local LM Studio" in res_provider["source"]

        monkeypatch.setenv("LLM_EVAL_CONCURRENCY", "5")
        res_env = resolve_eval_concurrency()
        assert res_env["concurrency"] == 5
        assert res_env["source"] == "env:LLM_EVAL_CONCURRENCY"

        res_cli = resolve_eval_concurrency(explicit_concurrency=2)
        assert res_cli["concurrency"] == 2
        assert res_cli["source"] == "cli"

        with patch(
            "app.tests.golden.eval_config.run_provider_benchmark",
            return_value={
                "recommended_max_concurrency": 4,
                "quality_gate_passed": True,
            },
        ):
            monkeypatch.delenv("LLM_EVAL_CONCURRENCY", raising=False)
            res_bm = resolve_eval_concurrency(run_benchmark=True)
            assert res_bm["concurrency"] == 4
            assert res_bm["source"] == "benchmark_service"


def test_local_gate_infers_minimal_impacted_pipelines():
    """Verify prompt-change detector selects only affected golden pipelines including datasets/*.json."""
    assert infer_impacted_pipelines(["frontend/src/views/QueueView.vue"]) == []
    assert infer_impacted_pipelines(["backend/app/services/diagram_catalog.py"]) == [
        "system_design"
    ]
    assert infer_impacted_pipelines(
        ["backend/app/tests/golden/datasets/assessment.json"]
    ) == ["assessment"]
    assert infer_impacted_pipelines(
        ["backend/app/tests/golden/datasets/fake_personas.json"]
    ) == ["application_qa", "assessment", "cover_letter"]
    assert infer_impacted_pipelines(
        ["backend/app/core/prompts.py"],
        prompt_diff_text='@@ "system_design_reviewer": ( ...',
    ) == ["system_design"]
    assert infer_impacted_pipelines(
        ["backend/app/core/prompts.py"],
        prompt_diff_text='@@ "jd_extraction": ( ... "assessment": (',
    ) == ["assessment", "jd_extraction"]
