import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.models.intake_tasks import IntakeEvaluationTaskModel


@pytest.mark.asyncio
async def test_list_assessments_from_persistent_applications(db_session: AsyncSession):
    """Ensure GET /api/v1/intake/assessments retrieves applications in ASSESSMENT status with full payloads."""
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(
        name="PersistentCorp",
        name_normalized="persistentcorp",
        domain="persistent.io",
    )
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Principal AI Architect",
        position_normalized="principal ai architect",
        status="ASSESSMENT",
        job_url="https://persistent.io/jobs/123",
        match_analysis_payload={
            "fit_score": 88,
            "matching_skills": ["Python", "LangGraph"],
            "missing_skills": ["Rust"],
        },
    )
    db_session.add(application)
    await db_session.flush()

    posting = JobPostingModel(
        application_id=application.id,
        job_url="https://persistent.io/jobs/123",
        description_markdown="# Great Role\nExciting challenges.",
        salary_min=150000,
        salary_max=200000,
        currency="USD",
        work_model="Remote",
    )
    db_session.add(posting)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/intake/assessments")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

        match = next((item for item in data if item["id"] == application.id), None)
        assert match is not None
        assert match["title_hint"] == "PersistentCorp - Principal AI Architect"
        assert match["task_type"] == "JOB_ASSESSMENT"
        assert match["status"] == "COMPLETED"
        assert match["job_url"] == "https://persistent.io/jobs/123"
        assert "Great Role" in match["raw_text"]
        assert match["result_json"]["fit_score"] == 88
        assert match["result_json"]["salary_min"] == 150000
        assert match["result_json"]["company_domain"] == "persistent.io"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_assessments_survive_clear_completed_evaluations(
    db_session: AsyncSession,
):
    """Ensure clearing completed evaluation tasks never removes persistent assessments."""
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(name="RobustTech", name_normalized="robusttech")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Staff Engineer",
        position_normalized="senior staff engineer",
        status="ASSESSMENT",
        match_analysis_payload={"fit_score": 75},
    )
    db_session.add(application)

    # Add a worker task in the queue and an assessment task
    worker_task = IntakeEvaluationTaskModel(
        task_type="COMPANY_RESEARCH",
        title_hint="RobustTech",
        status="COMPLETED",
        stage="COMPLETED",
    )
    db_session.add(worker_task)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Clear completed evaluations from the queue
        clear_resp = await client.post("/api/v1/intake/evaluations/clear-completed")
        assert clear_resp.status_code == 200

        # 2. Query assessments list - MUST still contain the assessment
        assessments_resp = await client.get("/api/v1/intake/assessments")
        assert assessments_resp.status_code == 200
        data = assessments_resp.json()
        assert any(item["id"] == application.id for item in data)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dismiss_assessment_archives_application(db_session: AsyncSession):
    """Ensure DELETE /api/v1/intake/assessments/{app_id} archives the application."""
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(name="DismissCorp", name_normalized="dismisscorp")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Lead Data Engineer",
        position_normalized="lead data engineer",
        status="ASSESSMENT",
    )
    db_session.add(application)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/api/v1/intake/assessments/{application.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    await db_session.refresh(application)
    assert application.status == "ARCHIVED"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_archived_assessment_remains_listed(db_session: AsyncSession):
    """Archived assessment dossiers remain available independently of queue tasks."""
    app.dependency_overrides[get_db] = lambda: db_session
    company = CompanyModel(name="ArchivedCorp", name_normalized="archivedcorp")
    db_session.add(company)
    await db_session.flush()
    application = ApplicationModel(
        company_id=company.id,
        position="Archived Assessment Role",
        position_normalized="archived assessment role",
        status="ARCHIVED",
        is_assessment=True,
        match_analysis_payload={"fit_score": 61},
    )
    db_session.add(application)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/intake/assessments")
        assert response.status_code == 200
        archived = next(
            item for item in response.json() if item["id"] == application.id
        )
        assert archived["result_json"]["assessment_archived"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_clear_completed_removes_assessment_task_but_keeps_dossier(
    db_session: AsyncSession,
):
    """Clearing the queue removes completed worker rows without removing the dossier."""
    app.dependency_overrides[get_db] = lambda: db_session
    company = CompanyModel(name="QueueCorp", name_normalized="queuecorp")
    db_session.add(company)
    await db_session.flush()
    application = ApplicationModel(
        company_id=company.id,
        position="Queue Role",
        position_normalized="queue role",
        status="ASSESSMENT",
        is_assessment=True,
        match_analysis_payload={"fit_score": 72},
    )
    db_session.add(application)
    await db_session.flush()
    task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="QueueCorp",
        status="COMPLETED",
        stage="COMPLETE",
        result_json={"application_id": application.id},
    )
    db_session.add(task)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/intake/evaluations/clear-completed")
        assert response.status_code == 200
        assert response.json()["cleared_count"] == 1

    await db_session.refresh(application)
    assert application.status == "ASSESSMENT"
    assert await db_session.get(IntakeEvaluationTaskModel, task.id) is None
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanently_delete_assessment_in_ready_status(db_session: AsyncSession):
    """Ensure ready assessments (status='ASSESSMENT') can be permanently deleted."""
    app.dependency_overrides[get_db] = lambda: db_session
    company = CompanyModel(name="DeleteReadyCorp", name_normalized="deletereadycorp")
    db_session.add(company)
    await db_session.flush()
    application = ApplicationModel(
        company_id=company.id,
        position="Ready Role",
        position_normalized="ready role",
        status="ASSESSMENT",
        is_assessment=True,
    )
    db_session.add(application)
    await db_session.flush()

    task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="DeleteReadyCorp",
        status="COMPLETED",
        stage="COMPLETE",
        result_json={"application_id": application.id},
    )
    db_session.add(task)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete(
            f"/api/v1/intake/assessments/{application.id}/permanent"
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    assert await db_session.get(ApplicationModel, application.id) is None
    assert await db_session.get(IntakeEvaluationTaskModel, task.id) is None
    app.dependency_overrides.clear()
