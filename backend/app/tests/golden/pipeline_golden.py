"""Shareable synthetic multi-persona golden evaluation datasets loader.

All personas, job descriptions, emails, cover letters, and application Q&A scenarios live in
`backend/app/tests/golden/datasets/*.json` with human-authored expectations and rationales.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

PIPELINE_DATASET_FILES: tuple[str, ...] = (
    "jd_extraction.json",
    "assessment.json",
    "email_extraction.json",
    "cover_letter.json",
    "application_qa.json",
    "cv_anonymization.json",
    "role_alignment_dossier.json",
    "interview_star_eval.json",
    "interview_mc_generator.json",
    "interview_mc_eval.json",
    "interview_drilldown.json",
    "interview_question_gen.json",
    "llm_judge.json",
    "agent_system.json",
    "system_design_interviewer.json",
    "system_design_coach.json",
)


def load_fake_personas() -> dict[str, dict[str, Any]]:
    """Load synthetic candidate personas from datasets/fake_personas.json."""
    raw = json.loads((DATASETS_DIR / "fake_personas.json").read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def load_pipeline_scenarios() -> list[dict[str, Any]]:
    """Load and enrich all non-System-Design-review golden scenarios from datasets/*.json."""
    personas = load_fake_personas()
    scenarios: list[dict[str, Any]] = []
    for filename in PIPELINE_DATASET_FILES:
        items = json.loads((DATASETS_DIR / filename).read_text(encoding="utf-8"))
        assert isinstance(items, list), f"{filename} must contain a JSON array."
        for item in items:
            enriched = dict(item)
            persona_id = enriched.get("persona_id")
            if persona_id:
                persona = personas[persona_id]
                enriched.setdefault("candidate_cv", persona["cv_text"])
                enriched.setdefault("candidate_skills", persona["skills"])
                enriched.setdefault(
                    "candidate_years_of_experience", persona["years_of_experience"]
                )
                enriched.setdefault(
                    "candidate_spoken_languages", persona["spoken_languages"]
                )
            scenarios.append(enriched)
    return scenarios


FAKE_PERSONAS: dict[str, dict[str, Any]] = load_fake_personas()
GOLDEN_PIPELINE_SCENARIOS: list[dict[str, Any]] = load_pipeline_scenarios()
