import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_queue import ProviderConcurrencyManager
from app.core.database import get_db
from app.main import app
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.llm import JobAssessmentResult
from app.services.evaluation_worker import process_evaluation_task


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
            missing_skills=[],
            pros=["Excellent compensation", "Fully remote"],
            cons=[],
            summary="Strong match for backend architecture.",
        )

        with patch("app.services.evaluation_worker.assess_job_posting", new=AsyncMock(return_value=mock_assessment)):
            with patch("app.services.evaluation_worker.AsyncSessionLocal", return_value=db_session):
                await process_evaluation_task(task_id)

        # 5. Verify task is marked COMPLETED in database
        updated_task = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert updated_task is not None
        assert updated_task.status == "COMPLETED"
        assert updated_task.stage == "COMPLETE"
        assert updated_task.result_json["company"] == "Stripe"
        assert updated_task.result_json["fit_score"] == 95

        # 6. Delete evaluation task via DELETE /api/v1/intake/evaluations/{task_id}
        del_res = await ac.delete(f"/api/v1/intake/evaluations/{task_id}")
        assert del_res.status_code == 200

        deleted_check = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert deleted_check is None

    app.dependency_overrides.clear()
