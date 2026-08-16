from datetime import datetime, timezone
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_queue import concurrency_manager
from app.core.database import AsyncSessionLocal
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.job_saver import persist_or_stage_job_assessment
from app.services.llm import (
    anonymize_and_parse_cv,
    assess_job_posting,
    extract_job_spec,
)
from app.services.matcher import compute_programmatic_skill_match

from app.services.scraper import scrape_job_url

logger = logging.getLogger(__name__)


async def _execute_cv_extraction_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    try:
        raw_text = task.raw_text
        if not raw_text or not raw_text.strip():
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "EMPTY_CV: Provided CV text is empty."
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Stage 1: SCRUBBING
        task.stage = "SCRUBBING"
        await db.commit()

        # Stage 2: EXTRACTING
        task.stage = "EXTRACTING"
        await db.commit()

        anonymized_result = await anonymize_and_parse_cv(db, raw_text)

        # Stage 3: SAVING
        task.stage = "SAVING"
        await db.commit()

        # Delete previous active profiles
        from sqlalchemy import delete

        stmt_delete = delete(CandidateCVModel)
        await db.execute(stmt_delete)

        # Build domain_experience list of dicts
        raw_breakdown = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in (anonymized_result.domain_breakdown or [])
        ]
        if not raw_breakdown and anonymized_result.domain_expertise:
            raw_breakdown = [
                {
                    "domain": d,
                    "years": max(
                        1.0,
                        round(
                            anonymized_result.total_years_experience
                            / max(1, len(anonymized_result.domain_expertise)),
                            1,
                        ),
                    ),
                    "is_active": True,
                }
                for d in anonymized_result.domain_expertise
            ]

        cv_record = CandidateCVModel(
            raw_text=raw_text,
            anonymized_text=anonymized_result.anonymized_resume,
            extracted_skills=anonymized_result.extracted_skills,
            years_of_experience=anonymized_result.total_years_experience,
            domain_expertise=anonymized_result.domain_expertise,
            domain_experience=raw_breakdown,
            core_competencies=anonymized_result.core_competencies,
            summary=anonymized_result.summary,
            is_active=True,
        )
        db.add(cv_record)
        await db.commit()
        await db.refresh(cv_record)

        # Stage 4: COMPLETE
        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        task.result_json = {
            "profile_id": cv_record.id,
            "years_of_experience": cv_record.years_of_experience,
            "extracted_skills_count": len(cv_record.extracted_skills),
            "domain_experience_count": len(raw_breakdown),
            "summary": cv_record.summary,
        }
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(
            "CV extraction task %d completed. Active profile ID: %d",
            task.id,
            cv_record.id,
        )

    except Exception as err:
        logger.error("Failed processing CV task %d: %s", task.id, err, exc_info=True)
        task.status = "FAILED"
        task.stage = "FAILED"
        task.error_message = str(err)
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def _execute_evaluation_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    if task.task_type == "CV_EXTRACTION":
        await _execute_cv_extraction_steps(task, db)
        return

    try:
        content = task.raw_text

        # Stage 1: Fetch URL if content not already provided
        if not content and task.job_url:
            scraped = await scrape_job_url(task.job_url)
            if scraped.text:
                content = scraped.text

        if not content or not content.strip():
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "SCRAPE_FAILED: Unable to scrape job portal automatically. Please provide job description text."
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Stage 2: Extract Specs
        task.stage = "EXTRACTING"
        await db.commit()

        job_spec = await extract_job_spec(db, content)
        if not job_spec.job_found:
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "NO_JOB_FOUND: The scraped page or input text did not contain an active job description or vacancy."
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Stage 3: CV Keyword Overlap Matching
        task.stage = "MATCHING"
        cv_stmt = select(CandidateCVModel).limit(1)
        cv_res = await db.execute(cv_stmt)
        active_cv = cv_res.scalars().first()
        candidate_skills = active_cv.extracted_skills if active_cv else []

        match_info = compute_programmatic_skill_match(candidate_skills, content)
        await db.commit()

        # Format active domain experience breakdown string
        active_domains_str = None
        if active_cv and active_cv.domain_experience:
            active_list = [
                f"{item['domain']} ({item['years']} yrs)"
                for item in active_cv.domain_experience
                if item.get("is_active", True)
            ]
            if active_list:
                active_domains_str = ", ".join(active_list)
        elif active_cv and active_cv.domain_expertise:
            active_domains_str = ", ".join(active_cv.domain_expertise)

        # Stage 4: Qualitative AI Fit Assessment
        task.stage = "ASSESSING"
        await db.commit()

        assessment = await assess_job_posting(
            db,
            content,
            candidate_skills=candidate_skills,
            candidate_cv=active_cv.anonymized_text or active_cv.raw_text
            if active_cv
            else None,
            candidate_domain_breakdown=active_domains_str,
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
        task.stage = (
            "STAGED_DUPLICATE" if save_result.get("is_duplicate") else "COMPLETE"
        )
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
        logger.error(
            "Failed processing intake task %d: %s", task.id, err, exc_info=True
        )
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
        task.stage = "SCRUBBING" if task.task_type == "CV_EXTRACTION" else "FETCHING"
        await db.commit()
        await _execute_evaluation_steps(task, db)
        return

    async with AsyncSessionLocal() as session:
        stmt = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.id == task_id
        )
        res = await session.execute(stmt)
        task = res.scalar_one_or_none()

        if not task or task.status == "CANCELLED":
            logger.warning("Intake task %d not found or cancelled", task_id)
            return

        # 1. Resolve Provider and Concurrency Limit for EXTRACTION / AGENT_REASONING
        binding_stmt = (
            select(AITaskBindingModel, AIProviderModel)
            .join(AIProviderModel, AITaskBindingModel.provider_id == AIProviderModel.id)
            .where(
                AITaskBindingModel.task_type.in_(["EXTRACTION", "AGENT_REASONING"]),
                AITaskBindingModel.is_active,
                AIProviderModel.is_active,
            )
        )
        binding_res = await session.execute(binding_stmt)
        row = binding_res.first()

        provider_id = row[1].id if row else None
        max_concurrency = row[1].max_concurrency if row else 1

    # 2. Acquire Provider Semaphore to prevent local VRAM thrashing
    async with concurrency_manager.acquire(provider_id, max_concurrency):
        async with AsyncSessionLocal() as session:
            task = await session.get(IntakeEvaluationTaskModel, task_id)
            if not task or task.status == "CANCELLED":
                return

            task.status = "PROCESSING"
            task.stage = (
                "SCRUBBING" if task.task_type == "CV_EXTRACTION" else "FETCHING"
            )
            await session.commit()

            await _execute_evaluation_steps(task, session)
