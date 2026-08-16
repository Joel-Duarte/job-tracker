from unittest.mock import AsyncMock, patch

import pytest
from app.core.ai_queue import ProviderConcurrencyManager
from app.core.database import get_db
from app.main import app
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.applications import (
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel
from app.schemas.llm import ExtractedJobSpec, JobAssessmentResult
from app.services.evaluation_worker import process_evaluation_task
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_provider_concurrency_manager():
    mgr = ProviderConcurrencyManager()
    sem1 = await mgr.get_semaphore(provider_id=1, max_concurrency=1)
    assert sem1._value == 1

    sem2 = await mgr.get_semaphore(provider_id=2, max_concurrency=5)
    assert sem2._value == 5

    # Re-requesting with same concurrency returns existing semaphore
    sem1_again = await mgr.get_semaphore(provider_id=1, max_concurrency=1)
    assert sem1 is sem1_again

    # Dynamic update
    sem1_updated = await mgr.get_semaphore(provider_id=1, max_concurrency=3)
    assert sem1_updated._value == 3


@pytest.mark.asyncio
async def test_intake_queue_endpoints_and_worker(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create a Provider with max_concurrency=1
        provider = AIProviderModel(
            name="LM Studio Local",
            provider_type="openai",
            base_url="http://192.168.1.187:1234/v1",
            max_concurrency=1,
            is_active=True,
        )
        db_session.add(provider)
        await db_session.flush()

        binding = AITaskBindingModel(
            task_type="EXTRACTION",
            provider_id=provider.id,
            model_name="qwen3.5-4b",
            temperature=0.2,
            is_active=True,
        )
        db_session.add(binding)
        await db_session.commit()

        # 2. Enqueue Assessment via POST /api/v1/intake/enqueue-assessment
        with patch("fastapi.BackgroundTasks.add_task"):
            enqueue_res = await ac.post(
                "/api/v1/intake/enqueue-assessment",
                json={
                    "text": "Stripe - Staff Backend Engineer\nLocation: Remote\nSalary: $200k - $250k\nRequirements: Python, Distributed Systems, SQL",
                    "title_hint": "Stripe - Staff Backend Engineer",
                },
            )
        assert enqueue_res.status_code == 202
        task_data = enqueue_res.json()
        task_id = task_data["id"]
        assert task_data["status"] == "QUEUED"

        # 3. List Evaluations via GET /api/v1/intake/evaluations
        list_res = await ac.get("/api/v1/intake/evaluations")
        assert list_res.status_code == 200
        evals = list_res.json()
        assert len(evals) >= 1
        assert any(e["id"] == task_id for e in evals)

        # 4. Mock the LLM assessment call and run the worker
        mock_assessment = JobAssessmentResult(
            company="Stripe",
            position="Staff Backend Engineer",
            location="Remote",
            work_model="Remote",
            salary_min=200000.0,
            salary_max=250000.0,
            currency="USD",
            recommendation="APPLY_STRONGLY",
            fit_score=95,
            matching_skills=["Python", "Distributed Systems", "SQL"],
            pros=["Excellent compensation", "Fully remote"],
            cons=[],
            summary="Strong match for backend architecture.",
        )

        mock_job_spec = ExtractedJobSpec(
            job_found=True,
            company="Stripe",
            position="Staff Backend Engineer",
            location_work_type="Remote",
            salary_benefits="$200k - $250k",
            core_responsibilities="Backend systems",
            requirements_qualifications="Python, SQL",
            ats_keywords=["Python", "SQL"],
        )

        with (
            patch(
                "app.services.evaluation_worker.extract_job_spec",
                new=AsyncMock(return_value=mock_job_spec),
            ),
            patch(
                "app.services.evaluation_worker.assess_job_posting",
                new=AsyncMock(return_value=mock_assessment),
            ),
        ):
            await process_evaluation_task(task_id, db=db_session)

        # 5. Verify task is marked COMPLETED in database
        updated_task = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert updated_task is not None
        assert updated_task.status == "COMPLETED"
        assert updated_task.stage == "COMPLETE"
        assert updated_task.result_json["company"] == "Stripe"
        assert updated_task.result_json["fit_score"] == 95
        assert updated_task.result_json["application_id"] is not None

        # Verify Application, Company, JobPosting, and Event are persisted
        app_id = updated_task.result_json["application_id"]
        app_res = await db_session.get(ApplicationModel, app_id)
        assert app_res is not None
        assert app_res.status == "ASSESSMENT"
        assert app_res.position == "Staff Backend Engineer"

        jp_stmt = select(JobPostingModel).where(
            JobPostingModel.application_id == app_id
        )
        jp_res = await db_session.execute(jp_stmt)
        jp = jp_res.scalar_one_or_none()
        assert jp is not None
        assert jp.salary_min == 200000.0

        # 6. Delete evaluation task via DELETE /api/v1/intake/evaluations/{task_id}
        del_res = await ac.delete(f"/api/v1/intake/evaluations/{task_id}")
        assert del_res.status_code == 200

        deleted_check = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert deleted_check is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_intake_queue_duplicate_staging_and_resolution(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. First lead creates Application in ASSESSMENT
        comp = CompanyModel(name="GitHub", name_normalized="github")
        db_session.add(comp)
        await db_session.flush()

        app_orig = ApplicationModel(
            company_id=comp.id,
            position="Staff AI Engineer",
            position_normalized="staff ai engineer",
            status="ASSESSMENT",
        )
        db_session.add(app_orig)
        await db_session.commit()

        # 2. Enqueue duplicate lead
        with patch("fastapi.BackgroundTasks.add_task"):
            enqueue_res = await ac.post(
                "/api/v1/intake/enqueue-assessment",
                json={
                    "text": "GitHub - Staff AI Engineer\nLocation: Remote\nRequirements: Python, LLM",
                    "title_hint": "GitHub - Staff AI Engineer",
                },
            )
        assert enqueue_res.status_code == 202
        task_id = enqueue_res.json()["id"]

        mock_assessment = JobAssessmentResult(
            company="GitHub",
            position="Staff AI Engineer",
            location="Remote",
            work_model="Remote",
            recommendation="APPLY_STRONGLY",
            fit_score=92,
            matching_skills=["Python", "LLM"],
            missing_skills=[],
            pros=["Great culture"],
            cons=[],
            summary="Strong candidate match for AI role.",
        )

        mock_job_spec = ExtractedJobSpec(
            job_found=True,
            company="GitHub",
            position="Staff AI Engineer",
            location_work_type="Remote",
            salary_benefits="Competitive",
            core_responsibilities="AI platform engineering",
            requirements_qualifications="Python, LLM",
            ats_keywords=["Python", "LLM"],
        )

        with (
            patch(
                "app.services.evaluation_worker.extract_job_spec",
                new=AsyncMock(return_value=mock_job_spec),
            ),
            patch(
                "app.services.evaluation_worker.assess_job_posting",
                new=AsyncMock(return_value=mock_assessment),
            ),
        ):
            await process_evaluation_task(task_id, db=db_session)

        # 3. Verify task stage is STAGED_DUPLICATE
        dup_task = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert dup_task.stage == "STAGED_DUPLICATE"
        assert dup_task.result_json["is_duplicate"] is True
        staging_id = dup_task.result_json["staging_item_id"]
        assert staging_id is not None

        # 4. Verify Staging Item exists
        staging_item = await db_session.get(StagingItemModel, staging_id)
        assert staging_item is not None
        assert staging_item.match_reason == "DUPLICATE_APPLICATION_FOUND"
        assert staging_item.status == "PENDING"

        # 5. Resolve as NEW application (e.g. re-application)
        resolve_res = await ac.post(
            f"/api/v1/staging/{staging_id}/resolve",
            json={
                "company_name": "GitHub",
                "position": "Staff AI Engineer",
                "status": "ASSESSMENT",
                "create_new": True,
            },
        )
        assert resolve_res.status_code == 200
        data = resolve_res.json()
        new_app_id = data["application_id"]
        assert new_app_id != app_orig.id

        # Verify two distinct applications now exist
        all_apps = (
            (
                await db_session.execute(
                    select(ApplicationModel).where(
                        ApplicationModel.company_id == comp.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(all_apps) == 2

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retry_evaluation_task(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    task = IntakeEvaluationTaskModel(
        job_url="https://example.com/failed-job",
        raw_text="Some text",
        title_hint="Failed Task",
        status="FAILED",
        stage="FAILED",
        error_message="Network timeout",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("app.routers.intake.process_evaluation_task") as mock_proc:
            res = await ac.post(f"/api/v1/intake/evaluations/{task.id}/retry")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == task.id
            assert data["status"] == "QUEUED"
            assert data["error_message"] is None

    app.dependency_overrides.clear()
