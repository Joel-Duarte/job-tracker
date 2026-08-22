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
