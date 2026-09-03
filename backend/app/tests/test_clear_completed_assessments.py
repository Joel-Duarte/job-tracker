import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel
from app.models.intake_tasks import IntakeEvaluationTaskModel


@pytest.mark.asyncio
async def test_clear_completed_preserves_job_assessment(db_session: AsyncSession):
    """Ensure clear-completed deletes worker tasks but strictly preserves JOB_ASSESSMENT tasks."""
    app.dependency_overrides[get_db] = lambda: db_session

    # 1. Create a worker task (e.g. COMPANY_RESEARCH) that is completed
    worker_task = IntakeEvaluationTaskModel(
        task_type="COMPANY_RESEARCH",
        title_hint="Acme Corp",
        status="COMPLETED",
        stage="COMPLETED",
    )
    # 2. Create a JOB_ASSESSMENT task that is completed
    assessment_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="Acme Corp - Senior Engineer",
        status="COMPLETED",
        stage="COMPLETE",
    )
    db_session.add(worker_task)
    db_session.add(assessment_task)
    await db_session.commit()
    await db_session.refresh(worker_task)
    await db_session.refresh(assessment_task)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/intake/evaluations/clear-completed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    # Worker task should be deleted
    w_check = await db_session.get(IntakeEvaluationTaskModel, worker_task.id)
    assert w_check is None

    # Assessment task MUST be preserved
    a_check = await db_session.get(IntakeEvaluationTaskModel, assessment_task.id)
    assert a_check is not None
    assert a_check.id == assessment_task.id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_assessment_task_archives_application(db_session: AsyncSession):
    """Ensure deleting a job assessment task transitions linked assessment application to ARCHIVED."""
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(name="TestCorp", name_normalized="testcorp")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="AI Engineer",
        position_normalized="ai engineer",
        status="ASSESSMENT",
    )
    db_session.add(application)
    await db_session.flush()

    task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="TestCorp - AI Engineer",
        status="COMPLETED",
        stage="COMPLETE",
        result_json={"application_id": application.id},
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/api/v1/intake/evaluations/{task.id}")
        assert resp.status_code == 200

    # Task should be deleted
    t_check = await db_session.get(IntakeEvaluationTaskModel, task.id)
    assert t_check is None

    # Application should be ARCHIVED
    await db_session.refresh(application)
    assert application.status == "ARCHIVED"

    app.dependency_overrides.clear()
