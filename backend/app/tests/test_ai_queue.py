import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.llm import ExtractedJobSpec, JobAssessmentResult
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
            workplace_type="Remote",
            compensation_text="$200k - $250k",
            responsibilities=["Backend systems"],
            requirements=["Python, SQL"],
            extracted_skills=["Python", "SQL"],
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
async def test_intake_queue_unrestricted_submissions(db_session: AsyncSession):
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

        # 2. Enqueue new lead for the same company and position
        with patch("fastapi.BackgroundTasks.add_task"):
            enqueue_res = await ac.post(
                "/api/v1/intake/enqueue-assessment",
                json={
                    "text": "GitHub - Staff AI Engineer\nLocation: Remote\nResponsibilities: Build AI systems\nRequirements: Python, LLM",
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
            workplace_type="Remote",
            compensation_text="Competitive",
            responsibilities=["AI platform engineering"],
            requirements=["Python, LLM"],
            extracted_skills=["Python", "LLM"],
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

        # 3. Verify task stage is COMPLETE and creates a fresh application unconditionally
        new_task = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert new_task.status == "COMPLETED"
        assert new_task.stage == "COMPLETE"
        assert new_task.result_json["is_duplicate"] is False
        new_app_id = new_task.result_json["application_id"]
        assert new_app_id is not None
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
async def test_fix_jd_evaluation_task(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    task = IntakeEvaluationTaskModel(
        job_url="https://example.com/non-job-page",
        raw_text="",
        title_hint="Non Job Page",
        status="FAILED",
        stage="FAILED",
        error_message="INVALID_JOB_CONTENT: Scraped page does not appear to be a job description.",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch("app.routers.intake.process_evaluation_task"):
            res = await ac.post(
                f"/api/v1/intake/evaluations/{task.id}/fix-jd",
                json={
                    "raw_text": "Company: Acme Corp\nPosition: Senior Software Engineer\nRequirements: Python, Postgres, FastAPI\nResponsibilities: Build scalable backend systems\nSalary: $150,000",
                    "job_url": "https://example.com/fixed-job",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == task.id
            assert data["status"] == "QUEUED"
            assert data["stage"] == "EXTRACTING"
            assert data["error_message"] is None
            assert data["job_url"] == "https://example.com/fixed-job"
            assert "Requirements: Python" in data["raw_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cancel_evaluation_task(db_session: AsyncSession):
    from app.core.ai_queue import register_running_task, unregister_running_task

    app.dependency_overrides[get_db] = lambda: db_session

    task = IntakeEvaluationTaskModel(
        job_url="https://example.com/running-job",
        raw_text="Job text",
        title_hint="Running Task",
        status="PROCESSING",
        stage="FETCHING",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Simulate an active background task
    async def _dummy_worker():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    dummy_task = asyncio.create_task(_dummy_worker())
    register_running_task(task.id, dummy_task)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.post(f"/api/v1/intake/evaluations/{task.id}/cancel")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == task.id
            assert data["status"] == "CANCELLED"
            assert data["stage"] == "CANCELLED"
            assert data["error_message"] == "Task stopped by user"

            # Verify in-flight task received cancellation signal
            assert dummy_task.cancelled() or dummy_task.cancelling() > 0

            # Verify task state in database
            updated_task = await db_session.get(IntakeEvaluationTaskModel, task.id)
            assert updated_task.status == "CANCELLED"
            assert updated_task.stage == "CANCELLED"
            assert updated_task.error_message == "Task stopped by user"
    finally:
        unregister_running_task(task.id)
        if not dummy_task.done():
            dummy_task.cancel()
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
        with patch("app.routers.intake.process_evaluation_task"):
            res = await ac.post(f"/api/v1/intake/evaluations/{task.id}/retry")
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == task.id
            assert data["status"] == "QUEUED"
            assert data["error_message"] is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bulk_retry_and_delete_evaluation_tasks(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    # Create tasks with mixed statuses
    t1_failed = IntakeEvaluationTaskModel(
        title_hint="Task 1 Failed",
        status="FAILED",
        stage="FAILED",
        error_message="Timeout",
    )
    t2_completed = IntakeEvaluationTaskModel(
        title_hint="Task 2 Completed", status="COMPLETED", stage="COMPLETE"
    )
    t3_running = IntakeEvaluationTaskModel(
        title_hint="Task 3 Running", status="PROCESSING", stage="FETCHING"
    )
    t4_cancelled = IntakeEvaluationTaskModel(
        title_hint="Task 4 Cancelled", status="CANCELLED", stage="CANCELLED"
    )

    db_session.add_all([t1_failed, t2_completed, t3_running, t4_cancelled])
    await db_session.commit()
    for t in [t1_failed, t2_completed, t3_running, t4_cancelled]:
        await db_session.refresh(t)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Bulk Retry mixed tasks
        with patch("app.routers.intake.process_evaluation_task"):
            retry_res = await ac.post(
                "/api/v1/intake/evaluations/bulk-retry",
                json={
                    "task_ids": [
                        t1_failed.id,
                        t2_completed.id,
                        t3_running.id,
                        t4_cancelled.id,
                        999999,
                    ]
                },
            )
            assert retry_res.status_code == 200
            retry_data = retry_res.json()
            assert retry_data["affected_count"] == 2  # t1_failed and t4_cancelled
            assert retry_data["skipped_count"] == 3  # t2_completed, t3_running, 999999
            assert 999999 in retry_data["unhandled_ids"]

            # Verify database states
            updated_t1 = await db_session.get(IntakeEvaluationTaskModel, t1_failed.id)
            assert updated_t1.status == "QUEUED"
            assert updated_t1.error_message is None

            updated_t2 = await db_session.get(
                IntakeEvaluationTaskModel, t2_completed.id
            )
            assert updated_t2.status == "COMPLETED"

        # 2. Bulk Delete mixed tasks (t3_running should be protected and skipped)
        del_res = await ac.post(
            "/api/v1/intake/evaluations/bulk-delete",
            json={
                "task_ids": [
                    t1_failed.id,
                    t2_completed.id,
                    t3_running.id,
                    t4_cancelled.id,
                    888888,
                ]
            },
        )
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert (
            del_data["deleted_count"] == 3
        )  # t1_failed (now QUEUED), t2_completed, t4_cancelled (now QUEUED)
        assert del_data["skipped_count"] == 2  # t3_running, 888888
        assert t3_running.id in del_data["unhandled_ids"]

        # Verify running task still exists
        running_check = await db_session.get(IntakeEvaluationTaskModel, t3_running.id)
        assert running_check is not None
        assert running_check.status == "PROCESSING"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retry_endpoint_guards_active_and_completed_and_preserves_checkpoint(
    db_session: AsyncSession,
):
    app.dependency_overrides[get_db] = lambda: db_session

    processing_task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_REVIEW",
        title_hint="Processing SD Review",
        status="PROCESSING",
        stage="ANALYZING",
    )
    completed_task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_EVALUATION",
        title_hint="Completed SD Eval",
        status="COMPLETED",
        stage="COMPLETE",
    )
    checkpointed_failed = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_REVIEW",
        title_hint="Failed at SAVING",
        status="FAILED",
        stage="FAILED",
        error_message="DB blip during save",
        result_json={
            "session_id": 77,
            "_checkpoint": {
                "completed_steps": ["PREPARING", "ANALYZING"],
                "review_result": {"diagram_version": 1},
                "attempt_count": 1,
            },
        },
    )
    db_session.add_all([processing_task, completed_task, checkpointed_failed])
    await db_session.commit()
    for t in (processing_task, completed_task, checkpointed_failed):
        await db_session.refresh(t)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r_proc = await ac.post(
                f"/api/v1/intake/evaluations/{processing_task.id}/retry"
            )
            assert r_proc.status_code == 409

            r_comp = await ac.post(
                f"/api/v1/intake/evaluations/{completed_task.id}/retry"
            )
            assert r_comp.status_code == 409

            with patch("app.routers.intake.process_evaluation_task"):
                r_retry = await ac.post(
                    f"/api/v1/intake/evaluations/{checkpointed_failed.id}/retry"
                )
            assert r_retry.status_code == 200
            retried = r_retry.json()
            assert retried["status"] == "QUEUED"
            assert retried["stage"] == "SAVING"
            cp = retried["result_json"]["_checkpoint"]
            assert cp["completed_steps"] == ["PREPARING", "ANALYZING"]
            assert cp["manual_retry_count"] == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_startup_recovery_duplicate_claim_and_graceful_shutdown(
    db_session: AsyncSession,
):
    from datetime import UTC, datetime, timedelta

    from app.core.ai_queue import set_shutting_down
    from app.services.evaluation_worker import (
        recover_and_dispatch_queue_tasks,
    )

    # Scenario B: stale/crashed PROCESSING task with partial checkpoint
    stale_time = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
    crashed_task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_REVIEW",
        title_hint="Crashed mid-review",
        status="PROCESSING",
        stage="ANALYZING",
        result_json={
            "session_id": 12,
            "_checkpoint": {
                "completed_steps": ["PREPARING"],
                "last_activity_at": stale_time,
                "worker_host": "crashed-host",
            },
        },
    )
    db_session.add(crashed_task)
    await db_session.commit()
    await db_session.refresh(crashed_task)

    # Prevent real background execution in test while inspecting dispatch behavior
    spawned_ids: list[int] = []

    async def fake_process(task_id: int, db=None):
        spawned_ids.append(task_id)

    with patch(
        "app.services.evaluation_worker.process_evaluation_task",
        side_effect=fake_process,
    ):
        summary = await recover_and_dispatch_queue_tasks(
            startup=True, stale_after_seconds=300
        )
        # Allow scheduled asyncio tasks to run one event-loop turn
        await asyncio.sleep(0.05)

    assert summary["recovered_count"] == 1
    assert crashed_task.id in summary["dispatched_task_ids"]
    assert crashed_task.id in spawned_ids

    await db_session.refresh(crashed_task)
    assert crashed_task.status == "QUEUED"
    assert crashed_task.stage == "ANALYZING"
    assert crashed_task.result_json["_checkpoint"]["completed_steps"] == ["PREPARING"]
    assert crashed_task.result_json["_checkpoint"]["recovery_count"] == 1

    # Scenario D: Duplicate claim / concurrent worker guard & completed idempotency
    exec_count = 0

    async def counting_steps(task, db, **kwargs):
        nonlocal exec_count
        exec_count += 1
        await asyncio.sleep(0.05)
        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        await db.commit()

    dup_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="Concurrent Claim Guard",
        status="QUEUED",
        stage="QUEUED",
    )
    db_session.add(dup_task)
    await db_session.commit()
    await db_session.refresh(dup_task)

    with patch(
        "app.services.evaluation_worker._execute_evaluation_steps",
        side_effect=counting_steps,
    ):
        await asyncio.gather(
            process_evaluation_task(dup_task.id),
            process_evaluation_task(dup_task.id),
        )
        # Calling again once COMPLETED must be an immediate no-op
        await process_evaluation_task(dup_task.id)

    assert exec_count == 1
    await db_session.refresh(dup_task)
    assert dup_task.status == "COMPLETED"

    # Scenario E: Graceful shutdown re-queues interrupted task preserving _checkpoint
    shutdown_task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_EVALUATION",
        title_hint="Shutdown Interrupt Task",
        status="QUEUED",
        stage="QUEUED",
        result_json={
            "session_id": 55,
            "_checkpoint": {"completed_steps": ["PREPARING"]},
        },
    )
    db_session.add(shutdown_task)
    await db_session.commit()
    await db_session.refresh(shutdown_task)

    started_event = asyncio.Event()

    async def slow_eval_steps(task, db, **kwargs):
        started_event.set()
        await asyncio.sleep(10.0)

    try:
        with patch(
            "app.services.evaluation_worker._execute_evaluation_steps",
            side_effect=slow_eval_steps,
        ):
            worker = asyncio.create_task(process_evaluation_task(shutdown_task.id))
            await started_event.wait()
            set_shutting_down(True)
            worker.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker
    finally:
        set_shutting_down(False)

    await db_session.refresh(shutdown_task)
    assert shutdown_task.status == "QUEUED"
    assert shutdown_task.result_json["_checkpoint"]["completed_steps"] == ["PREPARING"]
    assert shutdown_task.result_json["_checkpoint"].get("interrupted_by_shutdown_at")


@pytest.mark.asyncio
async def test_transient_retry_vs_permanent_error_policy():
    from app.services import evaluation_worker as ew

    task = IntakeEvaluationTaskModel(
        id=909,
        task_type="SYSTEM_DESIGN_REVIEW",
        status="PROCESSING",
        stage="ANALYZING",
        result_json={"_checkpoint": {}},
    )

    mock_exec_res = AsyncMock()
    mock_exec_res.scalar_one_or_none = lambda: "PROCESSING"
    mock_exec_res.first = lambda: ("PROCESSING", {"_checkpoint": {}})
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_exec_res)
    mock_db.get = AsyncMock(return_value=task)

    calls = 0

    async def flaky_then_ok():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise TimeoutError("429 upstream timed out")
        return {"ok": True}

    with patch.object(ew, "_TRANSIENT_RETRY_DELAYS", (0.0, 0.0)):
        out = await ew._run_with_transient_retry(
            909, "ANALYZING", flaky_then_ok, task, mock_db
        )
    assert out == {"ok": True}
    assert calls == 2

    perm_calls = 0

    async def permanent_validation_err():
        nonlocal perm_calls
        perm_calls += 1
        raise ValueError("Invalid rubric schema output")

    with (
        patch.object(ew, "_TRANSIENT_RETRY_DELAYS", (0.0, 0.0)),
        pytest.raises(ValueError, match="Invalid rubric schema output"),
    ):
        await ew._run_with_transient_retry(
            909, "ANALYZING", permanent_validation_err, task, mock_db
        )
    assert perm_calls == 1


@pytest.mark.asyncio
async def test_worker_instance_id_and_lease_renewal_ownership(db_session: AsyncSession):
    from datetime import UTC, datetime, timedelta

    from app.core.ai_queue import get_worker_instance_id
    from app.services.evaluation_worker import renew_task_lease

    wid = get_worker_instance_id()
    assert wid and wid.count(":") >= 2
    assert wid == get_worker_instance_id()

    old_exp = (datetime.now(UTC) + timedelta(seconds=10)).isoformat()
    task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_REVIEW",
        title_hint="Lease Renewal Test",
        status="PROCESSING",
        stage="ANALYZING",
        result_json={
            "_checkpoint": {
                "lease_owner": "worker-owner-1",
                "lease_expires_at": old_exp,
            }
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Non-owner cannot renew
    assert await renew_task_lease(task.id, "worker-intruder-2", ttl_seconds=60) is False
    await db_session.refresh(task)
    assert task.result_json["_checkpoint"]["lease_expires_at"] == old_exp

    # Owner renews and extends lease_expires_at
    assert await renew_task_lease(task.id, "worker-owner-1", ttl_seconds=120) is True
    await db_session.refresh(task)
    new_exp = task.result_json["_checkpoint"]["lease_expires_at"]
    assert new_exp != old_exp
    assert task.result_json["_checkpoint"]["lease_owner"] == "worker-owner-1"


@pytest.mark.asyncio
async def test_active_lease_not_recovered_and_expired_lease_recovers(
    db_session: AsyncSession,
):
    from datetime import UTC, datetime, timedelta

    from app.services.evaluation_worker import recover_and_dispatch_queue_tasks

    ten_mins_ago = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    future_lease = (datetime.now(UTC) + timedelta(seconds=45)).isoformat()
    expired_lease = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()

    active_long_task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_REVIEW",
        title_hint="Long active VLM (>5m) with live lease",
        status="PROCESSING",
        stage="ANALYZING",
        result_json={
            "session_id": 201,
            "_checkpoint": {
                "completed_steps": ["PREPARING"],
                "last_activity_at": ten_mins_ago,
                "lease_owner": "sibling-container-worker",
                "lease_expires_at": future_lease,
            },
        },
    )
    expired_task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_EVALUATION",
        title_hint="Crashed worker expired lease",
        status="PROCESSING",
        stage="EVALUATING",
        result_json={
            "session_id": 202,
            "_checkpoint": {
                "completed_steps": ["PREPARING"],
                "last_activity_at": ten_mins_ago,
                "lease_owner": "dead-container-worker",
                "lease_expires_at": expired_lease,
            },
        },
    )
    db_session.add_all([active_long_task, expired_task])
    await db_session.commit()
    await db_session.refresh(active_long_task)
    await db_session.refresh(expired_task)

    with patch("app.services.evaluation_worker.process_evaluation_task"):
        summary = await recover_and_dispatch_queue_tasks(
            startup=True, stale_after_seconds=300
        )
        await asyncio.sleep(0.05)

    assert summary["recovered_count"] == 1
    assert expired_task.id in summary["dispatched_task_ids"]
    assert active_long_task.id not in summary["dispatched_task_ids"]

    await db_session.refresh(active_long_task)
    await db_session.refresh(expired_task)
    assert active_long_task.status == "PROCESSING"
    assert (
        active_long_task.result_json["_checkpoint"]["lease_owner"]
        == "sibling-container-worker"
    )
    assert expired_task.status == "QUEUED"
    assert expired_task.result_json["_checkpoint"]["lease_owner"] is None
    assert expired_task.result_json["_checkpoint"]["recovery_count"] == 1


@pytest.mark.asyncio
async def test_fenced_worker_cannot_commit_after_lease_loss(db_session: AsyncSession):
    import app.core.database as db_module
    from app.services.evaluation_worker import _execute_system_design_evaluation_steps
    from app.services.system_design_service import SystemDesignService

    task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_EVALUATION",
        title_hint="Fencing Test",
        status="PROCESSING",
        stage="EVALUATING",
        result_json={
            "session_id": 303,
            "_checkpoint": {
                "completed_steps": ["PREPARING"],
                "prepared_ctx": {"session_id": 303},
                "lease_owner": "worker-old",
            },
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async def hijack_lease_in_other_session(db, ctx):
        async with db_module.AsyncSessionLocal() as s2:
            other = await s2.get(IntakeEvaluationTaskModel, task.id)
            cp = dict(other.result_json["_checkpoint"])
            cp["lease_owner"] = "worker-new"
            other.result_json = {**other.result_json, "_checkpoint": cp}
            await s2.commit()
        return {
            "evaluation": {"overall_score": 88},
            "provider_telemetry": {"primary_provider": "mock"},
        }

    with (
        patch.object(
            SystemDesignService,
            "run_final_evaluation_inference",
            new=AsyncMock(side_effect=hijack_lease_in_other_session),
        ),
        patch.object(
            SystemDesignService,
            "persist_final_evaluation",
            new=AsyncMock(),
        ) as mock_persist,
    ):
        await _execute_system_design_evaluation_steps(
            task, db_session, worker_id="worker-old"
        )

    mock_persist.assert_not_called()
    await db_session.refresh(task)
    assert task.status == "PROCESSING"
    assert task.result_json["_checkpoint"]["lease_owner"] == "worker-new"
    assert "EVALUATING" not in task.result_json["_checkpoint"]["completed_steps"]


@pytest.mark.asyncio
async def test_atomic_claim_skip_locked_across_sessions(db_session: AsyncSession):
    import app.core.database as db_module

    task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="Skip Locked Contention",
        status="QUEUED",
        stage="QUEUED",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    async with db_module.AsyncSessionLocal() as lock_session:
        # Hold PostgreSQL FOR UPDATE row lock in session 1
        locked = (
            await lock_session.execute(
                select(IntakeEvaluationTaskModel)
                .where(IntakeEvaluationTaskModel.id == task.id)
                .with_for_update()
            )
        ).scalar_one()
        assert locked.id == task.id

        # Competing worker using a different session must immediately skip via SKIP LOCKED
        exec_count = 0

        async def should_not_run(*args, **kwargs):
            nonlocal exec_count
            exec_count += 1

        with patch(
            "app.services.evaluation_worker._execute_evaluation_steps",
            side_effect=should_not_run,
        ):
            await process_evaluation_task(task.id, worker_id="worker-beta")

        assert exec_count == 0
        await lock_session.rollback()

    # Once lock is released, worker-alpha claims and completes it once
    completed_workers: list[str] = []

    async def complete_steps(t, db, *, worker_id=None, **kwargs):
        completed_workers.append(worker_id or "")
        t.status = "COMPLETED"
        t.stage = "COMPLETE"
        await db.commit()

    with patch(
        "app.services.evaluation_worker._execute_evaluation_steps",
        side_effect=complete_steps,
    ):
        await process_evaluation_task(task.id, worker_id="worker-alpha")

    assert completed_workers == ["worker-alpha"]


@pytest.mark.asyncio
async def test_short_raw_text_fails_for_manual_input_or_scrapes_fallback(
    db_session: AsyncSession,
) -> None:
    """
    When an extension capture submits an incomplete snippet (< 100 chars),
    the worker must try scraping the URL if available, and fail with SCRAPE_FAILED
    so the UI prompts the user to supply the full job description.
    """
    from types import SimpleNamespace

    # Case 1: Tiny raw_text with no URL -> fails with SCRAPE_FAILED
    short_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="BNP Paribas - AI Engineer",
        raw_text="Check out our FAQ page\nSee the page",
        status="QUEUED",
        stage="FETCHING",
    )
    db_session.add(short_task)
    await db_session.commit()
    await db_session.refresh(short_task)

    await process_evaluation_task(short_task.id, db=db_session)
    await db_session.refresh(short_task)
    assert short_task.status == "FAILED"
    assert short_task.error_message is not None
    assert short_task.error_message.startswith("SCRAPE_FAILED:")

    # Case 2: Metadata-only raw_text (< 400 chars) where LLM finds no job -> fails with NO_JOB_FOUND
    meta_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="Siemens - IT Professional",
        raw_text="ID da vaga 528770\nEmpresa Siemens S.A.\nLocalização Amadora - Lisboa - Portugal\n"
        * 3,
        status="QUEUED",
        stage="FETCHING",
    )
    db_session.add(meta_task)
    await db_session.commit()
    await db_session.refresh(meta_task)

    mock_no_job = ExtractedJobSpec(job_found=False, company="Siemens", position="IT")
    with patch(
        "app.services.evaluation_worker.extract_job_spec",
        new=AsyncMock(return_value=mock_no_job),
    ):
        await process_evaluation_task(meta_task.id, db=db_session)
    await db_session.refresh(meta_task)
    assert meta_task.status == "FAILED"
    assert meta_task.error_message is not None
    assert meta_task.error_message.startswith("NO_JOB_FOUND:")

    # Case 3: Tiny raw_text with URL where scrape_job_url recovers full JD -> proceeds
    url_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        title_hint="BNP Paribas - AI Engineer",
        job_url="https://group.bnpparibas/en/careers/job-offer/ai-engineer",
        raw_text="Check out our FAQ page\nSee the page",
        status="QUEUED",
        stage="FETCHING",
    )
    db_session.add(url_task)
    await db_session.commit()
    await db_session.refresh(url_task)

    recovered_jd = (
        "About the Job\nResponsibilities: Build Python and FastAPI AI systems.\n"
        "Requirements: 5+ years of experience in backend engineering and LLMs.\n"
        + ("Detailed role description. " * 20)
    )
    mock_job_spec = ExtractedJobSpec(
        job_found=True,
        company="BNP Paribas",
        position="AI Engineer",
        responsibilities=["Build Python AI systems"],
        requirements=["5+ years experience"],
        extracted_skills=["Python", "FastAPI"],
    )
    mock_assessment = JobAssessmentResult(
        company="BNP Paribas",
        position="AI Engineer",
        recommendation="APPLY_STRONGLY",
        fit_score=90,
        matching_skills=["Python"],
        pros=["Strong match"],
        cons=[],
        summary="Good fit.",
    )
    with (
        patch(
            "app.services.evaluation_worker.scrape_job_url",
            new=AsyncMock(return_value=SimpleNamespace(text=recovered_jd)),
        ),
        patch(
            "app.services.evaluation_worker.extract_job_spec",
            new=AsyncMock(return_value=mock_job_spec),
        ),
        patch(
            "app.services.evaluation_worker.assess_job_posting",
            new=AsyncMock(return_value=mock_assessment),
        ),
    ):
        await process_evaluation_task(url_task.id, db=db_session)

    await db_session.refresh(url_task)
    assert url_task.status == "COMPLETED"
    assert url_task.result_json["fit_score"] == 90
