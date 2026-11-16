from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.llm import ExtractedJobSpec, JobAssessmentResult
from app.services.evaluation_worker import (
    _execute_evaluation_steps,
    process_evaluation_task,
)


@pytest.mark.asyncio
async def test_evaluation_task_checkpoint_and_resume_unit():
    """
    Unit test using AsyncMock DB session to verify that intermediate step state is saved
    to task.result_json['_checkpoint'] and that retrying a task resumes from point of failure.
    """
    task = IntakeEvaluationTaskModel(
        id=101,
        task_type="JOB_ASSESSMENT",
        job_url="https://example.com/job-lead",
        title_hint="Test Job Lead",
        status="PROCESSING",
        stage="FETCHING",
        result_json=None,
    )

    mock_scalars = type("Scal", (), {"first": lambda *a, **kw: None})()
    mock_exec_res = type("Res", (), {"scalars": lambda *a, **kw: mock_scalars})()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_exec_res)

    mock_scraped_text = "Acme Corp - Senior Software Engineer\nRequirements and Responsibilities: Python, Postgres\nSkills: Python, Postgres"
    mock_job_spec = ExtractedJobSpec(
        job_found=True,
        company="Acme Corp",
        position="Senior Software Engineer",
        workplace_type="Remote",
        compensation_text="$150k",
        responsibilities=["Build APIs"],
        requirements=["Python, Postgres"],
        extracted_skills=["Python", "Postgres"],
    )

    # 1. First execution run: Scrape succeeds, Spec Extraction succeeds, but Matching raises an exception
    mock_scrape = AsyncMock(
        return_value=type("Scraped", (), {"text": mock_scraped_text})()
    )
    mock_spec_extract = AsyncMock(return_value=mock_job_spec)
    mock_match = MagicMock(side_effect=RuntimeError("Simulated matching failure"))

    with (
        patch("app.services.evaluation_worker.scrape_job_url", new=mock_scrape),
        patch("app.services.evaluation_worker.extract_job_spec", new=mock_spec_extract),
        patch(
            "app.services.evaluation_worker.compute_programmatic_skill_match",
            new=mock_match,
        ),
    ):
        await _execute_evaluation_steps(task, mock_db)

    # Verify state after failure in stage 3 (matching)
    assert task.status == "FAILED"
    assert "Simulated matching failure" in task.error_message

    # Verify intermediate checkpoint saved scraped content and extracted spec
    checkpoint = (task.result_json or {}).get("_checkpoint")
    assert checkpoint is not None
    assert checkpoint.get("content") == mock_scraped_text
    assert checkpoint.get("structured_spec")["company"] == "Acme Corp"

    # 2. Second execution run (Resume on retry):
    # Reset status to QUEUED / PROCESSING (simulating retry), preserving task.result_json
    task.status = "PROCESSING"
    task.error_message = None

    mock_assessment = JobAssessmentResult(
        company="Acme Corp",
        position="Senior Software Engineer",
        location="Remote",
        work_model="Remote",
        recommendation="APPLY_STRONGLY",
        fit_score=90,
        matching_skills=["Python", "Postgres"],
        pros=["Great tech stack"],
        cons=[],
        summary="Excellent fit.",
    )

    mock_scrape_resume = AsyncMock()
    mock_spec_resume = AsyncMock()
    mock_match_resume = MagicMock(return_value={"programmatic_score": 85})
    mock_assess_resume = AsyncMock(return_value=mock_assessment)
    mock_save_resume = AsyncMock(
        return_value={"status": "committed", "application_id": 42}
    )

    with (
        patch("app.services.evaluation_worker.scrape_job_url", new=mock_scrape_resume),
        patch("app.services.evaluation_worker.extract_job_spec", new=mock_spec_resume),
        patch(
            "app.services.evaluation_worker.compute_programmatic_skill_match",
            new=mock_match_resume,
        ),
        patch(
            "app.services.evaluation_worker.assess_job_posting", new=mock_assess_resume
        ),
        patch(
            "app.services.evaluation_worker.persist_or_stage_job_assessment",
            new=mock_save_resume,
        ),
    ):
        await _execute_evaluation_steps(task, mock_db)

    # 3. Verify already-completed stages (Scrape, Spec Extraction) were SKIPPED on resume
    mock_scrape_resume.assert_not_called()
    mock_spec_resume.assert_not_called()
    mock_match_resume.assert_called_once()
    mock_assess_resume.assert_called_once()

    # 4. Verify task completed successfully
    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert task.result_json["company"] == "Acme Corp"
    assert task.result_json["fit_score"] == 90
    assert task.result_json["application_id"] == 42


@pytest.mark.asyncio
async def test_evaluation_task_checkpoint_and_resume(db_session):
    """Integration test using db_session fixture when database is available."""
    task = IntakeEvaluationTaskModel(
        job_url="https://example.com/job-lead-2",
        title_hint="Test Job Lead Integration",
        status="QUEUED",
        stage="FETCHING",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    mock_scraped_text = "Beta Co - Frontend Engineer\nRequirements and Responsibilities: Vue, TypeScript\nSkills: Vue, TypeScript"
    mock_job_spec = ExtractedJobSpec(
        job_found=True,
        company="Beta Co",
        position="Frontend Engineer",
        workplace_type="Remote",
        compensation_text="$130k",
        responsibilities=["Build Vue components"],
        requirements=["Vue, TypeScript"],
        extracted_skills=["Vue", "TypeScript"],
    )

    mock_scrape = AsyncMock(
        return_value=type("Scraped", (), {"text": mock_scraped_text})()
    )
    mock_spec_extract = AsyncMock(return_value=mock_job_spec)
    mock_match = MagicMock(side_effect=RuntimeError("Simulated matching error"))

    with (
        patch("app.services.evaluation_worker.scrape_job_url", new=mock_scrape),
        patch("app.services.evaluation_worker.extract_job_spec", new=mock_spec_extract),
        patch(
            "app.services.evaluation_worker.compute_programmatic_skill_match",
            new=mock_match,
        ),
    ):
        await process_evaluation_task(task.id, db=db_session)

    await db_session.refresh(task)
    assert task.status == "FAILED"
    checkpoint = (task.result_json or {}).get("_checkpoint")
    assert checkpoint is not None
    assert checkpoint.get("content") == mock_scraped_text

    task.status = "QUEUED"
    await db_session.commit()

    mock_assessment = JobAssessmentResult(
        company="Beta Co",
        position="Frontend Engineer",
        location="Remote",
        work_model="Remote",
        recommendation="APPLY_MODERATELY",
        fit_score=80,
        matching_skills=["Vue", "TypeScript"],
        pros=["Modern stack"],
        cons=[],
        summary="Good fit.",
    )

    mock_scrape_resume = AsyncMock()
    mock_spec_resume = AsyncMock()
    mock_match_resume = MagicMock(return_value={"programmatic_score": 80})
    mock_assess_resume = AsyncMock(return_value=mock_assessment)

    with (
        patch("app.services.evaluation_worker.scrape_job_url", new=mock_scrape_resume),
        patch("app.services.evaluation_worker.extract_job_spec", new=mock_spec_resume),
        patch(
            "app.services.evaluation_worker.compute_programmatic_skill_match",
            new=mock_match_resume,
        ),
        patch(
            "app.services.evaluation_worker.assess_job_posting", new=mock_assess_resume
        ),
    ):
        await process_evaluation_task(task.id, db=db_session)

    mock_scrape_resume.assert_not_called()
    mock_spec_resume.assert_not_called()

    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    assert task.result_json["company"] == "Beta Co"


@pytest.mark.asyncio
async def test_system_design_review_checkpoint_resume_and_cancellation(
    db_session, tmp_path
):
    from sqlalchemy import select

    from app.models.system_design import SystemDesignChallengeModel
    from app.services.evaluation_worker import _execute_system_design_review_steps
    from app.services.system_design_service import SystemDesignService

    await SystemDesignService._ensure_challenges_seeded(db_session)
    challenge = (
        (await db_session.execute(select(SystemDesignChallengeModel))).scalars().first()
    )
    session = await SystemDesignService.start_session(
        db_session, challenge_id=challenge.id, mode="ADAPTIVE"
    )
    session_id = int(session.id)
    await SystemDesignService.update_requirements_ledger(
        db_session,
        session_id,
        payload=type(
            "LedgerReq",
            (),
            {
                "functional_requirements": ["Create short URL", "Redirect"],
                "non_functional_requirements": ["Low latency"],
                "scale_estimates": {"dau": "100k"},
                "out_of_scope": [],
                "notes": "",
                "is_locked": True,
            },
        )(),
    )

    diagram_path = tmp_path / "diag.png"
    diagram_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake")
    session_obj = await SystemDesignService.get_session(db_session, session_id)
    session_obj.diagrams_metadata = [
        {
            "version": 1,
            "filename": "diag.png",
            "mime_type": "image/png",
            "size_bytes": 24,
            "notes": "Initial v1",
            "file_path": str(diagram_path),
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    await db_session.commit()

    task = IntakeEvaluationTaskModel(
        task_type="SYSTEM_DESIGN_REVIEW",
        title_hint="Checkpoint SD Review",
        status="PROCESSING",
        stage="ANALYZING",
        result_json={"session_id": session_id, "diagram_version": 1},
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    fake_ctx = {
        "session_id": session_id,
        "target_version": 1,
        "file_path": str(diagram_path),
        "mime_type": "image/png",
        "sys_prompt": "Review architecture",
    }
    fake_review = {
        "diagram_version": 1,
        "interpreted_components": ["API", "Cache"],
        "interpreted_data_flows": ["Client -> API"],
        "visual_clarifications_needed": [],
        "strengths": ["Clear separation"],
        "missing_components": [],
        "bottlenecks_and_spofs": ["Single Redis"],
        "unnecessary_complexity": [],
        "requirement_gaps": [],
        "overall_impression": "Solid baseline.",
        "suggested_defence_topics": ["How do you handle Redis failover?"],
    }

    # 1. Fail during ANALYZING (validation error) -> PREPARING checkpoint must persist
    with (
        patch.object(
            SystemDesignService,
            "prepare_diagram_review_context",
            new=AsyncMock(return_value=fake_ctx),
        ) as m_prep1,
        patch.object(
            SystemDesignService,
            "run_diagram_vlm_inference",
            new=AsyncMock(side_effect=ValueError("VLM returned invalid JSON")),
        ),
    ):
        await _execute_system_design_review_steps(task, db_session)

    assert m_prep1.call_count == 1
    await db_session.refresh(task)
    assert task.status == "FAILED"
    cp = task.result_json["_checkpoint"]
    assert cp["completed_steps"] == ["PREPARING"]
    assert cp["prepared_ctx"]["file_path"] == str(diagram_path)

    # 2. Resume after retry, succeed ANALYZING, then simulate user CANCEL before SAVING commit
    task.status = "PROCESSING"
    task.stage = "ANALYZING"
    task.error_message = None
    await db_session.commit()

    async def cancel_after_inference(db, ctx):
        # User hits /cancel while VLM inference finishes
        db_task = await db.get(IntakeEvaluationTaskModel, task.id)
        db_task.status = "CANCELLED"
        db_task.stage = "CANCELLED"
        await db.commit()
        return {
            "review": fake_review,
            "provider_telemetry": {
                "primary_provider": "Local VLM",
                "last_used_provider": "Local VLM",
                "fallback_used": False,
            },
        }

    with (
        patch.object(
            SystemDesignService,
            "prepare_diagram_review_context",
            new=AsyncMock(),
        ) as m_prep2,
        patch.object(
            SystemDesignService,
            "run_diagram_vlm_inference",
            new=AsyncMock(side_effect=cancel_after_inference),
        ),
        patch.object(
            SystemDesignService,
            "persist_architecture_review",
            new=AsyncMock(),
        ) as m_persist2,
    ):
        await _execute_system_design_review_steps(task, db_session)

    m_prep2.assert_not_called()
    m_persist2.assert_not_called()
    await db_session.refresh(task)
    assert task.status == "CANCELLED"
    assert task.result_json["_checkpoint"]["completed_steps"] == [
        "PREPARING",
        "ANALYZING",
    ]
    fresh_session = await SystemDesignService.get_session(db_session, session_id)
    assert len(fresh_session.architecture_reviews or []) == 0

    # 3. Retry again -> resumes straight at SAVING, skips PREPARING & ANALYZING
    task.status = "PROCESSING"
    task.stage = "SAVING"
    await db_session.commit()

    with (
        patch.object(
            SystemDesignService,
            "prepare_diagram_review_context",
            new=AsyncMock(),
        ) as m_prep3,
        patch.object(
            SystemDesignService,
            "run_diagram_vlm_inference",
            new=AsyncMock(),
        ) as m_inf3,
    ):
        await _execute_system_design_review_steps(task, db_session)

    m_prep3.assert_not_called()
    m_inf3.assert_not_called()
    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert task.result_json["_checkpoint"]["completed_steps"] == [
        "PREPARING",
        "ANALYZING",
        "SAVING",
    ]
    final_session = await SystemDesignService.get_session(db_session, session_id)
    assert len(final_session.architecture_reviews or []) == 1


@pytest.mark.asyncio
async def test_system_design_evaluation_failover_telemetry_persisted(db_session):
    import json

    from sqlalchemy import select

    from app.core.llm_factory import FailoverChatModel
    from app.models.system_design import SystemDesignChallengeModel
    from app.services.evaluation_worker import process_evaluation_task
    from app.services.system_design_service import (
        DEFAULT_RUBRIC_DIMENSIONS,
        SystemDesignService,
    )

    await SystemDesignService._ensure_challenges_seeded(db_session)
    challenge = (
        (await db_session.execute(select(SystemDesignChallengeModel))).scalars().first()
    )
    session = await SystemDesignService.start_session(
        db_session, challenge_id=challenge.id, mode="ADAPTIVE"
    )
    s_obj = await SystemDesignService.get_session(db_session, session.id)
    s_obj.requirements_ledger = {
        "functional_requirements": ["Shorten URLs"],
        "non_functional_requirements": ["High availability"],
        "scale_estimates": {"dau": "100k"},
        "out_of_scope": [],
        "notes": "",
        "is_locked": True,
    }
    s_obj.stage = "DEFENCE"
    s_obj.diagrams_metadata = [{"version": 1, "filename": "v1.png", "size_bytes": 10}]
    s_obj.architecture_reviews = [{"diagram_version": 1, "overall_impression": "Good."}]
    s_obj.defence_transcript = [
        {"turn_index": 1, "role": "interviewer", "content": "Why cache?"},
        {"turn_index": 2, "role": "candidate", "content": "Reduce DB read load."},
    ]
    await db_session.commit()

    eval_payload = {
        "overall_score": 80.0,
        "readiness_rating": "INTERVIEW_READY",
        "executive_summary": "Solid architecture and defence.",
        "rubric_scores": [
            {
                "dimension": dim,
                "score": 4,
                "evidence": f"Evidence observed for {dim}.",
                "critique": f"Actionable improvement advice for {dim}.",
            }
            for dim in DEFAULT_RUBRIC_DIMENSIONS
        ],
        "key_strengths": ["Low latency read path"],
        "critical_gaps": ["Quantify replication lag"],
        "recommended_next_steps": ["Add circuit breakers"],
    }

    primary_mock = AsyncMock(
        ainvoke=AsyncMock(side_effect=ConnectionError("Connection refused"))
    )
    fallback_mock = AsyncMock(
        ainvoke=AsyncMock(return_value=AsyncMock(content=json.dumps(eval_payload)))
    )
    failover_chat = FailoverChatModel(
        primary_model=primary_mock,
        fallback_model=fallback_mock,
        primary_name="Local LM Studio",
        fallback_name="Cloud Fallback Provider",
    )

    _, task = await SystemDesignService.enqueue_final_evaluation(db_session, session.id)
    with patch(
        "app.services.system_design_service.get_task_chat_model",
        return_value=failover_chat,
    ):
        await process_evaluation_task(task.id, db=db_session)

    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    cp = task.result_json["_checkpoint"]
    assert cp["completed_steps"] == ["PREPARING", "EVALUATING", "SAVING"]
    telemetry = cp["provider_telemetry"]
    assert telemetry["fallback_used"] is True
    assert telemetry["last_used_provider"] == "Cloud Fallback Provider"
    assert "Connection refused" in telemetry["last_fallback_error"]
