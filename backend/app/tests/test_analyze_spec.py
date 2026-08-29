from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.applications import ApplicationAnalyzeSpecRequest
from app.schemas.llm import ExtractedJobSpec, JobAssessmentResult
from app.services.evaluation_worker import _execute_evaluation_steps


def test_analyze_spec_schema():
    req = ApplicationAnalyzeSpecRequest(
        job_url="https://example.com/job/123",
        raw_description="We are looking for a Python backend engineer.",
    )
    assert req.job_url == "https://example.com/job/123"
    assert "Python" in req.raw_description


@pytest.mark.asyncio
async def test_analyze_spec_endpoint_validation_and_enqueue(db_session):
    # 1. Create company and application
    company = CompanyModel(
        name="Initech Spec Test",
        name_normalized="initech spec test",
        domain="initech.com",
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Backend Engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test 404 for non-existent application
        resp_404 = await client.post(
            "/api/v1/applications/999999/analyze-spec",
            json={"job_url": "https://example.com/job"},
        )
        assert resp_404.status_code == 404

        # Test 400 when no url and no raw_description
        resp_400 = await client.post(
            f"/api/v1/applications/{application.id}/analyze-spec",
            json={"job_url": "", "raw_description": ""},
        )
        assert resp_400.status_code == 400

        # Test successful enqueue
        with patch("app.routers.applications.process_evaluation_task") as mock_process:
            resp = await client.post(
                f"/api/v1/applications/{application.id}/analyze-spec",
                json={
                    "job_url": "https://initech.com/jobs/senior-backend",
                    "raw_description": "Job description text for Initech.",
                },
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["task_type"] == "APPLICATION_ASSESSMENT"
            assert data["status"] == "QUEUED"
            assert data["result_json"]["target_application_id"] == application.id
            assert data["result_json"]["is_direct_application"] is True
            mock_process.assert_called_once()

            task_id = data["id"]

            # Test GET /api/v1/intake/evaluations/{task_id}
            get_task_resp = await client.get(f"/api/v1/intake/evaluations/{task_id}")
            assert get_task_resp.status_code == 200
            task_data = get_task_resp.json()
            assert task_data["id"] == task_id
            assert task_data["task_type"] == "APPLICATION_ASSESSMENT"


@pytest.mark.asyncio
async def test_worker_processes_application_assessment(db_session):
    company = CompanyModel(
        name="Direct Assessment Co",
        name_normalized="direct assessment co",
        domain="direct.com",
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    application = ApplicationModel(
        company_id=company.id,
        position="Staff Distributed Engineer",
        status="TECHNICAL_INTERVIEW",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    task = IntakeEvaluationTaskModel(
        task_type="APPLICATION_ASSESSMENT",
        job_url="https://direct.com/jobs/staff-eng",
        raw_text="Staff Distributed Engineer position. Responsibilities include building backend services. Requirements: 5+ years experience and technical skills.",
        title_hint="Direct Assessment Co - Staff Distributed Engineer",
        status="PROCESSING",
        stage="FETCHING",
        result_json={
            "target_application_id": application.id,
            "is_direct_application": True,
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    mock_assessment = JobAssessmentResult(
        fit_score=92,
        matching_skills=["Distributed Systems", "Python", "PostgreSQL"],
        missing_skills=[],
        seniority_fit="MATCHES",
        recommendation="APPLY_STRONGLY",
        pros=["High alignment with distributed systems"],
        cons=[],
        summary="Strong candidate match for Staff role.",
        company="Direct Assessment Co",
        position="Staff Distributed Engineer",
        salary_min=180000,
        salary_max=240000,
        currency="USD",
        location="Remote",
        work_model="Remote",
    )

    mock_spec = ExtractedJobSpec(
        company="Direct Assessment Co",
        position="Staff Distributed Engineer",
        why_hiring="Scale core data infrastructure.",
        what_you_will_build="Distributed message broker.",
        responsibilities=["Build high scale pipelines."],
        requirements=["5+ years distributed systems."],
        extracted_skills=["Distributed Systems", "Python", "PostgreSQL"],
        salary_min=180000,
        salary_max=240000,
        currency="USD",
        location_text="Remote",
        work_model="Remote",
    )

    with (
        patch(
            "app.services.evaluation_worker.extract_job_spec",
            new_callable=AsyncMock,
            return_value=mock_spec,
        ),
        patch(
            "app.services.evaluation_worker.assess_job_posting",
            new_callable=AsyncMock,
            return_value=mock_assessment,
        ),
    ):
        await _execute_evaluation_steps(task, db_session)

    # Refresh task and application
    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert task.result_json["target_application_id"] == application.id

    # Verify application was updated
    await db_session.refresh(application)
    assert application.match_analysis_payload is not None
    assert application.match_analysis_payload["fit_score"] == 92
    assert application.status == "TECHNICAL_INTERVIEW"  # Status preserved!

    # Verify JobPostingModel was created / linked
    jp_stmt = select(JobPostingModel).where(
        JobPostingModel.application_id == application.id
    )
    jp_res = await db_session.execute(jp_stmt)
    job_posting = jp_res.scalar_one_or_none()
    assert job_posting is not None
    assert job_posting.salary_min == 180000
    assert job_posting.salary_max == 240000
    assert job_posting.structured_spec is not None
    assert (
        job_posting.structured_spec["why_hiring"] == "Scale core data infrastructure."
    )


@pytest.mark.asyncio
async def test_worker_skips_keyword_check_for_user_provided_jd(db_session):
    # Test that arbitrary user-written text (which fails scraper validate_job_content keyword match)
    # is NOT blocked when raw_text is provided by user.
    company = CompanyModel(
        name="Custom Intake Co",
        name_normalized="custom intake co",
        domain="custom.com",
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    application = ApplicationModel(
        company_id=company.id,
        position="Founding Engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    # Arbitrary user notes without standard keywords (e.g. no "responsibilities", "requirements", etc.)
    user_jd_text = "Looking for a hacker to build cool stuff with us from day one."

    task = IntakeEvaluationTaskModel(
        task_type="APPLICATION_ASSESSMENT",
        job_url=None,
        raw_text=user_jd_text,
        title_hint="Custom Intake Co - Founding Engineer",
        status="PROCESSING",
        stage="FETCHING",
        result_json={
            "target_application_id": application.id,
            "is_direct_application": True,
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    mock_assessment = JobAssessmentResult(
        fit_score=88,
        matching_skills=["Fast execution", "Full stack"],
        missing_skills=[],
        seniority_fit="MATCHES",
        recommendation="APPLY",
        pros=["Startup speed"],
        cons=[],
        summary="Good candidate fit.",
        company="Custom Intake Co",
        position="Founding Engineer",
    )

    mock_spec = ExtractedJobSpec(
        company="Custom Intake Co",
        position="Founding Engineer",
        why_hiring="Early stage MVP build.",
        what_you_will_build="Core prototype.",
        responsibilities=["Ship fast."],
        requirements=["Self-directed builder."],
        extracted_skills=["Full stack"],
    )

    with (
        patch(
            "app.services.evaluation_worker.extract_job_spec",
            new_callable=AsyncMock,
            return_value=mock_spec,
        ),
        patch(
            "app.services.evaluation_worker.assess_job_posting",
            new_callable=AsyncMock,
            return_value=mock_assessment,
        ),
    ):
        await _execute_evaluation_steps(task, db_session)

    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    assert task.error_message is None
