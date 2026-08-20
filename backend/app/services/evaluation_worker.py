import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_queue import concurrency_manager
from app.core.database import AsyncSessionLocal
from app.core.url_utils import normalize_job_url
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.applications import ApplicationModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.job_saver import persist_or_stage_job_assessment
from app.services.llm import (
    anonymize_and_parse_cv,
    assess_job_posting,
    extract_job_spec,
    generate_cover_letter,
)
from app.services.matcher import compute_programmatic_skill_match
from app.services.scraper import scrape_job_url
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)


async def _execute_cover_letter_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    try:
        app_id = (task.result_json or {}).get("application_id")
        if not app_id and task.raw_text and task.raw_text.isdigit():
            app_id = int(task.raw_text)

        if not app_id:
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = (
                "MISSING_APP_ID: Cover letter task missing application_id."
            )
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        task.stage = "GENERATING"
        await db.commit()

        from sqlalchemy.orm import joinedload, selectinload

        stmt = (
            select(ApplicationModel)
            .where(ApplicationModel.id == app_id)
            .options(
                joinedload(ApplicationModel.company),
                selectinload(ApplicationModel.job_posting),
            )
        )
        res = await db.execute(stmt)
        app = res.scalar_one_or_none()

        if not app:
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = (
                f"APPLICATION_NOT_FOUND: Application ID {app_id} not found."
            )
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        # Fetch Candidate CV
        cv_stmt = (
            select(CandidateCVModel)
            .where(CandidateCVModel.is_active.is_(True))
            .limit(1)
        )
        cv_res = await db.execute(cv_stmt)
        active_cv = cv_res.scalars().first()
        if not active_cv:
            cv_stmt_fallback = select(CandidateCVModel).limit(1)
            cv_res_fallback = await db.execute(cv_stmt_fallback)
            active_cv = cv_res_fallback.scalars().first()

        cv_text = (active_cv.anonymized_text or active_cv.raw_text) if active_cv else ""
        company_name = app.company.name if app.company else ""
        position_name = app.position or ""
        job_desc = (
            app.job_posting.description_markdown
            if app.job_posting and app.job_posting.description_markdown
            else ""
        )

        tone_val = (task.result_json or {}).get("tone") or "professional"
        instructions_val = (task.result_json or {}).get("custom_instructions")

        cl_text = await generate_cover_letter(
            db,
            company_name=company_name,
            position=position_name,
            job_description=job_desc,
            candidate_cv=cv_text,
            tone=tone_val,
            custom_instructions=instructions_val,
        )

        app.cover_letter_text = cl_text
        app.cover_letter_status = "GENERATED"
        app.cover_letter_generated_at = datetime.now(UTC)

        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        task.result_json = {
            "application_id": app.id,
            "cover_letter_text": cl_text,
            "cover_letter_status": "GENERATED",
            "cover_letter_generated_at": app.cover_letter_generated_at.isoformat(),
            "company": company_name,
            "position": position_name,
            "tone": tone_val,
        }
        task.completed_at = datetime.now(UTC)

        # Sync cover_letter_status and cover_letter_text to matching JOB_ASSESSMENT tasks for this application
        stmt_tasks = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.result_json.op("->>")("application_id")
            == str(app.id)
        )
        tasks_res = await db.execute(stmt_tasks)
        for t in tasks_res.scalars().all():
            if t.result_json:
                updated_json = dict(t.result_json)
                updated_json["cover_letter_text"] = cl_text
                updated_json["cover_letter_status"] = "GENERATED"
                updated_json["cover_letter_generated_at"] = (
                    app.cover_letter_generated_at.isoformat()
                )
                t.result_json = updated_json

        await db.commit()
        logger.info(
            "Cover letter generation task %d completed for application %d",
            task.id,
            app.id,
        )

    except Exception as err:
        logger.error(
            "Failed processing cover letter task %d: %s", task.id, err, exc_info=True
        )
        task.status = "FAILED"
        task.stage = "FAILED"
        task.error_message = str(err)
        task.completed_at = datetime.now(UTC)
        await db.commit()


async def _execute_cv_extraction_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    try:
        raw_text = task.raw_text
        if not raw_text or not raw_text.strip():
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "EMPTY_CV: Provided CV text is empty."
            task.completed_at = datetime.now(UTC)
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
        task.completed_at = datetime.now(UTC)
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
        task.completed_at = datetime.now(UTC)
        await db.commit()


async def _execute_evaluation_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    async with trace_operation(
        category="worker",
        name=f"worker_{task.task_type.lower()}",
        inputs={
            "task_id": task.id,
            "task_type": task.task_type,
            "job_url": task.job_url,
            "title_hint": task.title_hint,
        },
    ) as ctx:
        if task.task_type == "CV_EXTRACTION":
            await _execute_cv_extraction_steps(task, db)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type == "COVER_LETTER":
            await _execute_cover_letter_steps(task, db)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        try:
            content = task.raw_text
            clean_job_url = normalize_job_url(task.job_url)

            # Stage 1: Fetch URL if content not already provided
            if not content and clean_job_url:
                scraped = await scrape_job_url(clean_job_url)
                if scraped.text:
                    content = scraped.text

            if not content or not content.strip():
                task.status = "FAILED"
                task.stage = "FAILED"
                task.error_message = "SCRAPE_FAILED: Unable to scrape job portal automatically. Please provide job description text."
                task.completed_at = datetime.now(UTC)
                await db.commit()
                ctx["error"] = task.error_message
                ctx["outputs"] = {"status": task.status, "stage": task.stage}
                return

            # Stage 2: Extract Specs
            task.stage = "EXTRACTING"
            await db.commit()

            job_spec = await extract_job_spec(db, content)
            if not job_spec.job_found:
                task.status = "FAILED"
                task.stage = "FAILED"
                task.error_message = "NO_JOB_FOUND: The scraped page or input text did not contain an active job description or vacancy."
                task.completed_at = datetime.now(UTC)
                await db.commit()
                ctx["error"] = task.error_message
                ctx["outputs"] = {"status": task.status, "stage": task.stage}
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
                job_url=clean_job_url,
                force_new=False,
                target_status="ASSESSMENT",
                structured_spec=job_spec.model_dump(),
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
            task.completed_at = datetime.now(UTC)
            await db.commit()
            ctx["outputs"] = {
                "status": task.status,
                "stage": task.stage,
                "company": assessment.company,
                "position": assessment.position,
                "fit_score": assessment.fit_score,
            }
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
            task.completed_at = datetime.now(UTC)
            await db.commit()
            ctx["error"] = str(err)
            ctx["outputs"] = {"status": "FAILED", "stage": "FAILED"}


async def process_evaluation_task(task_id: int, db: AsyncSession | None = None) -> None:
    """
    Processes a single queued intake evaluation task asynchronously within
    the provider's configured concurrency limits.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.id == task_id
        )
        res = await session.execute(stmt)
        task = res.scalar_one_or_none()

        if not task or task.status == "CANCELLED":
            logger.warning("Intake task %d not found or cancelled", task_id)
            return

        task_type = task.task_type or "JOB_ASSESSMENT"

        # 1. Resolve Provider and Concurrency Limit for this task_type (or GLOBAL_DEFAULT)
        binding_stmt = (
            select(AITaskBindingModel, AIProviderModel)
            .join(AIProviderModel, AITaskBindingModel.provider_id == AIProviderModel.id)
            .where(
                AITaskBindingModel.task_type.in_([task_type, "GLOBAL_DEFAULT"]),
                AITaskBindingModel.is_active,
                AIProviderModel.is_active,
            )
        )
        binding_res = await session.execute(binding_stmt)
        rows = binding_res.all()

        exact_row = next((r for r in rows if r[0].task_type == task_type), None)
        global_row = next((r for r in rows if r[0].task_type == "GLOBAL_DEFAULT"), None)
        selected_row = exact_row or global_row or (rows[0] if rows else None)

        provider_id = selected_row[1].id if selected_row else None
        max_concurrency = selected_row[1].max_concurrency if selected_row else 1

    # 2. Acquire Provider Semaphore to strictly gate task execution based on provider's max concurrency setting
    async with concurrency_manager.acquire(provider_id, max_concurrency):
        if db is not None:
            task = await db.get(IntakeEvaluationTaskModel, task_id)
            if not task or task.status == "CANCELLED":
                return
            task.status = "PROCESSING"
            task.stage = (
                "SCRUBBING"
                if task.task_type == "CV_EXTRACTION"
                else ("GENERATING" if task.task_type == "COVER_LETTER" else "FETCHING")
            )
            await db.commit()
            await _execute_evaluation_steps(task, db)
            return

        async with AsyncSessionLocal() as session:
            task = await session.get(IntakeEvaluationTaskModel, task_id)
            if not task or task.status == "CANCELLED":
                return

            task.status = "PROCESSING"
            task.stage = (
                "SCRUBBING"
                if task.task_type == "CV_EXTRACTION"
                else ("GENERATING" if task.task_type == "COVER_LETTER" else "FETCHING")
            )
            await session.commit()

            await _execute_evaluation_steps(task, session)
