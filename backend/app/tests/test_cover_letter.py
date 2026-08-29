from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config_manager import load_settings, save_settings
from app.core.prompts import DEFAULT_PROMPTS
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.applications import CoverLetterResponse, CoverLetterUpdateRequest
from app.schemas.global_settings import GlobalSettingsRead, GlobalSettingsUpdate
from app.services.graph_nodes import cover_letter_node


def test_cover_letter_schemas():
    # CoverLetterResponse schema
    resp = CoverLetterResponse(
        application_id=1,
        cover_letter_text="Dear Hiring Manager...",
        cover_letter_status="GENERATED",
        cover_letter_generated_at=datetime.now(UTC),
    )
    assert resp.application_id == 1
    assert resp.cover_letter_status == "GENERATED"
    assert "Hiring Manager" in resp.cover_letter_text

    # CoverLetterUpdateRequest schema
    update = CoverLetterUpdateRequest(
        cover_letter_text="Updated text",
        cover_letter_status="DRAFTED",
    )
    assert update.cover_letter_text == "Updated text"
    assert update.cover_letter_status == "DRAFTED"

    # GlobalSettings schemas with Cover Letter fields
    gs_read = GlobalSettingsRead(
        ENABLE_EMBEDDINGS=True,
        AGENT_CHAT_RETENTION_DAYS=7,
        ENABLE_AUTO_COVER_LETTER=True,
        COVER_LETTER_MATCH_THRESHOLD=75,
        COVER_LETTER_LENGTH="concise",
    )
    assert gs_read.ENABLE_AUTO_COVER_LETTER is True
    assert gs_read.COVER_LETTER_MATCH_THRESHOLD == 75
    assert gs_read.COVER_LETTER_LENGTH == "concise"

    gs_update = GlobalSettingsUpdate(
        ENABLE_AUTO_COVER_LETTER=False,
        COVER_LETTER_MATCH_THRESHOLD=80,
        COVER_LETTER_LENGTH="detailed",
    )
    assert gs_update.ENABLE_AUTO_COVER_LETTER is False
    assert gs_update.COVER_LETTER_MATCH_THRESHOLD == 80
    assert gs_update.COVER_LETTER_LENGTH == "detailed"


def test_cover_letter_prompt_template_exists():
    assert "cover_letter" in DEFAULT_PROMPTS
    template = DEFAULT_PROMPTS["cover_letter"]
    assert "{company_name}" in template
    assert "{position}" in template
    assert "{job_description}" in template
    assert "{candidate_cv}" in template
    assert "{length}" in template


@pytest.mark.asyncio
async def test_global_settings_cover_letter(db_session):
    # Verify defaults
    settings = await load_settings(db_session)
    assert settings["ENABLE_AUTO_COVER_LETTER"] is True
    assert settings["COVER_LETTER_MATCH_THRESHOLD"] == 70

    # Save new values
    await save_settings(
        {
            "ENABLE_AUTO_COVER_LETTER": False,
            "COVER_LETTER_MATCH_THRESHOLD": 80,
        },
        db=db_session,
    )

    updated = await load_settings(db_session)
    assert updated["ENABLE_AUTO_COVER_LETTER"] is False
    assert updated["COVER_LETTER_MATCH_THRESHOLD"] == 80


@pytest.mark.asyncio
async def test_cover_letter_node_skipped_when_disabled(db_session):
    # Setup company and application
    company = CompanyModel(name="Test Co", name_normalized="test co")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Backend Engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()

    # Settings: auto generation disabled
    await save_settings(
        {"ENABLE_AUTO_COVER_LETTER": False, "COVER_LETTER_MATCH_THRESHOLD": 70},
        db=db_session,
    )

    state = {
        "application_id": application.id,
        "match_score": 0.85,  # 85% score
    }
    config = {"configurable": {"db": db_session}}

    result = await cover_letter_node(state, config)
    assert result["cover_letter_status"] == "SKIPPED"

    await db_session.refresh(application)
    assert application.cover_letter_status == "SKIPPED"


@pytest.mark.asyncio
async def test_cover_letter_node_skipped_below_threshold(db_session):
    # Setup company and application
    company = CompanyModel(name="Low Score Co", name_normalized="low score co")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Frontend Engineer",
        status="APPLIED",
    )
    db_session.add(application)

    task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        status="PROCESSING",
        stage="MATCHING",
        result_json={"fit_score": 50},
    )
    db_session.add(task)
    await db_session.commit()

    # Settings: auto generation enabled with 70% threshold
    await save_settings(
        {"ENABLE_AUTO_COVER_LETTER": True, "COVER_LETTER_MATCH_THRESHOLD": 70},
        db=db_session,
    )

    state = {
        "application_id": application.id,
        "match_score": 0.50,  # 50% score
        "task_id": task.id,
    }
    config = {"configurable": {"db": db_session}}

    result = await cover_letter_node(state, config)
    assert result["cover_letter_status"] == "SKIPPED"

    await db_session.refresh(application)
    assert application.cover_letter_status == "SKIPPED"

    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert task.result_json["cover_letter_status"] == "SKIPPED"
    assert "skipped" in task.result_json["cover_letter_note"]


@pytest.mark.asyncio
async def test_cover_letter_node_generates_when_above_threshold(db_session):
    # Setup active CV
    cv = CandidateCVModel(
        raw_text="Experienced Software Engineer with Python and FastAPI experience.",
    )
    db_session.add(cv)

    company = CompanyModel(name="High Score Co", name_normalized="high score co")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Python Developer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()

    # Settings: auto generation enabled with 70% threshold
    await save_settings(
        {"ENABLE_AUTO_COVER_LETTER": True, "COVER_LETTER_MATCH_THRESHOLD": 70},
        db=db_session,
    )

    state = {
        "application_id": application.id,
        "match_score": 0.90,  # 90% score
    }
    config = {"configurable": {"db": db_session}}

    mock_letter = (
        "Dear Hiring Manager,\n\nI am excited to apply for Senior Python Developer..."
    )

    with patch(
        "app.services.llm.generate_cover_letter",
        new=AsyncMock(return_value=mock_letter),
    ):
        result = await cover_letter_node(state, config)

    assert result["cover_letter_status"] == "GENERATED"

    await db_session.refresh(application)
    assert application.cover_letter_status == "GENERATED"
    assert application.cover_letter_text == mock_letter
    assert application.cover_letter_generated_at is not None


@pytest.mark.asyncio
async def test_cover_letter_api_endpoints(db_session):
    company = CompanyModel(name="API Test Co", name_normalized="api test co")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="DevOps Engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. GET cover letter (initially empty)
        res = await ac.get(f"/api/v1/applications/{application.id}/cover-letter")
        assert res.status_code == 200
        data = res.json()
        assert data["application_id"] == application.id
        assert data["cover_letter_text"] is None
        assert data["cover_letter_status"] is None

        # 2. PATCH cover letter manually
        res = await ac.patch(
            f"/api/v1/applications/{application.id}/cover-letter",
            json={
                "cover_letter_text": "Custom edited cover letter.",
                "cover_letter_status": "DRAFTED",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["cover_letter_text"] == "Custom edited cover letter."
        assert data["cover_letter_status"] == "DRAFTED"

        # 3. POST generate cover letter (Queues background task with HTTP 202)
        with patch("app.routers.applications.process_evaluation_task"):
            res = await ac.post(
                f"/api/v1/applications/{application.id}/cover-letter/generate"
            )
            assert res.status_code == 202
            data = res.json()
            assert data["cover_letter_status"] == "QUEUED"

        # 4. POST regenerate cover letter
        with patch("app.routers.applications.process_evaluation_task"):
            res = await ac.post(
                f"/api/v1/applications/{application.id}/cover-letter/regenerate"
            )
            assert res.status_code == 202
            data = res.json()
            assert data["cover_letter_status"] == "QUEUED"
