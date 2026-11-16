"""Deterministic unit tests for synthetic golden datasets, concurrency resolution, prompt-eval endpoint, and gate."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.prompts import _PROMPT_OVERRIDE_CTX, get_prompt_template, prompt_overrides
from app.main import app
from app.services.prompt_eval_service import PROMPT_TO_PIPELINE, get_golden_cases_count
from app.tests.golden.eval_config import resolve_eval_concurrency
from app.tests.golden.pipeline_golden import FAKE_PERSONAS, GOLDEN_PIPELINE_SCENARIOS
from scripts.run_local_llm_gate import infer_impacted_pipelines


def test_shareable_fake_datasets_are_complete_and_grounded():
    """Verify synthetic JSON datasets cover all 3 personas, 10 non-SD pipelines, and human rationales."""
    assert set(FAKE_PERSONAS.keys()) == {
        "marcus_ai_backend",
        "elena_frontend_react",
        "samir_junior_ml",
    }
    expected_pipelines = set(PROMPT_TO_PIPELINE.values()) - {"system_design"}
    assert {sc["pipeline"] for sc in GOLDEN_PIPELINE_SCENARIOS} == expected_pipelines
    used_personas = {
        sc["persona_id"] for sc in GOLDEN_PIPELINE_SCENARIOS if sc.get("persona_id")
    }
    assert used_personas == set(FAKE_PERSONAS.keys())
    for sc in GOLDEN_PIPELINE_SCENARIOS:
        assert sc.get("human_rationale"), f"Scenario {sc['id']} missing human_rationale"
        if sc.get("persona_id"):
            assert sc.get("candidate_cv")
            assert sc.get("candidate_spoken_languages")


@pytest.mark.asyncio
async def test_prompt_override_context_is_isolated(db_session: AsyncSession):
    """Verify prompt_overrides overrides get_prompt_template without touching DB."""
    assert _PROMPT_OVERRIDE_CTX.get() is None
    with prompt_overrides({"jd_extraction": "CUSTOM_TEMP_PROMPT"}):
        val = await get_prompt_template(db_session, "jd_extraction")
        assert val == "CUSTOM_TEMP_PROMPT"
    assert _PROMPT_OVERRIDE_CTX.get() is None


@pytest.mark.asyncio
async def test_prompts_evaluate_endpoint_and_metadata(db_session: AsyncSession):
    """Verify GET /prompts includes golden metadata and POST /prompts/{name}/evaluate returns A/B delta."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            list_res = await client.get("/api/v1/prompts")
            assert list_res.status_code == 200
            by_name = {item["name"]: item for item in list_res.json()}
            assert by_name["jd_extraction"]["has_golden_eval"] is True
            assert by_name["jd_extraction"][
                "golden_cases_count"
            ] == get_golden_cases_count("jd_extraction")
            assert by_name["company_research"]["has_golden_eval"] is False

            unsupported = await client.post(
                "/api/v1/prompts/company_research/evaluate",
                json={"compare_default": True},
            )
            assert unsupported.status_code == 400

            mocked_eval = {
                "prompt_name": "jd_extraction",
                "pipeline": "jd_extraction",
                "candidate_source": "candidate_editor",
                "concurrency": 3,
                "concurrency_source": "provider:Local LM Studio",
                "candidate_result": {
                    "pipeline": "jd_extraction",
                    "concurrency": 3,
                    "wall_secs": 10.2,
                    "passed": 3,
                    "total": 3,
                    "pass_rate": 100.0,
                    "all_passed": True,
                    "results": [],
                },
                "default_result": {
                    "pipeline": "jd_extraction",
                    "concurrency": 3,
                    "wall_secs": 11.4,
                    "passed": 2,
                    "total": 3,
                    "pass_rate": 66.7,
                    "all_passed": False,
                    "results": [],
                },
                "delta_passed": 1,
                "delta_pass_rate": 33.3,
            }
            with patch(
                "app.routers.prompts.evaluate_prompt_against_golden",
                new_callable=AsyncMock,
                return_value=mocked_eval,
            ):
                eval_res = await client.post(
                    "/api/v1/prompts/jd_extraction/evaluate",
                    json={
                        "candidate_template": "Test prompt...",
                        "compare_default": True,
                    },
                )
                assert eval_res.status_code == 200
                body = eval_res.json()
                assert body["delta_passed"] == 1
                assert body["delta_pass_rate"] == 33.3
                assert body["candidate_result"]["pass_rate"] == 100.0
    finally:
        app.dependency_overrides.clear()


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
        "system_design",
        "system_design_coach",
    ]
    assert infer_impacted_pipelines(
        ["backend/app/tests/golden/datasets/assessment.json"]
    ) == ["assessment"]
    assert infer_impacted_pipelines(
        ["backend/app/tests/golden/datasets/fake_personas.json"]
    ) == [
        "application_qa",
        "assessment",
        "cover_letter",
        "interview_mc_generator",
        "interview_question_gen",
        "llm_judge",
        "role_alignment_dossier",
    ]
    assert infer_impacted_pipelines(
        ["backend/app/core/prompts.py"],
        prompt_diff_text='@@ "system_design_reviewer": ( ...',
    ) == ["system_design"]
    assert infer_impacted_pipelines(
        ["backend/app/core/prompts.py"],
        prompt_diff_text='@@ "jd_extraction": ( ... "assessment": (',
    ) == ["assessment", "jd_extraction"]
