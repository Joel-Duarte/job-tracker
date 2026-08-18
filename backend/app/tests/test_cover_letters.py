from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.runnables import RunnableLambda
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.cover_letter import (
    CoverLetterGenerateRequest,
    CoverLetterResponse,
    CoverLetterUpdateRequest,
)
from app.schemas.global_settings import GlobalSettingsRead, GlobalSettingsUpdate
from app.services.cover_letter import CoverLetterLLMResult, generate_cover_letter_chain
from app.services.evaluation_worker import process_evaluation_task


def test_cover_letter_schemas_validation():
    """Verifies schema instantiation, field aliases, and default values."""
    gen_req = CoverLetterGenerateRequest(
        custom_instructions="Emphasize payment systems leadership",
        tone="confident",
    )
    assert gen_req.custom_instructions == "Emphasize payment systems leadership"
    assert gen_req.tone == "confident"

    update_req = CoverLetterUpdateRequest(
        content="# Cover Letter\nDear Hiring Manager..."
    )
    assert update_req.content == "# Cover Letter\nDear Hiring Manager..."

    now = datetime.now(UTC)
    resp = CoverLetterResponse(
        application_id=42,
        cover_letter_markdown="# Cover Letter\nDear Recruiter...",
        content="# Cover Letter\nDear Recruiter...",
        cover_letter_status="COMPLETED",
        status="COMPLETED",
        highlighted_skills=["Python", "FastAPI", "PostgreSQL"],
        created_at=now,
        updated_at=now,
    )
    assert resp.application_id == 42
    assert resp.cover_letter_status == "COMPLETED"
    assert resp.status == "COMPLETED"
    assert resp.cover_letter_markdown == "# Cover Letter\nDear Recruiter..."
    assert resp.content == "# Cover Letter\nDear Recruiter..."
    assert "FastAPI" in resp.highlighted_skills


def test_global_settings_cover_letter_fields():
    """Verifies GlobalSettingsRead & Update schemas include cover letter configuration."""
    read = GlobalSettingsRead(
        ENABLE_EMBEDDINGS=True,
        auto_generate_cover_letter=True,
        cover_letter_min_match_pct=75,
    )
    assert read.auto_generate_cover_letter is True
    assert read.cover_letter_min_match_pct == 75

    update = GlobalSettingsUpdate(
        auto_generate_cover_letter=False,
        cover_letter_min_match_pct=60,
    )
    assert update.auto_generate_cover_letter is False
    assert update.cover_letter_min_match_pct == 60


async def test_cover_letter_chain_structured_and_fallback():
    """Verifies generate_cover_letter_chain structured output and raw LLM fallback path."""
    mock_db = AsyncMock(spec=AsyncSession)

    # 1. Test structured generation path
    mock_llm_result = CoverLetterLLMResult(
        cover_letter_markdown="# Structured Cover Letter\nDear Hiring Team...",
        highlighted_skills=["Python", "FastAPI"],
    )

    mock_llm = RunnableLambda(lambda x: mock_llm_result)
    mock_llm.with_structured_output = MagicMock(
        return_value=RunnableLambda(lambda x: mock_llm_result)
    )

    with (
        patch(
            "app.services.cover_letter.get_task_chat_model",
            new_callable=AsyncMock,
            return_value=mock_llm,
        ),
        patch(
            "app.services.cover_letter.get_prompt_template",
            new_callable=AsyncMock,
            return_value="Prompt template {company_name}",
        ),
    ):
        res = await generate_cover_letter_chain(
            db=mock_db,
            company_name="Stripe",
            job_title="Backend Engineer",
            job_description="Payment systems",
            candidate_cv="CV text",
            candidate_skills=["Python", "FastAPI"],
        )
        assert res.cover_letter_markdown == mock_llm_result.cover_letter_markdown
        assert res.highlighted_skills == ["Python", "FastAPI"]

    # 2. Test fallback raw LLM path when structured output fails
    def _raise_error(x):
        raise RuntimeError("Structured output error")

    mock_response = MagicMock()
    mock_response.content = "# Fallback Cover Letter Content"

    mock_llm_fallback = RunnableLambda(lambda x: mock_response)
    mock_llm_fallback.with_structured_output = MagicMock(
        return_value=RunnableLambda(_raise_error)
    )

    with (
        patch(
            "app.services.cover_letter.get_task_chat_model",
            new_callable=AsyncMock,
            return_value=mock_llm_fallback,
        ),
        patch(
            "app.services.cover_letter.get_prompt_template",
            new_callable=AsyncMock,
            return_value="Prompt template {company_name}",
        ),
    ):
        res_fallback = await generate_cover_letter_chain(
            db=mock_db,
            company_name="Stripe",
            job_title="Backend Engineer",
            job_description="Payment systems",
            candidate_cv="CV text",
            candidate_skills=["Python", "FastAPI"],
        )
        assert res_fallback.cover_letter_markdown == "# Fallback Cover Letter Content"
        assert res_fallback.highlighted_skills == ["Python", "FastAPI"]


@pytest.mark.docker
async def test_cover_letter_get_endpoint_not_found(db_session: AsyncSession):
    """Verifies 404 response for non-existent application cover letter GET request."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/applications/999999/cover-letter")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    app.dependency_overrides.clear()


@pytest.mark.docker
async def test_cover_letter_put_and_get_workflow(db_session: AsyncSession):
    """Verifies creating an application, retrieving initial cover letter status, and saving manual edits via PUT."""
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(name="Stripe", name_normalized="stripe", domain="stripe.com")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Backend Engineer",
        status="APPLIED",
        cover_letter_status="PENDING",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET initial status
        get_resp = await client.get(
            f"/api/v1/applications/{application.id}/cover-letter"
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["application_id"] == application.id
        assert data["cover_letter_status"] == "PENDING"
        assert data["cover_letter_markdown"] is None

        # PUT manual user edits
        edit_payload = {"content": "# Custom Cover Letter\n\nDear Stripe Team..."}
        put_resp = await client.put(
            f"/api/v1/applications/{application.id}/cover-letter",
            json=edit_payload,
        )
        assert put_resp.status_code == 200
        updated_data = put_resp.json()
        assert updated_data["cover_letter_status"] == "COMPLETED"
        assert updated_data["cover_letter_markdown"] == edit_payload["content"]

    await db_session.refresh(application)
    assert application.cover_letter_status == "COMPLETED"
    assert application.cover_letter_markdown == edit_payload["content"]
    app.dependency_overrides.clear()


@pytest.mark.docker
async def test_cover_letter_generate_endpoint_queues_task(db_session: AsyncSession):
    """Verifies POST /generate queues background generation task and sets status to PENDING."""
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(name="Linear", name_normalized="linear", domain="linear.app")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Staff Systems Engineer",
        status="APPLIED",
        cover_letter_status="PENDING",
    )
    db_session.add(application)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "app.routers.cover_letters.process_evaluation_task", new_callable=AsyncMock
        ) as mock_worker:
            gen_resp = await client.post(
                f"/api/v1/applications/{application.id}/cover-letter/generate",
                json={
                    "custom_instructions": "Focus on offline sync",
                    "tone": "enthusiastic",
                },
            )
            assert gen_resp.status_code == 202
            body = gen_resp.json()
            assert body["application_id"] == application.id
            assert body["cover_letter_status"] == "PENDING"
            mock_worker.assert_called_once()

    app.dependency_overrides.clear()


@pytest.mark.docker
async def test_cover_letter_worker_execution_with_mocked_llm(db_session: AsyncSession):
    """
    Verifies full background worker execution for COVER_LETTER_GENERATION task:
    - Status transitions from PENDING -> GENERATING -> COMPLETED
    - Persists markdown content and highlighted skills to database.
    """
    company = CompanyModel(name="Figma", name_normalized="figma", domain="figma.com")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Principal Platform Engineer",
        status="APPLIED",
        cover_letter_status="PENDING",
    )
    db_session.add(application)

    cv = CandidateCVModel(
        raw_text="Candidate Alex Morgan...",
        anonymized_text="Alex Morgan - Staff Engineer",
        extracted_skills=["Rust", "Go", "Kubernetes", "PostgreSQL"],
        is_active=True,
    )
    db_session.add(cv)
    await db_session.commit()

    task = IntakeEvaluationTaskModel(
        task_type="COVER_LETTER_GENERATION",
        status="QUEUED",
        stage="QUEUED",
        title_hint="Cover Letter - Figma",
        result_json={"application_id": application.id},
    )
    db_session.add(task)
    await db_session.commit()

    mock_llm_result = CoverLetterLLMResult(
        cover_letter_markdown="# Cover Letter for Figma\n\nDear Figma Engineering Team...",
        highlighted_skills=["Rust", "Kubernetes", "Distributed Systems"],
    )

    with patch(
        "app.services.cover_letter.generate_cover_letter_chain",
        new_callable=AsyncMock,
        return_value=mock_llm_result,
    ):
        await process_evaluation_task(task.id, db=db_session)

    await db_session.refresh(task)
    await db_session.refresh(application)

    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert application.cover_letter_status == "COMPLETED"
    assert application.cover_letter_markdown == mock_llm_result.cover_letter_markdown
    assert "Rust" in application.cover_letter_highlighted_skills
