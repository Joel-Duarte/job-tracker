"""Tests for external Frontier prompt preparation & import endpoints on applications."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.models.candidate_profile import CandidateCVModel


@pytest.mark.asyncio
async def test_deliverable_frontier_prompts_and_guide_import(db_session: AsyncSession):
    """Verify Frontier prompt generation for Cover Letter, Q&A, Interview Guide and guide HTML PATCH."""
    comp = CompanyModel(
        name="FrontierTestCorp",
        name_normalized="frontiertestcorp",
        domain="frontiertest.example",
        company_research={
            "summary": "Cloud observability SaaS serving enterprise SRE teams.",
            "engineering_culture": "High ownership and strict latency SLOs.",
        },
    )
    db_session.add(comp)
    await db_session.flush()

    app_row = ApplicationModel(
        company_id=comp.id,
        position="Staff Backend Engineer",
        status="APPLIED",
    )
    db_session.add(app_row)
    await db_session.flush()

    jp = JobPostingModel(
        application_id=app_row.id,
        job_url="https://frontiertest.example/jobs/backend",
        description_markdown="Looking for a Staff Python/PostgreSQL Engineer to scale trace ingestion.",
    )
    cv_row = CandidateCVModel(
        raw_text="Alex Test — 8 years Python, FastAPI, PostgreSQL, Redis.",
        anonymized_text="[Candidate Name] — 8 years Python, FastAPI, PostgreSQL, Redis.",
        extracted_skills=["Python", "FastAPI", "PostgreSQL", "Redis"],
    )
    db_session.add_all([jp, cv_row])
    await db_session.commit()
    await db_session.refresh(app_row)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            cl_res = await client.post(
                f"/api/v1/applications/{app_row.id}/cover-letter/frontier-prompt",
                json={"tone": "technical", "length": "concise"},
            )
            assert cl_res.status_code == 200
            cl_data = cl_res.json()
            assert "FrontierTestCorp" in cl_data["markdown_prompt"]
            assert "FastAPI" in cl_data["markdown_prompt"]
            assert cl_data["filename"].endswith(".md")

            qa_res = await client.post(
                f"/api/v1/applications/{app_row.id}/questions/frontier-prompt",
                json={
                    "questions": [
                        {
                            "id": "q1",
                            "question": "Why FrontierTestCorp?",
                            "word_limit": 120,
                        }
                    ],
                    "tone": "professional",
                },
            )
            assert qa_res.status_code == 200
            qa_data = qa_res.json()
            assert "Why FrontierTestCorp?" in qa_data["markdown_prompt"]
            assert '"id": "q1"' in qa_data["markdown_prompt"]

            ig_res = await client.post(
                f"/api/v1/applications/{app_row.id}/interview-guide/frontier-prompt",
                json={
                    "language": "en",
                    "selected_sections": ["role_company_brief", "star_stories"],
                },
            )
            assert ig_res.status_code == 200
            assert "Role & Company Brief" in ig_res.json()["markdown_prompt"]

            patch_res = await client.patch(
                f"/api/v1/applications/{app_row.id}/interview-guide",
                json={
                    "interview_guide_html": "<h2>Imported Brief</h2><p>Ready for loop.</p>",
                    "language": "en",
                },
            )
            assert patch_res.status_code == 200
            assert "<h2>Imported Brief</h2>" in patch_res.json()["interview_guide_html"]
    finally:
        app.dependency_overrides.clear()
