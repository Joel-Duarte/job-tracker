"""Deterministic unit tests for the local LLM golden evaluation harness, PII scrubber, and prompt gate."""

from __future__ import annotations

from unittest.mock import patch

from app.tests.golden.eval_config import resolve_eval_concurrency
from app.tests.golden.pii_scrubber import find_residual_pii, scrub_nested, scrub_pii
from app.tests.golden.pipeline_golden import GOLDEN_PIPELINE_SCENARIOS
from scripts.export_golden_from_db import _audit_match_row
from scripts.run_local_llm_gate import infer_impacted_pipelines


def test_pii_scrubber_redacts_contacts_links_and_custom_terms():
    """Verify emails, phone numbers, social URLs, signatures, and explicit company terms are scrubbed."""
    raw = (
        "Contact Alice Doe at alice.doe@acme-corp.com or +1 (415) 555-0199.\n"
        "Profile: https://www.linkedin.com/in/alicedoe123 and https://github.com/alicedoe\n"
        "Salary range $160,000 - $185,000 USD in 2026.\n"
        "Best regards,\nAlice Doe"
    )
    cleaned, counts = scrub_pii(raw, extra_terms=["Acme-Corp"])
    assert "alice.doe@acme-corp.com" not in cleaned
    assert "555-0199" not in cleaned
    assert "linkedin.com/in/alicedoe123" not in cleaned
    assert "$160,000 - $185,000" in cleaned  # Preserve compensation figures
    assert "2026" in cleaned
    assert counts["email"] == 1
    assert counts["phone"] == 1
    assert find_residual_pii(cleaned) == []

    nested = scrub_nested({"nested": ["Reach bob@test.io"]}, extra_terms=["Acme"])
    assert nested["nested"][0] == "Reach [EMAIL]"


def test_audit_match_row_detects_conflicts_and_pseudo_risks():
    """Verify match quality auditor flags score/recommendation conflicts and pseudo-risks."""
    clean = _audit_match_row(
        {
            "match_analysis_payload": {
                "fit_score": 84,
                "programmatic_match_score": 80,
                "recommendation": "APPLY_STRONGLY",
                "critical_risks": ["Requires Kubernetes cluster ops"],
            }
        }
    )
    assert clean["audit_flags"] == []

    noisy = _audit_match_row(
        {
            "match_analysis_payload": {
                "fit_score": 85,
                "programmatic_match_score": 25,
                "recommendation": "DO_NOT_APPLY",
                "critical_risks": ["No critical risks found"],
            }
        }
    )
    assert any("score_rec_conflict" in f for f in noisy["audit_flags"])
    assert any("ai_vs_algo_delta" in f for f in noisy["audit_flags"])
    assert any("pseudo_risk" in f for f in noisy["audit_flags"])


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
    """Verify prompt-change detector selects only affected golden pipelines."""
    assert infer_impacted_pipelines(["frontend/src/views/QueueView.vue"]) == []
    assert infer_impacted_pipelines(["backend/app/services/diagram_catalog.py"]) == [
        "system_design"
    ]
    assert infer_impacted_pipelines(
        ["backend/app/core/prompts.py"],
        prompt_diff_text='@@ "system_design_reviewer": ( ...',
    ) == ["system_design"]
    assert infer_impacted_pipelines(
        ["backend/app/core/prompts.py"],
        prompt_diff_text='@@ "jd_extraction": ( ... "assessment": (',
    ) == ["assessment", "jd_extraction"]
    assert {sc["pipeline"] for sc in GOLDEN_PIPELINE_SCENARIOS} == {
        "jd_extraction",
        "assessment",
        "email_extraction",
        "cover_letter",
        "application_qa",
    }
