import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_queue import concurrency_manager
from app.core.database import AsyncSessionLocal
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.job_saver import persist_or_stage_job_assessment
from app.services.llm import assess_job_posting
from app.services.matcher import compute_programmatic_skill_match

logger = logging.getLogger(__name__)


async def _execute_evaluation_steps(task: IntakeEvaluationTaskModel, db: AsyncSession) -> None:
    try:
        content = task.raw_text

        # Stage 1: Fetch URL if content not already provided
        if not content and task.job_url:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        task.job_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                        follow_redirects=True,
                    )
                    if resp.status_code == 200:
                        content = resp.text[:12000]
            except Exception as scrape_err:
                logger.warning("Worker scrape failed for %s: %s", task.job_url, scrape_err)

        if not content or not content.strip():
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = (
                "SCRAPE_FAILED: Unable to scrape job portal automatically. Please provide job description text."
            )
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Stage 2: Extract Specs
        task.stage = "EXTRACTING"
        await db.commit()

        # Stage 3: CV Keyword Overlap Matching
        task.stage = "MATCHING"
        cv_stmt = select(CandidateCVModel).where(CandidateCVModel.is_active == True).order_by(CandidateCVModel.id.desc())
        cv_res = await db.execute(cv_stmt)
        active_cv = cv_res.scalars().first()
        candidate_skills = active_cv.extracted_skills if active_cv else []

        match_info = compute_programmatic_skill_match(candidate_skills, content)
        await db.commit()

        # Stage 4: Qualitative AI Fit Assessment
        task.stage = "ASSESSING"
        await db.commit()

        assessment = await assess_job_posting(
            db,
            content,
            candidate_skills=candidate_skills,
            programmatic_baseline=match_info.get("programmatic_score", 0),
        )

        # Persist to database (or route to staging if duplicate)
        save_result = await persist_or_stage_job_assessment(
            db=db,
            assessment=assessment,
            raw_text=content,
            job_url=task.job_url,
            force_new=False,
            target_status="ASSESSMENT",
        )

        # Completed Successfully
        task.status = "COMPLETED"
        task.stage = "STAGED_DUPLICATE" if save_result.get("is_duplicate") else "COMPLETE"
        result_payload = assessment.model_dump()
        result_payload["application_id"] = save_result.get("application_id")
        result_payload["staging_item_id"] = save_result.get("staging_item_id")
        result_payload["is_duplicate"] = save_result.get("is_duplicate", False)
        result_payload["save_status"] = save_result.get("status")
        task.result_json = result_payload
        task.title_hint = f"{assessment.company} - {assessment.position}"
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(
            "Intake evaluation task %d completed for '%s' (saved: %s, app_id: %s, staged_id: %s)",
            task.id,
            task.title_hint,
            save_result.get("status"),
            save_result.get("application_id"),
            save_result.get("staging_item_id"),
        )

    except Exception as err:
        logger.error("Failed processing intake task %d: %s", task.id, err, exc_info=True)
        task.status = "FAILED"
        task.stage = "FAILED"
        task.error_message = str(err)
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def process_evaluation_task(task_id: int, db: AsyncSession | None = None) -> None:
    """
    Processes a single queued intake evaluation task asynchronously within
    the provider's configured concurrency limits.
    """
    if db is not None:
        task = await db.get(IntakeEvaluationTaskModel, task_id)
        if not task or task.status == "CANCELLED":
            return
        task.status = "PROCESSING"
        task.stage = "FETCHING"
        await db.commit()
        await _execute_evaluation_steps(task, db)
        return

    async with AsyncSessionLocal() as session:
        stmt = select(IntakeEvaluationTaskModel).where(IntakeEvaluationTaskModel.id == task_id)
        res = await session.execute(stmt)
        task = res.scalar_one_or_none()

        if not task:
            logger.warning("Intake task %d not found for processing", task_id)
            return

        # 1. Resolve Provider and Concurrency Limit for EXTRACTION / AGENT_REASONING
        binding_stmt = select(AITaskBindingModel, AIProviderModel).join(
            AIProviderModel, AITaskBindingModel.provider_id == AIProviderModel.id
        ).where(
            AITaskBindingModel.task_type.in_(["EXTRACTION", "AGENT_REASONING"]),
            AITaskBindingModel.is_active == True,
            AIProviderModel.is_active == True,
        )
        binding_res = await session.execute(binding_stmt)
        row = binding_res.first()

        provider_id = row[1].id if row else None
        max_concurrency = row[1].max_concurrency if row else 1

        task.status = "PROCESSING"
        task.stage = "FETCHING"
        await session.commit()

    # 2. Acquire Provider Semaphore to prevent local VRAM thrashing
    async with concurrency_manager.acquire(provider_id, max_concurrency):
        async with AsyncSessionLocal() as session:
            task = await session.get(IntakeEvaluationTaskModel, task_id)
            if not task or task.status == "CANCELLED":
                return
            await _execute_evaluation_steps(task, session)
