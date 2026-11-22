import asyncio
import json
import logging
import os
import socket
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified

import app.core.database as db_module
from app.core.ai_queue import (
    concurrency_manager,
    get_worker_instance_id,
    is_shutting_down,
    is_task_running_locally,
    register_running_task,
    unregister_running_task,
)
from app.core.config_manager import get_setting
from app.core.url_utils import normalize_job_url
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.applications import ApplicationModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.system_settings import SystemSettingsModel
from app.schemas.llm import ExtractedJobSpec, JobAssessmentResult
from app.services.company_research import research_company_context
from app.services.job_saver import persist_or_stage_job_assessment
from app.services.llm import (
    anonymize_and_parse_cv,
    assess_job_posting,
    build_application_company_context,
    extract_job_spec,
    generate_application_answers,
    generate_cover_letter,
)
from app.services.llm_judge import audit_generation_grounding
from app.services.matcher import compute_programmatic_skill_match
from app.services.scraper import scrape_job_url, validate_job_content
from app.services.skill_normalizer import hybrid_extract_skills
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)

_company_research_semaphore: asyncio.Semaphore | None = None


def get_company_research_semaphore() -> asyncio.Semaphore:
    """Returns a process-wide semaphore limiting simultaneous company research tasks to 2."""
    global _company_research_semaphore
    if _company_research_semaphore is None:
        _company_research_semaphore = asyncio.Semaphore(2)
    return _company_research_semaphore


def _build_judge_target_context(
    company_name: str,
    position_name: str,
    job_desc: str | None,
    company_research: dict | None,
) -> str:
    """Builds separate target opportunity context so the judge does not flag company/role references."""
    parts = [f"Target Company: {company_name}", f"Target Position: {position_name}"]
    cr_ctx = build_application_company_context(company_research)
    if cr_ctx:
        parts.append(f"Company Research Facts:\n{cr_ctx}")
    if job_desc:
        parts.append(f"Job Description Excerpt:\n{job_desc[:1500]}")
    return "\n\n".join(parts)


async def _execute_application_qa_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    task_id = int(task.id)
    try:
        app_id = (task.result_json or {}).get("application_id")
        if not app_id and task.raw_text and task.raw_text.isdigit():
            app_id = int(task.raw_text)

        if not app_id:
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "No application_id found for APPLICATION_QA task."
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

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
            task.error_message = f"Application {app_id} not found."
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        # Fetch Candidate CV
        cv_stmt = select(CandidateCVModel).limit(1)
        cv_res = await db.execute(cv_stmt)
        active_cv = cv_res.scalars().first()

        cv_text = (active_cv.anonymized_text or active_cv.raw_text) if active_cv else ""
        company_name = app.company.name if app.company else ""
        position_name = app.position or ""
        job_desc = (
            app.job_posting.description_markdown
            if app.job_posting and app.job_posting.description_markdown
            else ""
        )

        task_result = task.result_json or {}
        questions_payload = (
            task_result.get("questions") or app.application_questions or []
        )
        tone_val = task_result.get("tone") or "professional"
        instructions_val = task_result.get("custom_instructions")
        include_research = task_result.get("include_company_research", True)
        company_research = task_result.get("company_research")

        if include_research and not company_research and app.company:
            try:
                task.stage = "RESEARCHING"
                await db.commit()

                from app.services.company_research import research_company_context

                company_research = await research_company_context(
                    company_name=company_name,
                    domain=app.company.domain,
                    company_id=app.company.id,
                    db=db,
                )
            except Exception as r_err:
                logger.warning(
                    "Failed to retrieve company research for %s in QA task: %s",
                    company_name,
                    r_err,
                )
                company_research = None

        task.stage = "ANSWERING"
        await db.commit()

        generated_qa = await generate_application_answers(
            db,
            company_name=company_name,
            position=position_name,
            job_description=job_desc,
            candidate_cv=cv_text,
            questions=questions_payload,
            tone=tone_val,
            custom_instructions=instructions_val,
            company_research=company_research,
        )

        sys_res = await db.execute(
            select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        )
        settings = sys_res.scalar_one_or_none()
        audit_summary = None

        if (
            settings
            and settings.enable_llm_judge
            and settings.llm_judge_audit_application_qa
        ):
            judge_target_ctx = _build_judge_target_context(
                company_name, position_name, job_desc, company_research
            )

            retries = 0
            while True:
                joined_text = "\n".join(
                    [
                        f"Q: {q.get('question', '')}\nA: {q.get('answer', '')}"
                        for q in generated_qa
                    ]
                )
                audit = await audit_generation_grounding(
                    db,
                    candidate_cv=cv_text,
                    generated_text=joined_text,
                    context_label=f"Application QA for {company_name}",
                    task_type="APPLICATION_QA",
                    target_context=judge_target_ctx,
                )
                audit_summary = audit.model_dump()

                if (
                    audit.passed
                    or settings.llm_judge_action != "auto_rewrite"
                    or retries >= settings.llm_judge_max_retries
                ):
                    break

                retries += 1
                feedback = (
                    f"PREVIOUS ATTEMPT FAILED GROUNDING AUDIT.\n"
                    f"Critique: {audit.critique}\n"
                    f"Unverified Claims to Fix/Remove: {', '.join(audit.unverified_claims)}\n"
                    f"Please rewrite the answers ensuring strict factual grounding against the CV."
                )
                new_instructions = (
                    (instructions_val + "\n\n" + feedback)
                    if instructions_val
                    else feedback
                )

                generated_qa = await generate_application_answers(
                    db,
                    company_name=company_name,
                    position=position_name,
                    job_description=job_desc,
                    candidate_cv=cv_text,
                    questions=questions_payload,
                    tone=tone_val,
                    custom_instructions=new_instructions,
                    company_research=company_research,
                )

        app.application_questions = generated_qa

        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        task.result_json = {
            "application_id": app.id,
            "company": company_name,
            "position": position_name,
            "tone": tone_val,
            "include_company_research": include_research,
            "company_research": company_research,
            "questions": generated_qa,
            "audit_summary": audit_summary,
        }
        task.completed_at = datetime.now(UTC)
        await db.commit()
        logger.info(
            "Application QA task %d completed successfully for app %d (%d questions answered)",
            task_id,
            app.id,
            len(generated_qa),
        )

    except Exception as err:
        logger.error(
            "Failed processing Application QA task %d: %s", task_id, err, exc_info=True
        )
        try:
            await db.rollback()
            refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
            target_task = (
                refreshed if isinstance(refreshed, IntakeEvaluationTaskModel) else task
            )
            target_task.status = "FAILED"
            target_task.stage = "FAILED"
            target_task.error_message = str(err)
            target_task.completed_at = datetime.now(UTC)
            await db.commit()
        except Exception as rollback_err:
            logger.error(
                "Error setting failure state for Application QA task %d: %s",
                task_id,
                rollback_err,
            )
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = str(err)
            task.completed_at = datetime.now(UTC)


async def _execute_cover_letter_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    task_id = int(task.id)
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
        cv_stmt = select(CandidateCVModel).limit(1)
        cv_res = await db.execute(cv_stmt)
        active_cv = cv_res.scalars().first()

        cv_text = (active_cv.anonymized_text or active_cv.raw_text) if active_cv else ""
        company_name = app.company.name if app.company else ""
        position_name = app.position or ""
        job_desc = (
            app.job_posting.description_markdown
            if app.job_posting and app.job_posting.description_markdown
            else ""
        )

        tone_val = (task.result_json or {}).get("tone") or "professional"
        length_val = (task.result_json or {}).get("length")
        instructions_val = (task.result_json or {}).get("custom_instructions")
        include_research = (task.result_json or {}).get(
            "include_company_research", True
        )
        company_research = (task.result_json or {}).get("company_research")

        if include_research and not company_research and app.company:
            try:
                company_research = await research_company_context(
                    company_name=company_name,
                    domain=app.company.domain,
                    company_id=app.company.id,
                    db=db,
                )
            except Exception as r_err:
                logger.warning(
                    "Failed to retrieve company research for %s: %s",
                    company_name,
                    r_err,
                )
                company_research = None

        cl_text = await generate_cover_letter(
            db,
            company_name=company_name,
            position=position_name,
            job_description=job_desc,
            candidate_cv=cv_text,
            tone=tone_val,
            length=length_val,
            custom_instructions=instructions_val,
            company_research=company_research,
        )

        sys_res = await db.execute(
            select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        )
        settings = sys_res.scalar_one_or_none()
        audit_summary = None

        if (
            settings
            and settings.enable_llm_judge
            and settings.llm_judge_audit_cover_letter
        ):
            judge_target_ctx = _build_judge_target_context(
                company_name, position_name, job_desc, company_research
            )

            retries = 0
            while True:
                audit = await audit_generation_grounding(
                    db,
                    candidate_cv=cv_text,
                    generated_text=cl_text,
                    context_label=f"Cover Letter for {company_name}",
                    task_type="COVER_LETTER",
                    target_context=judge_target_ctx,
                )
                audit_summary = audit.model_dump()

                if (
                    audit.passed
                    or settings.llm_judge_action != "auto_rewrite"
                    or retries >= settings.llm_judge_max_retries
                ):
                    break

                retries += 1
                feedback = (
                    f"PREVIOUS ATTEMPT FAILED GROUNDING AUDIT.\n"
                    f"Critique: {audit.critique}\n"
                    f"Unverified Claims to Fix/Remove: {', '.join(audit.unverified_claims)}\n"
                    f"You MUST rewrite the cover letter and strictly remove or correct these hallucinated claims to match the candidate's CV."
                )
                new_instructions = (
                    (instructions_val + "\n\n" + feedback)
                    if instructions_val
                    else feedback
                )

                cl_text = await generate_cover_letter(
                    db,
                    company_name=company_name,
                    position=position_name,
                    job_description=job_desc,
                    candidate_cv=cv_text,
                    tone=tone_val,
                    length=length_val,
                    custom_instructions=new_instructions,
                    company_research=company_research,
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
            "company_research": company_research,
            "tone": tone_val,
            "length": length_val,
            "audit_summary": audit_summary,
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
            task_id,
            app.id,
        )

    except Exception as err:
        logger.error(
            "Failed processing cover letter task %d: %s", task_id, err, exc_info=True
        )
        try:
            await db.rollback()
            refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
            target_task = (
                refreshed if isinstance(refreshed, IntakeEvaluationTaskModel) else task
            )
            target_task.status = "FAILED"
            target_task.stage = "FAILED"
            target_task.error_message = str(err)
            target_task.completed_at = datetime.now(UTC)
            await db.commit()
        except Exception as rollback_err:
            logger.error(
                "Error setting failure state for cover letter task %d: %s",
                task_id,
                rollback_err,
            )
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = str(err)
            task.completed_at = datetime.now(UTC)


async def _execute_cv_extraction_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    task_id = int(task.id)
    try:
        raw_text = task.raw_text
        if not raw_text or not raw_text.strip():
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "EMPTY_CV: Provided CV text is empty."
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        current_json = dict(task.result_json or {})
        checkpoint = dict(current_json.get("_checkpoint") or {})

        # Stage 1: SCRUBBING
        if not checkpoint.get("scrubbed"):
            task.stage = "SCRUBBING"
            checkpoint["scrubbed"] = True
            current_json["_checkpoint"] = checkpoint
            task.result_json = current_json
            await db.commit()

        # Stage 2: EXTRACTING
        extracted_data = checkpoint.get("extracted_data")
        if not extracted_data:
            task.stage = "EXTRACTING"
            await db.commit()

            anonymized_result = await anonymize_and_parse_cv(db, raw_text)
            extracted_data = anonymized_result.model_dump()
            checkpoint["extracted_data"] = extracted_data
            current_json["_checkpoint"] = checkpoint
            task.result_json = current_json
            await db.commit()

        # Stage 3: SAVING
        task.stage = "SAVING"
        await db.commit()

        # Delete previous active profiles
        from sqlalchemy import delete

        stmt_delete = delete(CandidateCVModel)
        await db.execute(stmt_delete)

        domain_breakdown = extracted_data.get("domain_breakdown") or []
        domain_expertise = extracted_data.get("domain_expertise") or []
        total_years = extracted_data.get("total_years_experience") or 0.0

        raw_breakdown = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in domain_breakdown
        ]
        if not raw_breakdown and domain_expertise:
            raw_breakdown = [
                {
                    "domain": d,
                    "years": max(
                        1.0,
                        round(
                            total_years / max(1, len(domain_expertise)),
                            1,
                        ),
                    ),
                    "is_active": True,
                }
                for d in domain_expertise
            ]

        final_skills = hybrid_extract_skills(
            raw_text=raw_text,
            llm_skills=extracted_data.get("extracted_skills"),
        )

        extracted_spoken_langs = extracted_data.get("spoken_languages") or []
        raw_spoken_languages = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in extracted_spoken_langs
        ]
        if not raw_spoken_languages:
            raw_spoken_languages = [{"language": "English", "proficiency": "Native"}]

        cv_record = CandidateCVModel(
            raw_text=raw_text,
            anonymized_text=extracted_data.get("anonymized_resume"),
            extracted_skills=final_skills,
            years_of_experience=total_years,
            domain_expertise=domain_expertise,
            domain_experience=raw_breakdown,
            spoken_languages=raw_spoken_languages,
            summary=extracted_data.get("summary"),
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
        logger.error("Failed processing CV task %d: %s", task_id, err, exc_info=True)
        try:
            await db.rollback()
            refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
            target_task = (
                refreshed if isinstance(refreshed, IntakeEvaluationTaskModel) else task
            )
            target_task.status = "FAILED"
            target_task.stage = "FAILED"
            target_task.error_message = str(err)
            target_task.completed_at = datetime.now(UTC)
            await db.commit()
        except Exception as rollback_err:
            logger.error(
                "Error setting failure state for CV task %d: %s", task_id, rollback_err
            )
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = str(err)
            task.completed_at = datetime.now(UTC)


async def _execute_role_alignment_dossier_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    task_id = int(task.id)
    try:
        from app.services.role_alignment_dossier_service import (
            enhance_role_alignment_dossier,
        )

        task.stage = "SYNTHESIZING"
        await db.commit()

        role_track = (
            (task.result_json or {}).get("role_track") or task.raw_text or "all"
        )

        dossier_res = await enhance_role_alignment_dossier(
            db=db, role_track=role_track, force_regenerate=True
        )

        task.status = "COMPLETED"
        task.stage = "COMPLETED"
        task.result_json = {
            "role_track": role_track,
            "dossier_id": dossier_res.id,
            "model_name": dossier_res.model_name,
            "executive_fit": dossier_res.dossier.executive_fit.model_dump(),
        }
        task.completed_at = datetime.now(UTC)
        await db.commit()
        logger.info(
            "Role alignment dossier task %d completed for track: %s",
            task.id,
            role_track,
        )

    except Exception as err:
        logger.error(
            "Failed processing role alignment dossier task %d: %s",
            task_id,
            err,
            exc_info=True,
        )
        try:
            await db.rollback()
            refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
            target_task = (
                refreshed if isinstance(refreshed, IntakeEvaluationTaskModel) else task
            )
            target_task.status = "FAILED"
            target_task.stage = "FAILED"
            target_task.error_message = str(err)
            target_task.completed_at = datetime.now(UTC)
            await db.commit()
        except Exception as rollback_err:
            logger.error(
                "Error setting failure state for dossier task %d: %s",
                task_id,
                rollback_err,
            )
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = str(err)
            task.completed_at = datetime.now(UTC)


async def _execute_company_research_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    task_id = int(task.id)
    try:
        from app.models.applications import CompanyModel
        from app.services.company_research import research_company_context

        current_data = dict(task.result_json or {})
        company_id = current_data.get("company_id")
        if not company_id and task.raw_text and task.raw_text.isdigit():
            company_id = int(task.raw_text)

        company_name = current_data.get("company_name") or task.title_hint
        domain = current_data.get("domain") or task.job_url
        about_url = current_data.get("about_url")

        # Load company record so we can track research_status lifecycle
        company_rec = await db.get(CompanyModel, company_id) if company_id else None

        # Stage 1: WEB_SEARCH — mark company as IN_PROGRESS so the UI shows a spinner
        task.stage = "WEB_SEARCH"
        if company_rec:
            company_rec.research_status = "IN_PROGRESS"
        await db.commit()

        # Stage 2: AI_SYNTHESIS
        task.stage = "AI_SYNTHESIS"
        await db.commit()

        # If the user provided an about_url via the company record, honour it
        # even if it wasn't stored in result_json (e.g. set after task was queued)
        if not about_url and company_rec and company_rec.about_url:
            about_url = company_rec.about_url

        async with get_company_research_semaphore():
            research_result = await research_company_context(
                company_name=company_name,
                domain=domain,
                company_id=company_id,
                force_refresh=True,
                db=db,
            )

        # Stage 3: COMPLETED
        # research_company_context already sets research_status=COMPLETED on the record;
        # we confirm task status here.
        task.status = "COMPLETED"
        task.stage = "COMPLETED"
        task.result_json = {
            "company_id": company_id,
            "company_name": company_name,
            "domain": domain,
            "about_url": about_url,
            "summary": research_result.get("summary"),
            "engineering_culture": research_result.get("engineering_culture"),
            "recent_initiatives": research_result.get("recent_initiatives"),
            "company_mission_and_customer": research_result.get(
                "company_mission_and_customer"
            ),
            "products_and_technical_domain": research_result.get(
                "products_and_technical_domain", []
            ),
            "strategic_priorities": research_result.get("strategic_priorities", []),
            "language_to_mirror": research_result.get("language_to_mirror", []),
            "verified_facts": research_result.get("verified_facts", []),
            "candidate_alignment_angles": research_result.get(
                "candidate_alignment_angles", []
            ),
            "employee_signals": research_result.get("employee_signals", []),
            "evidence_quality": research_result.get("evidence_quality"),
            "profile_links": research_result.get("profile_links", []),
            "sources": research_result.get("sources", []),
            "researched_at": research_result.get("researched_at"),
        }
        task.completed_at = datetime.now(UTC)
        await db.commit()
        logger.info("Company research task %d completed for %s", task_id, company_name)
    except Exception as err:
        logger.error(
            "Failed processing company research task %d: %s",
            task_id,
            err,
            exc_info=True,
        )
        try:
            await db.rollback()
            from app.models.applications import CompanyModel

            refreshed_task = await db.get(IntakeEvaluationTaskModel, task_id)
            target_task = (
                refreshed_task
                if isinstance(refreshed_task, IntakeEvaluationTaskModel)
                else task
            )
            target_task.status = "FAILED"
            target_task.stage = "FAILED"
            target_task.error_message = str(err)
            target_task.completed_at = datetime.now(UTC)

            # Belt-and-suspenders: also mark company record FAILED in case
            # research_company_context raised before it could do so itself
            current_data = dict(target_task.result_json or {})
            cid = current_data.get("company_id")
            if not cid and target_task.raw_text and target_task.raw_text.isdigit():
                cid = int(target_task.raw_text)
            if cid:
                failed_company = await db.get(CompanyModel, cid)
                if failed_company and failed_company.research_status not in (
                    "COMPLETED",
                ):
                    failed_company.research_status = "FAILED"

            await db.commit()
        except Exception as rollback_err:
            logger.error(
                "Error setting failure state for company research task %d: %s",
                task_id,
                rollback_err,
            )
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = str(err)
            task.completed_at = datetime.now(UTC)


async def _execute_email_sync_steps(
    task: IntakeEvaluationTaskModel, db: AsyncSession
) -> None:
    task_id = int(task.id)
    try:
        from app.schemas.intake import EmailPayload
        from app.services.intake import process_single_email_graph

        result_data = dict(task.result_json or {})
        emails_raw = result_data.get("emails") or []

        if not emails_raw and task.raw_text:
            try:
                parsed_json = json.loads(task.raw_text)
                if isinstance(parsed_json, list):
                    emails_raw = parsed_json
                elif isinstance(parsed_json, dict):
                    emails_raw = [parsed_json]
            except Exception:
                emails_raw = [
                    {
                        "subject": task.title_hint or "Pasted Email",
                        "body": task.raw_text,
                        "message_id": f"task-{task_id}",
                        "conversation_id": f"task-{task_id}",
                        "received_at": datetime.now(UTC).isoformat(),
                    }
                ]

        total = len(emails_raw)
        if total == 0:
            task.status = "COMPLETED"
            task.stage = "COMPLETE"
            task.result_json = {
                **result_data,
                "total_emails": 0,
                "processed_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "message": "No emails to process.",
            }
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        processed = 0
        applications_count = 0
        events_count = 0
        staged_count = 0
        skipped_duplicates = 0
        failed_count = 0
        details = []

        # Sort emails chronologically (oldest first -> newest last)
        def _get_email_sort_key(item: Any) -> datetime:
            rec = (
                item.get("received_at")
                if isinstance(item, dict)
                else getattr(item, "received_at", None)
            )
            if isinstance(rec, datetime):
                return rec if rec.tzinfo else rec.replace(tzinfo=UTC)
            if isinstance(rec, str):
                try:
                    dt = datetime.fromisoformat(rec.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
                except Exception:
                    pass
            return datetime.min.replace(tzinfo=UTC)

        emails_raw = sorted(emails_raw, key=_get_email_sort_key)

        task.status = "PROCESSING"
        task.stage = f"Processing 0 of {total} (0%)"
        await db.commit()

        for idx, email_dict in enumerate(emails_raw, start=1):
            await db.refresh(task)
            if task.status == "CANCELLED":
                logger.info(
                    "Email sync task %d was cancelled during processing.", task_id
                )
                return

            if isinstance(email_dict, dict):
                email_payload = EmailPayload.model_validate(
                    {
                        **email_dict,
                        "message_id": email_dict.get("message_id")
                        or f"sync-{task_id}-{idx}",
                        "conversation_id": email_dict.get("conversation_id")
                        or f"conv-{task_id}-{idx}",
                        "subject": email_dict.get("subject") or "No Subject",
                        "body": email_dict.get("body") or "",
                    }
                )
            elif isinstance(email_dict, EmailPayload):
                email_payload = email_dict
            else:
                continue

            pct = int((idx / total) * 100)
            task.stage = f"Processing {idx} of {total} ({pct}%)"
            result_data["current_subject"] = email_payload.subject
            result_data["processed_count"] = idx
            result_data["progress_pct"] = pct
            task.result_json = dict(result_data)
            flag_modified(task, "result_json")
            await db.commit()

            # Attempt graph execution with retry for transient LLM/network failures
            graph_res = None
            last_err = None
            max_attempts = 2

            for attempt in range(1, max_attempts + 1):
                try:
                    graph_res = await process_single_email_graph(
                        db, email_payload, str(task_id)
                    )
                    last_err = None
                    break
                except Exception as item_err:
                    await db.rollback()
                    last_err = item_err
                    if attempt < max_attempts:
                        logger.warning(
                            "Transient error on email '%s' (attempt %d/%d): %s. Retrying in 0.5s...",
                            email_payload.subject,
                            attempt,
                            max_attempts,
                            item_err,
                        )
                        await asyncio.sleep(0.5)

            if last_err is not None or graph_res is None:
                logger.error(
                    "Failed processing email '%s': %s",
                    email_payload.subject,
                    last_err,
                    exc_info=True,
                )
                failed_count += 1
                details.append(
                    {
                        "subject": email_payload.subject,
                        "sender": getattr(email_payload, "sender", None),
                        "status": "error",
                        "error": str(last_err),
                    }
                )
                continue

            processed += 1
            if graph_res.get("is_duplicate"):
                skipped_duplicates += 1
                details.append(
                    {
                        "subject": email_payload.subject,
                        "sender": getattr(email_payload, "sender", None),
                        "status": "skipped",
                        "reason": "duplicate",
                    }
                )
            elif graph_res.get("staging_item_id"):
                staged_count += 1
                details.append(
                    {
                        "subject": email_payload.subject,
                        "sender": getattr(email_payload, "sender", None),
                        "status": "staged",
                        "company": graph_res.get("company_name"),
                        "position": graph_res.get("position_name"),
                        "staging_item_id": graph_res.get("staging_item_id"),
                        "summary": (graph_res.get("extracted_data") or {}).get(
                            "summary"
                        ),
                    }
                )
            elif graph_res.get("is_application"):
                applications_count += 1
                details.append(
                    {
                        "subject": email_payload.subject,
                        "sender": getattr(email_payload, "sender", None),
                        "status": "application_committed",
                        "company": graph_res.get("company_name"),
                        "position": graph_res.get("position_name"),
                        "application_id": graph_res.get("application_id"),
                        "event_id": graph_res.get("event_id"),
                        "summary": (graph_res.get("extracted_data") or {}).get(
                            "summary"
                        ),
                    }
                )
            else:
                events_count += 1
                details.append(
                    {
                        "subject": email_payload.subject,
                        "sender": getattr(email_payload, "sender", None),
                        "status": "event_logged",
                        "event_id": graph_res.get("event_id"),
                        "summary": (graph_res.get("extracted_data") or {}).get(
                            "summary"
                        ),
                    }
                )

        task.status = "COMPLETED" if (failed_count < total or total == 0) else "FAILED"
        task.stage = "COMPLETE" if task.status == "COMPLETED" else "FAILED"
        if task.status == "FAILED" and details:
            task.error_message = next(
                (
                    d["error"]
                    for d in details
                    if d.get("status") == "error" and d.get("error")
                ),
                "All emails in batch failed processing.",
            )
        task.completed_at = datetime.now(UTC)
        task.result_json = {
            **result_data,
            "total_emails": total,
            "processed_count": processed,
            "applications_count": applications_count,
            "events_count": events_count,
            "staged_count": staged_count,
            "skipped_duplicates": skipped_duplicates,
            "failed_count": failed_count,
            "details": details,
            "progress_pct": 100,
        }
        flag_modified(task, "result_json")
        await db.commit()
        logger.info(
            "Email sync task %d finished: processed=%d, apps=%d, events=%d, staged=%d, failed=%d",
            task_id,
            processed,
            applications_count,
            events_count,
            staged_count,
            failed_count,
        )
    except Exception as err:
        logger.error("Email sync task %d failure: %s", task_id, err, exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        task.status = "FAILED"
        task.stage = "FAILED"
        task.error_message = str(err)
        task.completed_at = datetime.now(UTC)
        await db.commit()


def _resolve_worker_binding_type(task_type: str) -> str:
    if task_type in ["EMAIL_SYNC", "EMAIL_INTAKE"]:
        return "EMAIL_EXTRACTION"
    if task_type in ["APPLICATION_ASSESSMENT"]:
        return "JOB_ASSESSMENT"
    if task_type in ["SYSTEM_DESIGN_REVIEW", "SYSTEM_DESIGN_EVALUATION"]:
        return "SYSTEM_DESIGN_REVIEWER"
    if task_type in ["SYSTEM_DESIGN_CHALLENGE_GEN"]:
        return "SYSTEM_DESIGN_INTERVIEWER"
    return task_type


def _initial_stage_for_task(task_type: str | None) -> str:
    stage_map = {
        "CV_EXTRACTION": "SCRUBBING",
        "COVER_LETTER": "GENERATING",
        "ROLE_ALIGNMENT_DOSSIER": "SYNTHESIZING",
        "COMPANY_RESEARCH": "WEB_SEARCH",
        "EMAIL_SYNC": "PARSING",
        "EMAIL_INTAKE": "PARSING",
        "SYSTEM_DESIGN_REVIEW": "ANALYZING",
        "SYSTEM_DESIGN_EVALUATION": "ANALYZING",
        "SYSTEM_DESIGN_CHALLENGE_GEN": "GENERATING",
    }
    return stage_map.get(task_type or "", "FETCHING")


_CLAIM_LOCK = asyncio.Lock()
_IN_PROCESS_CLAIMED: set[int] = set()
_TRANSIENT_RETRY_DELAYS: tuple[float, ...] = (0.5, 1.5)


class _TaskCancelledError(Exception):
    """Raised when a task is found CANCELLED in the DB between worker steps."""


def _resume_stage_for_task(
    task_type: str | None, result_json: dict[str, Any] | None
) -> str:
    """Choose the next non-completed stage for a checkpointed task on retry/recovery."""
    checkpoint = (
        result_json.get("_checkpoint")
        if isinstance(result_json, dict)
        and isinstance(result_json.get("_checkpoint"), dict)
        else {}
    )
    completed = set(str(s) for s in (checkpoint.get("completed_steps") or []))
    if task_type == "SYSTEM_DESIGN_REVIEW":
        return "SAVING" if "ANALYZING" in completed else "ANALYZING"
    if task_type == "SYSTEM_DESIGN_EVALUATION":
        return "SAVING" if "EVALUATING" in completed else "ANALYZING"
    if task_type == "SYSTEM_DESIGN_CHALLENGE_GEN":
        return "SAVING" if "GENERATING" in completed else "GENERATING"
    return _initial_stage_for_task(task_type)


DEFAULT_LEASE_TTL_SECONDS = 60
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15.0


class _LeaseLostError(Exception):
    """Raised when a worker loses task ownership/lease before or during execution."""


def _parse_iso_ts(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _is_transient_ai_error(exc: Exception) -> bool:
    """Classify transient provider/network/rate-limit failures vs permanent validation errors."""
    if isinstance(
        exc,
        (
            ValueError,
            FileNotFoundError,
            LookupError,
            PermissionError,
            json.JSONDecodeError,
            _TaskCancelledError,
            _LeaseLostError,
            asyncio.CancelledError,
        ),
    ):
        return False
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
        return True
    msg = str(exc).lower()
    permanent_markers = (
        "validation",
        "not found",
        "requires ",
        "already completed",
        "locked before",
        "must not be",
        "missing at",
    )
    if any(marker in msg for marker in permanent_markers):
        return False
    transient_markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "timeout",
        "timed out",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "connection error",
        "connecterror",
        "connection refused",
        "server disconnected",
        "remoteprotocolerror",
        "apiconnectionerror",
        "service unavailable",
    )
    return any(marker in msg for marker in transient_markers)


def _ensure_checkpoint_meta(
    task: IntakeEvaluationTaskModel,
    *,
    increment_attempt: bool = False,
    worker_id: str | None = None,
) -> dict[str, Any]:
    """Ensure task.result_json['_checkpoint'] contains consistent durability & telemetry metadata."""
    now_iso = datetime.now(UTC).isoformat()
    payload = dict(task.result_json or {})
    existing = payload.get("_checkpoint")
    checkpoint = dict(existing) if isinstance(existing, dict) else {}
    checkpoint.setdefault("completed_steps", [])
    checkpoint.setdefault("step_attempts", {})
    checkpoint.setdefault("step_timestamps", {})
    checkpoint.setdefault("attempt_count", 0)
    checkpoint["last_activity_at"] = now_iso
    checkpoint["worker_host"] = socket.gethostname()
    checkpoint["worker_pid"] = os.getpid()
    checkpoint["worker_instance_id"] = worker_id or get_worker_instance_id()
    if increment_attempt:
        checkpoint["attempt_count"] = int(checkpoint["attempt_count"]) + 1
    payload["_checkpoint"] = checkpoint
    task.result_json = payload
    flag_modified(task, "result_json")
    return checkpoint


def _acquire_lease_on_checkpoint(
    task: IntakeEvaluationTaskModel,
    worker_id: str,
    *,
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
    increment_attempt: bool = False,
) -> dict[str, Any]:
    """Record ownership lease metadata in task.result_json['_checkpoint']."""
    now = datetime.now(UTC)
    now_iso = now.isoformat()
    expires_iso = (now + timedelta(seconds=ttl_seconds)).isoformat()
    checkpoint = _ensure_checkpoint_meta(
        task, increment_attempt=increment_attempt, worker_id=worker_id
    )
    checkpoint["lease_owner"] = worker_id
    checkpoint["lease_acquired_at"] = now_iso
    checkpoint["heartbeat_at"] = now_iso
    checkpoint["lease_expires_at"] = expires_iso
    checkpoint["lease_ttl_seconds"] = int(ttl_seconds)
    flag_modified(task, "result_json")
    return checkpoint


def _clear_lease_on_checkpoint(task: IntakeEvaluationTaskModel) -> dict[str, Any]:
    """Clear active lease ownership metadata from task.result_json['_checkpoint']."""
    payload = dict(task.result_json or {})
    existing = payload.get("_checkpoint")
    if not isinstance(existing, dict):
        return {}
    checkpoint = dict(existing)
    checkpoint["lease_owner"] = None
    checkpoint["lease_expires_at"] = None
    payload["_checkpoint"] = checkpoint
    task.result_json = payload
    flag_modified(task, "result_json")
    return checkpoint


async def renew_task_lease(
    task_id: int,
    worker_id: str,
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
    session_factory: Any = None,
) -> bool:
    """Renew an active PROCESSING task lease only if this worker_id still owns it."""
    factory = session_factory or db_module.AsyncSessionLocal
    async with factory() as session:
        stmt = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.id == task_id
        )
        if session.bind and session.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()
        task = (await session.execute(stmt)).scalar_one_or_none()
        if not task or task.status != "PROCESSING":
            return False
        payload = dict(task.result_json or {})
        existing = payload.get("_checkpoint")
        checkpoint = dict(existing) if isinstance(existing, dict) else {}
        if checkpoint.get("lease_owner") != worker_id:
            return False
        now = datetime.now(UTC)
        now_iso = now.isoformat()
        checkpoint["heartbeat_at"] = now_iso
        checkpoint["last_activity_at"] = now_iso
        checkpoint["lease_expires_at"] = (
            now + timedelta(seconds=ttl_seconds)
        ).isoformat()
        checkpoint["lease_ttl_seconds"] = int(ttl_seconds)
        payload["_checkpoint"] = checkpoint
        task.result_json = payload
        flag_modified(task, "result_json")
        await session.commit()
        return True


async def _lease_heartbeat_loop(
    task_id: int,
    worker_id: str,
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
    interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
) -> None:
    """Periodically renew the worker's PostgreSQL lease while a task is in flight."""
    while not is_shutting_down():
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break
        if is_shutting_down():
            break
        try:
            renewed = await renew_task_lease(
                task_id, worker_id, ttl_seconds=ttl_seconds
            )
            if not renewed:
                logger.warning(
                    "Worker %s lost lease renewal for task %d; stopping heartbeat.",
                    worker_id,
                    task_id,
                )
                break
        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.warning(
                "Heartbeat renewal error for task %d (worker %s): %s",
                task_id,
                worker_id,
                err,
            )


async def _assert_not_cancelled(task_id: int, db: AsyncSession) -> None:
    """Query fresh DB task status and abort cleanly if the user cancelled the task."""
    status_val = (
        await db.execute(
            select(IntakeEvaluationTaskModel.status).where(
                IntakeEvaluationTaskModel.id == task_id
            )
        )
    ).scalar_one_or_none()
    if status_val == "CANCELLED":
        raise _TaskCancelledError(f"Task {task_id} was cancelled in database.")


async def _assert_owns_lease(
    task_id: int,
    db: AsyncSession,
    worker_id: str | None = None,
    *,
    for_update: bool = False,
    allow_cancelled: bool = False,
) -> None:
    """Verify the task is still PROCESSING and owned by worker_id (optional row lock)."""
    stmt = select(
        IntakeEvaluationTaskModel.status, IntakeEvaluationTaskModel.result_json
    ).where(IntakeEvaluationTaskModel.id == task_id)
    if for_update and db.bind and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    row = (await db.execute(stmt)).first()
    if row is None:
        raise _LeaseLostError(f"Task {task_id} no longer exists.")
    status_val, result_json = row
    if status_val == "CANCELLED":
        if not allow_cancelled:
            raise _TaskCancelledError(f"Task {task_id} was cancelled in database.")
    elif status_val != "PROCESSING":
        raise _LeaseLostError(
            f"Task {task_id} is {status_val} (no longer PROCESSING); aborting stale worker."
        )
    cp = result_json.get("_checkpoint") if isinstance(result_json, dict) else None
    lease_owner = cp.get("lease_owner") if isinstance(cp, dict) else None
    if worker_id and lease_owner and lease_owner != worker_id:
        raise _LeaseLostError(
            f"Task {task_id} lease owned by {lease_owner}, not {worker_id}."
        )


async def _begin_step(
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    step_name: str,
    worker_id: str | None = None,
) -> dict[str, Any]:
    """Assert active lease ownership, record step start metadata, and commit stage transition."""
    await _assert_owns_lease(int(task.id), db, worker_id)
    now_iso = datetime.now(UTC).isoformat()
    checkpoint = _ensure_checkpoint_meta(task, worker_id=worker_id)
    timestamps = dict(checkpoint.get("step_timestamps") or {})
    entry = dict(timestamps.get(step_name) or {})
    entry["started_at"] = now_iso
    timestamps[step_name] = entry
    checkpoint["step_timestamps"] = timestamps
    checkpoint["current_step"] = step_name
    attempts = dict(checkpoint.get("step_attempts") or {})
    attempts[step_name] = int(attempts.get(step_name, 0)) + 1
    checkpoint["step_attempts"] = attempts
    task.stage = step_name
    flag_modified(task, "result_json")
    await db.commit()
    return checkpoint


async def _complete_step(
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    step_name: str,
    worker_id: str | None = None,
    **extra_checkpoint_fields: Any,
) -> dict[str, Any]:
    """Persist intermediate step outputs and mark step completed in _checkpoint."""
    await _assert_owns_lease(
        int(task.id), db, worker_id, for_update=True, allow_cancelled=True
    )
    now_iso = datetime.now(UTC).isoformat()
    checkpoint = _ensure_checkpoint_meta(task, worker_id=worker_id)
    completed = [str(s) for s in (checkpoint.get("completed_steps") or [])]
    if step_name not in completed:
        completed.append(step_name)
    checkpoint["completed_steps"] = completed
    timestamps = dict(checkpoint.get("step_timestamps") or {})
    entry = dict(timestamps.get(step_name) or {})
    entry["completed_at"] = now_iso
    timestamps[step_name] = entry
    checkpoint["step_timestamps"] = timestamps
    checkpoint["current_step"] = None
    for key, val in extra_checkpoint_fields.items():
        checkpoint[key] = val
    flag_modified(task, "result_json")
    await db.commit()
    return checkpoint


async def _run_with_transient_retry(
    task_id: int,
    step_name: str,
    coro_factory: Any,
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    worker_id: str | None = None,
) -> Any:
    """Run an AI/IO step with bounded backoff retries only on transient errors."""
    delays = _TRANSIENT_RETRY_DELAYS
    for attempt_idx in range(len(delays) + 1):
        await _assert_owns_lease(task_id, db, worker_id)
        try:
            return await coro_factory()
        except Exception as exc:
            if isinstance(exc, (_TaskCancelledError, asyncio.CancelledError)):
                raise
            if attempt_idx < len(delays) and _is_transient_ai_error(exc):
                delay = delays[attempt_idx]
                logger.warning(
                    "Transient error on task %d step %s (attempt %d/%d): %s. Retrying in %.2fs",
                    task_id,
                    step_name,
                    attempt_idx + 1,
                    len(delays) + 1,
                    exc,
                    delay,
                )
                try:
                    await db.rollback()
                    refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
                    if refreshed is not None:
                        cp = _ensure_checkpoint_meta(refreshed, increment_attempt=True)
                        attempts = dict(cp.get("step_attempts") or {})
                        attempts[step_name] = int(attempts.get(step_name, 0)) + 1
                        cp["step_attempts"] = attempts
                        cp["last_transient_error"] = str(exc)[:400]
                        flag_modified(refreshed, "result_json")
                        await db.commit()
                except Exception:
                    pass
                await asyncio.sleep(delay)
                continue
            raise


async def _handle_step_exception(
    task_id: int,
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    err: Exception,
    label: str,
) -> None:
    """Record FAILED cleanly while preserving _checkpoint unless cancelled."""
    if isinstance(err, _TaskCancelledError):
        logger.info("%s task %d aborted due to DB cancellation.", label, task_id)
        try:
            await db.rollback()
            refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
            if isinstance(refreshed, IntakeEvaluationTaskModel):
                await db.refresh(refreshed)
        except Exception:
            pass
        return

    if isinstance(err, _LeaseLostError):
        logger.warning(
            "%s task %d aborted due to lost lease ownership (%s); leaving DB untouched.",
            label,
            task_id,
            err,
        )
        try:
            await db.rollback()
        except Exception:
            pass
        return

    logger.error("Failed processing %s task %d: %s", label, task_id, err, exc_info=True)
    try:
        await db.rollback()
        refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
        target_task = (
            refreshed if isinstance(refreshed, IntakeEvaluationTaskModel) else task
        )
        if target_task.status == "CANCELLED":
            return
        cp = _ensure_checkpoint_meta(target_task)
        cp["last_error"] = str(err)[:500]
        _clear_lease_on_checkpoint(target_task)
        target_task.status = "FAILED"
        target_task.stage = "FAILED"
        target_task.error_message = str(err)
        target_task.completed_at = datetime.now(UTC)
        flag_modified(target_task, "result_json")
        await db.commit()
    except Exception as rollback_err:
        logger.error(
            "Error setting failure state for %s task %d: %s",
            label,
            task_id,
            rollback_err,
        )


async def _execute_system_design_review_steps(
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    *,
    worker_id: str | None = None,
) -> None:
    """Checkpointed 3-step pipeline for SYSTEM_DESIGN_REVIEW: PREPARING -> ANALYZING -> SAVING."""
    task_id = int(task.id)
    effective_worker_id = worker_id or get_worker_instance_id()
    try:
        payload = dict(task.result_json or {})
        session_id = payload.get("session_id")
        diagram_version = payload.get("diagram_version")
        if not session_id:
            _clear_lease_on_checkpoint(task)
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = "No session_id found for SYSTEM_DESIGN_REVIEW task."
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        from app.services.system_design_service import SystemDesignService

        checkpoint = _ensure_checkpoint_meta(task, worker_id=effective_worker_id)
        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))

        if "PREPARING" not in completed_steps or not checkpoint.get("prepared_ctx"):
            await _begin_step(task, db, "PREPARING", worker_id=effective_worker_id)
            prepared_ctx = await SystemDesignService.prepare_diagram_review_context(
                db,
                session_id=int(session_id),
                diagram_version=int(diagram_version)
                if diagram_version is not None
                else None,
                use_web_search=bool(payload.get("use_web_search", False)),
            )
            checkpoint = await _complete_step(
                task,
                db,
                "PREPARING",
                worker_id=effective_worker_id,
                prepared_ctx=prepared_ctx,
            )
        else:
            prepared_ctx = dict(checkpoint["prepared_ctx"])

        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))
        if "ANALYZING" not in completed_steps or not checkpoint.get("review_result"):
            await _begin_step(task, db, "ANALYZING", worker_id=effective_worker_id)
            inference_out = await _run_with_transient_retry(
                task_id,
                "ANALYZING",
                lambda: SystemDesignService.run_diagram_vlm_inference(db, prepared_ctx),
                task,
                db,
                worker_id=effective_worker_id,
            )
            review_result = inference_out["review"]
            provider_telemetry = inference_out["provider_telemetry"]
            checkpoint = await _complete_step(
                task,
                db,
                "ANALYZING",
                worker_id=effective_worker_id,
                review_result=review_result,
                provider_telemetry=provider_telemetry,
            )
        else:
            review_result = dict(checkpoint["review_result"])

        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))
        if "SAVING" not in completed_steps:
            await _begin_step(task, db, "SAVING", worker_id=effective_worker_id)
            await _assert_owns_lease(task_id, db, effective_worker_id, for_update=True)
            session = await SystemDesignService.persist_architecture_review(
                db, session_id=int(session_id), review_dict=review_result
            )
            checkpoint = await _complete_step(
                task,
                db,
                "SAVING",
                worker_id=effective_worker_id,
                reviews_count=len(session.architecture_reviews or []),
            )
        else:
            session = await SystemDesignService.get_session(db, int(session_id))

        await _assert_owns_lease(task_id, db, effective_worker_id, for_update=True)
        latest_payload = dict(task.result_json or payload)
        latest_payload["reviews_count"] = len(session.architecture_reviews or [])
        latest_payload["_checkpoint"] = checkpoint
        task.result_json = latest_payload
        _clear_lease_on_checkpoint(task)
        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        task.error_message = None
        task.completed_at = datetime.now(UTC)
        flag_modified(task, "result_json")
        await db.commit()
    except Exception as err:
        await _handle_step_exception(task_id, task, db, err, "system design review")


async def _execute_system_design_evaluation_steps(
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    *,
    worker_id: str | None = None,
) -> None:
    """Checkpointed 3-step pipeline for SYSTEM_DESIGN_EVALUATION: PREPARING -> EVALUATING -> SAVING."""
    task_id = int(task.id)
    effective_worker_id = worker_id or get_worker_instance_id()
    try:
        payload = dict(task.result_json or {})
        session_id = payload.get("session_id")
        if not session_id:
            _clear_lease_on_checkpoint(task)
            task.status = "FAILED"
            task.stage = "FAILED"
            task.error_message = (
                "No session_id found for SYSTEM_DESIGN_EVALUATION task."
            )
            task.completed_at = datetime.now(UTC)
            await db.commit()
            return

        from app.services.system_design_service import SystemDesignService

        checkpoint = _ensure_checkpoint_meta(task, worker_id=effective_worker_id)
        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))

        if "PREPARING" not in completed_steps or not checkpoint.get("prepared_ctx"):
            await _begin_step(task, db, "PREPARING", worker_id=effective_worker_id)
            prepared_ctx = await SystemDesignService.prepare_final_evaluation_context(
                db, session_id=int(session_id)
            )
            checkpoint = await _complete_step(
                task,
                db,
                "PREPARING",
                worker_id=effective_worker_id,
                prepared_ctx=prepared_ctx,
            )
        else:
            prepared_ctx = dict(checkpoint["prepared_ctx"])

        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))
        if "EVALUATING" not in completed_steps or not checkpoint.get(
            "evaluation_result"
        ):
            await _begin_step(task, db, "EVALUATING", worker_id=effective_worker_id)
            inference_out = await _run_with_transient_retry(
                task_id,
                "EVALUATING",
                lambda: SystemDesignService.run_final_evaluation_inference(
                    db, prepared_ctx
                ),
                task,
                db,
                worker_id=effective_worker_id,
            )
            evaluation_result = inference_out["evaluation"]
            provider_telemetry = inference_out["provider_telemetry"]
            checkpoint = await _complete_step(
                task,
                db,
                "EVALUATING",
                worker_id=effective_worker_id,
                evaluation_result=evaluation_result,
                provider_telemetry=provider_telemetry,
            )
        else:
            evaluation_result = dict(checkpoint["evaluation_result"])

        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))
        if "SAVING" not in completed_steps:
            await _begin_step(task, db, "SAVING", worker_id=effective_worker_id)
            await _assert_owns_lease(task_id, db, effective_worker_id, for_update=True)
            updated_session = await SystemDesignService.persist_final_evaluation(
                db,
                session_id=int(session_id),
                eval_dict=evaluation_result,
                idempotent_if_completed=True,
            )
            checkpoint = await _complete_step(
                task, db, "SAVING", worker_id=effective_worker_id
            )
        else:
            updated_session = await SystemDesignService.get_session(db, int(session_id))

        await _assert_owns_lease(task_id, db, effective_worker_id, for_update=True)
        latest_payload = dict(task.result_json or payload)
        latest_payload["overall_score"] = updated_session.overall_score
        latest_payload["readiness_rating"] = updated_session.readiness_rating
        latest_payload["final_evaluation"] = updated_session.final_evaluation
        latest_payload["_checkpoint"] = checkpoint
        task.result_json = latest_payload
        _clear_lease_on_checkpoint(task)
        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        task.error_message = None
        task.completed_at = datetime.now(UTC)
        flag_modified(task, "result_json")
        await db.commit()
    except Exception as err:
        await _handle_step_exception(task_id, task, db, err, "system design evaluation")


async def _execute_system_design_challenge_gen_steps(
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    *,
    worker_id: str | None = None,
) -> None:
    """Checkpointed 3-step pipeline for SYSTEM_DESIGN_CHALLENGE_GEN: PREPARING -> GENERATING -> SAVING."""
    task_id = int(task.id)
    effective_worker_id = worker_id or get_worker_instance_id()
    try:
        payload = dict(task.result_json or {})
        request_payload = dict(payload.get("request_payload") or {})

        from app.services.system_design_service import SystemDesignService

        checkpoint = _ensure_checkpoint_meta(task, worker_id=effective_worker_id)
        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))

        if "PREPARING" not in completed_steps or not checkpoint.get("prepared_ctx"):
            await _begin_step(task, db, "PREPARING", worker_id=effective_worker_id)
            prepared_ctx = await SystemDesignService.prepare_challenge_gen_context(
                db, request_payload
            )
            checkpoint = await _complete_step(
                task,
                db,
                "PREPARING",
                worker_id=effective_worker_id,
                prepared_ctx=prepared_ctx,
            )
        else:
            prepared_ctx = dict(checkpoint["prepared_ctx"])

        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))
        if "GENERATING" not in completed_steps or not checkpoint.get(
            "parsed_challenge"
        ):
            await _begin_step(task, db, "GENERATING", worker_id=effective_worker_id)
            inference_out = await _run_with_transient_retry(
                task_id,
                "GENERATING",
                lambda: SystemDesignService.run_challenge_gen_inference(
                    db, prepared_ctx
                ),
                task,
                db,
                worker_id=effective_worker_id,
            )
            parsed_challenge = inference_out["parsed"]
            provider_telemetry = inference_out["provider_telemetry"]
            checkpoint = await _complete_step(
                task,
                db,
                "GENERATING",
                worker_id=effective_worker_id,
                parsed_challenge=parsed_challenge,
                provider_telemetry=provider_telemetry,
            )
        else:
            parsed_challenge = dict(checkpoint["parsed_challenge"])

        completed_steps = set(str(s) for s in (checkpoint.get("completed_steps") or []))
        if "SAVING" not in completed_steps or not checkpoint.get("challenge_id"):
            await _begin_step(task, db, "SAVING", worker_id=effective_worker_id)
            await _assert_owns_lease(task_id, db, effective_worker_id, for_update=True)
            challenge = await SystemDesignService.persist_generated_challenge(
                db, prepared_ctx, parsed_challenge
            )
            checkpoint = await _complete_step(
                task,
                db,
                "SAVING",
                worker_id=effective_worker_id,
                challenge_id=int(challenge.id),
                challenge_slug=str(challenge.slug),
            )
        else:
            challenge = None

        await _assert_owns_lease(task_id, db, effective_worker_id, for_update=True)
        latest_payload = dict(task.result_json or payload)
        latest_payload["challenge_id"] = int(
            checkpoint.get("challenge_id") or (challenge.id if challenge else 0)
        )
        latest_payload["challenge_slug"] = str(
            checkpoint.get("challenge_slug") or (challenge.slug if challenge else "")
        )
        latest_payload["_checkpoint"] = checkpoint
        task.result_json = latest_payload
        _clear_lease_on_checkpoint(task)
        task.status = "COMPLETED"
        task.stage = "COMPLETE"
        task.error_message = None
        task.completed_at = datetime.now(UTC)
        flag_modified(task, "result_json")
        await db.commit()
    except Exception as err:
        await _handle_step_exception(
            task_id, task, db, err, "system design challenge generation"
        )


async def _execute_evaluation_steps(
    task: IntakeEvaluationTaskModel,
    db: AsyncSession,
    *,
    worker_id: str | None = None,
) -> None:
    task_id = int(task.id)
    async with trace_operation(
        category="worker",
        name=f"worker_{task.task_type.lower()}",
        inputs={
            "task_id": task_id,
            "task_type": task.task_type,
            "job_url": task.job_url,
            "title_hint": task.title_hint,
        },
    ) as ctx:
        # Check if task was cancelled before starting execution steps
        await db.refresh(task)
        if task.status == "CANCELLED":
            logger.info("Task %d was cancelled before execution started.", task_id)
            ctx["outputs"] = {"status": "CANCELLED", "stage": "CANCELLED"}
            return

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

        if task.task_type == "APPLICATION_QA":
            await _execute_application_qa_steps(task, db)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type == "ROLE_ALIGNMENT_DOSSIER":
            await _execute_role_alignment_dossier_steps(task, db)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type in ["EMAIL_SYNC", "EMAIL_INTAKE"]:
            await _execute_email_sync_steps(task, db)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type == "COMPANY_RESEARCH":
            await _execute_company_research_steps(task, db)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type == "SYSTEM_DESIGN_REVIEW":
            await _execute_system_design_review_steps(task, db, worker_id=worker_id)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type == "SYSTEM_DESIGN_EVALUATION":
            await _execute_system_design_evaluation_steps(task, db, worker_id=worker_id)
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        if task.task_type == "SYSTEM_DESIGN_CHALLENGE_GEN":
            await _execute_system_design_challenge_gen_steps(
                task, db, worker_id=worker_id
            )
            ctx["outputs"] = {"status": task.status, "stage": task.stage}
            if task.status == "FAILED":
                ctx["error"] = task.error_message
            return

        try:
            current_json = dict(task.result_json or {})
            checkpoint = dict(current_json.get("_checkpoint") or {})

            content = task.raw_text or checkpoint.get("content")
            clean_job_url = normalize_job_url(task.job_url)
            min_job_text_chars = 100
            short_job_text_threshold = 400
            used_scraped_fallback = False

            stripped_content = content.strip() if content else ""
            needs_url_scrape = bool(clean_job_url) and (
                not stripped_content
                or len(stripped_content) < min_job_text_chars
                or (
                    len(stripped_content) < short_job_text_threshold
                    and not validate_job_content(stripped_content, min_matches=2)
                )
            )

            # Stage 1: Fetch URL if content is missing or appears to be an incomplete snippet
            if needs_url_scrape:
                task.stage = "FETCHING"
                await db.commit()

                scraped = await scrape_job_url(clean_job_url)
                if scraped.text and len(scraped.text.strip()) > len(stripped_content):
                    content = scraped.text
                    used_scraped_fallback = True
                    checkpoint["content"] = content
                    current_json["_checkpoint"] = checkpoint
                    task.result_json = dict(current_json)
                    flag_modified(task, "result_json")
                    await db.commit()

            if not content or not content.strip():
                task.status = "FAILED"
                task.stage = "FAILED"
                task.error_message = "SCRAPE_FAILED: Unable to scrape job portal automatically. Please provide job description text."
                task.completed_at = datetime.now(UTC)
                await db.commit()
                ctx["error"] = task.error_message
                ctx["outputs"] = {"status": task.status, "stage": task.stage}
                return

            if len(content.strip()) < min_job_text_chars:
                task.status = "FAILED"
                task.stage = "FAILED"
                task.error_message = (
                    f"SCRAPE_FAILED: Extracted job description is too short ({len(content.strip())} chars). "
                    "Please provide the full job description text."
                )
                task.completed_at = datetime.now(UTC)
                await db.commit()
                ctx["error"] = task.error_message
                ctx["outputs"] = {"status": task.status, "stage": task.stage}
                return

            # Lightweight Keyword Filtering Validation (only for scraped pages, skipped if user explicitly provided the JD text)
            is_user_provided_text = (
                bool(task.raw_text and task.raw_text.strip())
                and not used_scraped_fallback
            )
            if not is_user_provided_text and not validate_job_content(
                content, min_matches=2
            ):
                task.status = "FAILED"
                task.stage = "FAILED"
                task.error_message = "INVALID_JOB_CONTENT: Scraped page does not appear to be a job description."
                task.completed_at = datetime.now(UTC)
                await db.commit()
                ctx["error"] = task.error_message
                ctx["outputs"] = {"status": task.status, "stage": task.stage}
                return

            # Stage 2: Extract Specs
            spec_dict = checkpoint.get("structured_spec")
            if not spec_dict:
                task.stage = "EXTRACTING"
                await db.commit()

                job_spec = await extract_job_spec(
                    db,
                    content,
                    title_hint=task.title_hint,
                    page_title=current_json.get("page_title"),
                )
                if not job_spec.job_found:
                    if (
                        is_user_provided_text
                        and len(content.strip()) >= short_job_text_threshold
                    ):
                        # User explicitly pasted substantial text — trust their input and proceed
                        # even if the LLM didn't recognise it as a job posting.
                        logger.warning(
                            "Task %s: LLM returned job_found=False for user-provided text. "
                            "Trusting user input and proceeding with extraction.",
                            task.id,
                        )
                    else:
                        task.status = "FAILED"
                        task.stage = "FAILED"
                        task.error_message = "NO_JOB_FOUND: The scraped page or input text did not contain an active job description or vacancy. Please provide the full job description text."
                        task.completed_at = datetime.now(UTC)
                        await db.commit()
                        ctx["error"] = task.error_message
                        ctx["outputs"] = {"status": task.status, "stage": task.stage}
                        return

                if isinstance(job_spec, ExtractedJobSpec):
                    spec_dict = job_spec.model_dump()
                elif hasattr(job_spec, "model_dump") and callable(job_spec.model_dump):
                    res = job_spec.model_dump()
                    spec_dict = res if isinstance(res, dict) else {}
                elif isinstance(job_spec, dict):
                    spec_dict = job_spec
                else:
                    spec_dict = {}
                checkpoint["structured_spec"] = spec_dict
                current_json["_checkpoint"] = checkpoint
                task.result_json = dict(current_json)
                flag_modified(task, "result_json")
                await db.commit()

            # Stage 3: CV Keyword Overlap Matching
            match_info = checkpoint.get("match_info")
            candidate_skills = checkpoint.get("candidate_skills")
            active_domains_str = checkpoint.get("active_domains_str")
            candidate_cv_text = checkpoint.get("candidate_cv_text")

            if match_info is None or candidate_skills is None:
                task.stage = "MATCHING"
                await db.commit()

                cv_stmt = select(CandidateCVModel).limit(1)
                cv_res = await db.execute(cv_stmt)
                active_cv = cv_res.scalars().first()
                candidate_skills = active_cv.extracted_skills if active_cv else []

                # Deterministically compute skills and overlap using taxonomy regex & candidate mentions
                jd_skills_from_spec = (
                    spec_dict.get("extracted_skills") if spec_dict else None
                )
                match_info = compute_programmatic_skill_match(
                    candidate_skills, content, jd_required_skills=jd_skills_from_spec
                )

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

                candidate_cv_text = (
                    active_cv.anonymized_text or active_cv.raw_text
                    if active_cv
                    else None
                )

                candidate_spoken_langs_list = []
                if active_cv and active_cv.spoken_languages:
                    for sl in active_cv.spoken_languages:
                        if isinstance(sl, dict):
                            l_name = sl.get("language")
                            l_prof = sl.get("proficiency")
                            if l_name:
                                candidate_spoken_langs_list.append(
                                    f"{l_name} ({l_prof})" if l_prof else l_name
                                )
                        elif isinstance(sl, str):
                            candidate_spoken_langs_list.append(sl)

                candidate_spoken_langs_str = (
                    ", ".join(candidate_spoken_langs_list)
                    if candidate_spoken_langs_list
                    else "English (Native / Fluent)"
                )

                candidate_years_of_experience = (
                    active_cv.years_of_experience if active_cv else None
                )

                checkpoint["match_info"] = match_info
                checkpoint["candidate_skills"] = candidate_skills
                checkpoint["active_domains_str"] = active_domains_str
                checkpoint["candidate_cv_text"] = candidate_cv_text
                checkpoint["candidate_spoken_langs_str"] = candidate_spoken_langs_str
                checkpoint["candidate_years_of_experience"] = (
                    candidate_years_of_experience
                )
                current_json["_checkpoint"] = checkpoint
                task.result_json = dict(current_json)
                flag_modified(task, "result_json")
                await db.commit()

            # Stage 4: Qualitative AI Fit Assessment
            task.stage = "ASSESSING"
            await db.commit()

            # Prefer high-signal distilled job spec from Stage 2 over raw webpage HTML/markdown
            assessment_jd_input = content
            if spec_dict and (
                spec_dict.get("responsibilities") or spec_dict.get("requirements")
            ):
                distilled_parts = []
                if spec_dict.get("position"):
                    distilled_parts.append(f"Position: {spec_dict['position']}")
                if spec_dict.get("company"):
                    distilled_parts.append(f"Company: {spec_dict['company']}")
                if spec_dict.get("location"):
                    distilled_parts.append(f"Location: {spec_dict['location']}")
                if spec_dict.get("extracted_skills"):
                    distilled_parts.append(
                        f"Core ATS Skills: {', '.join(spec_dict['extracted_skills'])}"
                    )
                if spec_dict.get("responsibilities"):
                    distilled_parts.append(
                        "Key Responsibilities:\n"
                        + "\n".join(f"- {r}" for r in spec_dict["responsibilities"])
                    )
                if spec_dict.get("requirements"):
                    distilled_parts.append(
                        "Role Requirements:\n"
                        + "\n".join(f"- {r}" for r in spec_dict["requirements"])
                    )
                distilled_text = "\n\n".join(distilled_parts)
                if len(distilled_text.strip()) > 100:
                    assessment_jd_input = distilled_text

            assessment = await assess_job_posting(
                db,
                assessment_jd_input,
                candidate_skills=candidate_skills,
                candidate_cv=candidate_cv_text,
                candidate_domain_breakdown=active_domains_str,
                candidate_spoken_languages=checkpoint.get("candidate_spoken_langs_str"),
                candidate_years_of_experience=checkpoint.get(
                    "candidate_years_of_experience"
                ),
                programmatic_baseline=match_info.get("programmatic_score"),
                matched_skills_count=match_info.get("matched_count"),
                total_required_skills_count=match_info.get("total_required_count"),
                matching_skills=match_info.get("matching_skills"),
                missing_skills=match_info.get("missing_skills"),
            )

            # Guard against persona leakage ('Technical Bar') or workplace-mode leakage ('Hybrid')
            # in assessment.company by preferring the dedicated JD_EXTRACTION company when valid.
            if spec_dict:
                from app.services.domain_resolver import is_invalid_company_name

                spec_company = spec_dict.get("company")
                if spec_company and not is_invalid_company_name(spec_company):
                    if is_invalid_company_name(assessment.company):
                        assessment.company = str(spec_company).strip()
                spec_position = spec_dict.get("position")
                if spec_position and str(spec_position).strip().lower() not in {
                    "not specified",
                    "unknown",
                }:
                    if (
                        not assessment.position
                        or assessment.position.strip().lower()
                        in {
                            "not specified",
                            "unknown",
                            "unspecified position",
                        }
                    ):
                        assessment.position = str(spec_position).strip()

            task.stage = "SAVING"
            await db.commit()

            target_app_id = current_json.get("target_application_id")
            skip_cover_letter = current_json.get(
                "skip_cover_letter", bool(target_app_id)
            )

            # Persist to database
            save_result = await persist_or_stage_job_assessment(
                db=db,
                assessment=assessment,
                raw_text=content,
                job_url=clean_job_url,
                force_new=False,
                target_status="ASSESSMENT",
                structured_spec=spec_dict,
                target_application_id=target_app_id,
            )

            # Check cover letter automation criteria
            enable_auto = (
                False
                if skip_cover_letter
                else await get_setting("ENABLE_AUTO_COVER_LETTER", False, db=db)
            )
            threshold = await get_setting("COVER_LETTER_MATCH_THRESHOLD", 70, db=db)

            fit_score_val = float(
                assessment.fit_score if assessment.fit_score is not None else 0
            )
            score_pct = (
                fit_score_val * 100.0
                if (0.0 <= fit_score_val <= 1.0)
                else fit_score_val
            )

            cl_status = "SKIPPED"
            app_id = save_result.get("application_id")
            if enable_auto and app_id:
                if score_pct >= threshold:
                    task.stage = "COVER_LETTER"
                    await db.commit()
                    try:
                        cv_stmt = select(CandidateCVModel).limit(1)
                        cv_res = await db.execute(cv_stmt)
                        active_cv = cv_res.scalars().first()

                        cv_text = (
                            (active_cv.anonymized_text or active_cv.raw_text)
                            if active_cv
                            else ""
                        )
                        app_rec = await db.get(ApplicationModel, app_id)
                        company_research = None
                        if app_rec and app_rec.company_id:
                            from app.models.applications import CompanyModel

                            comp = await db.get(CompanyModel, app_rec.company_id)
                            if comp:
                                try:
                                    company_research = await research_company_context(
                                        company_name=comp.name,
                                        domain=comp.domain,
                                        company_id=comp.id,
                                        db=db,
                                    )
                                except Exception as c_err:
                                    logger.warning(
                                        "Could not fetch company research: %s",
                                        c_err,
                                    )

                        letter_text = await generate_cover_letter(
                            db,
                            company_name=assessment.company or "",
                            position=assessment.position or "",
                            job_description=content or "",
                            candidate_cv=cv_text,
                            company_research=company_research,
                        )

                        if app_rec:
                            app_rec.cover_letter_text = letter_text
                            app_rec.cover_letter_status = "GENERATED"
                            app_rec.cover_letter_generated_at = datetime.now(UTC)
                            await db.commit()
                        cl_status = "GENERATED"
                    except Exception as err:
                        logger.error(
                            "Failed auto cover letter generation in intake worker for app %s: %s",
                            app_id,
                            err,
                            exc_info=True,
                        )
                        app_rec = await db.get(ApplicationModel, app_id)
                        if app_rec:
                            app_rec.cover_letter_status = "FAILED"
                            await db.commit()
                        cl_status = "FAILED"

            # Completed Successfully
            task.status = "COMPLETED"
            task.stage = "COMPLETE"
            if isinstance(assessment, JobAssessmentResult):
                result_payload = assessment.model_dump()
            elif hasattr(assessment, "model_dump") and callable(assessment.model_dump):
                res = assessment.model_dump()
                result_payload = res if isinstance(res, dict) else {}
            elif isinstance(assessment, dict):
                result_payload = dict(assessment)
            else:
                result_payload = {}
            result_payload["application_id"] = save_result.get("application_id")
            result_payload["company_domain"] = save_result.get(
                "company_domain"
            ) or getattr(assessment, "company_url", None)
            result_payload["staging_item_id"] = save_result.get("staging_item_id")
            result_payload["is_duplicate"] = False
            result_payload["save_status"] = save_result.get("status")
            result_payload["cover_letter_status"] = cl_status
            if cl_status == "GENERATED":
                result_payload["cover_letter_note"] = (
                    "Cover letter generated successfully."
                )
            elif cl_status == "FAILED":
                result_payload["cover_letter_note"] = (
                    "Cover letter generation failed during pipeline execution."
                )
            else:
                result_payload["cover_letter_note"] = (
                    f"Cover letter generation skipped (auto_enabled={enable_auto}, "
                    f"score={score_pct:.1f}%, threshold={threshold}%)"
                )
            if target_app_id:
                result_payload["target_application_id"] = target_app_id
                result_payload["is_direct_application"] = True
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
                "Failed processing intake task %d: %s", task_id, err, exc_info=True
            )
            try:
                await db.rollback()
                refreshed = await db.get(IntakeEvaluationTaskModel, task_id)
                target_task = (
                    refreshed
                    if isinstance(refreshed, IntakeEvaluationTaskModel)
                    else task
                )
                target_task.status = "FAILED"
                target_task.stage = "FAILED"
                target_task.error_message = str(err)
                target_task.completed_at = datetime.now(UTC)
                await db.commit()
            except Exception as rollback_err:
                logger.error(
                    "Error setting failure state for intake task %d: %s",
                    task_id,
                    rollback_err,
                )
            ctx["error"] = str(err)
            ctx["outputs"] = {"status": "FAILED", "stage": "FAILED"}


_DISPATCHED_TASKS: set[asyncio.Task] = set()


async def _resolve_provider_concurrency(
    session: AsyncSession, task_type: str
) -> tuple[int | None, int]:
    """Resolve provider_id and max_concurrency for the target binding type."""
    target_binding_type = _resolve_worker_binding_type(task_type)
    binding_stmt = (
        select(AITaskBindingModel, AIProviderModel)
        .join(
            AIProviderModel,
            AITaskBindingModel.provider_id == AIProviderModel.id,
        )
        .where(
            AITaskBindingModel.task_type.in_([target_binding_type, "GLOBAL_DEFAULT"]),
            AITaskBindingModel.is_active,
            AIProviderModel.is_active,
        )
    )
    rows = (await session.execute(binding_stmt)).all()
    exact_row = next((r for r in rows if r[0].task_type == target_binding_type), None)
    global_row = next((r for r in rows if r[0].task_type == "GLOBAL_DEFAULT"), None)
    selected_row = exact_row or global_row or (rows[0] if rows else None)
    provider_id = selected_row[1].id if selected_row else None
    max_concurrency = selected_row[1].max_concurrency if selected_row else 1
    return (provider_id, max_concurrency)


async def _requeue_task_on_shutdown(
    task_id: int,
    db: AsyncSession | None = None,
    *,
    worker_id: str | None = None,
) -> None:
    """Re-queue an interrupted PROCESSING task on graceful shutdown if this worker still owns its lease."""
    try:
        if db is not None:
            try:
                await db.rollback()
            except Exception:
                pass
            t = await db.get(IntakeEvaluationTaskModel, task_id)
            if t and t.status == "PROCESSING":
                existing_cp = (
                    dict(t.result_json.get("_checkpoint"))
                    if isinstance(t.result_json, dict)
                    and isinstance(t.result_json.get("_checkpoint"), dict)
                    else {}
                )
                owner = existing_cp.get("lease_owner")
                if worker_id and owner and owner != worker_id:
                    return
                cp = _ensure_checkpoint_meta(t, worker_id=worker_id)
                cp["interrupted_by_shutdown_at"] = datetime.now(UTC).isoformat()
                _clear_lease_on_checkpoint(t)
                t.status = "QUEUED"
                t.stage = _resume_stage_for_task(t.task_type, t.result_json)
                t.error_message = "Paused cleanly during server shutdown; queued for automatic resume."
                t.completed_at = None
                flag_modified(t, "result_json")
                await db.commit()
            return

        async with db_module.AsyncSessionLocal() as recovery_session:
            stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.id == task_id
            )
            if (
                recovery_session.bind
                and recovery_session.bind.dialect.name == "postgresql"
            ):
                stmt = stmt.with_for_update(skip_locked=True)
            t = (await recovery_session.execute(stmt)).scalar_one_or_none()
            if t and t.status == "PROCESSING":
                existing_cp = (
                    dict(t.result_json.get("_checkpoint"))
                    if isinstance(t.result_json, dict)
                    and isinstance(t.result_json.get("_checkpoint"), dict)
                    else {}
                )
                owner = existing_cp.get("lease_owner")
                if worker_id and owner and owner != worker_id:
                    return
                cp = _ensure_checkpoint_meta(t, worker_id=worker_id)
                cp["interrupted_by_shutdown_at"] = datetime.now(UTC).isoformat()
                _clear_lease_on_checkpoint(t)
                t.status = "QUEUED"
                t.stage = _resume_stage_for_task(t.task_type, t.result_json)
                t.error_message = "Paused cleanly during server shutdown; queued for automatic resume."
                t.completed_at = None
                flag_modified(t, "result_json")
                await recovery_session.commit()
    except Exception as shutdown_err:
        logger.warning(
            "Error re-queuing task %d during shutdown: %s", task_id, shutdown_err
        )


async def _mark_task_cancelled(
    task_id: int,
    db: AsyncSession | None = None,
    *,
    worker_id: str | None = None,
) -> None:
    """Persist CANCELLED status cleanly when an in-flight task receives cancellation."""
    try:
        if db is not None:
            try:
                await db.rollback()
            except Exception:
                pass
            t = await db.get(IntakeEvaluationTaskModel, task_id)
            if t and t.status != "CANCELLED":
                existing_cp = (
                    dict(t.result_json.get("_checkpoint"))
                    if isinstance(t.result_json, dict)
                    and isinstance(t.result_json.get("_checkpoint"), dict)
                    else {}
                )
                owner = existing_cp.get("lease_owner")
                if worker_id and owner and owner != worker_id:
                    return
                _clear_lease_on_checkpoint(t)
                t.status = "CANCELLED"
                t.stage = "CANCELLED"
                t.error_message = "Task stopped by user"
                t.completed_at = datetime.now(UTC)
                await db.commit()
            return

        async with db_module.AsyncSessionLocal() as cancel_session:
            t = await cancel_session.get(IntakeEvaluationTaskModel, task_id)
            if t and t.status != "CANCELLED":
                existing_cp = (
                    dict(t.result_json.get("_checkpoint"))
                    if isinstance(t.result_json, dict)
                    and isinstance(t.result_json.get("_checkpoint"), dict)
                    else {}
                )
                owner = existing_cp.get("lease_owner")
                if worker_id and owner and owner != worker_id:
                    return
                _clear_lease_on_checkpoint(t)
                t.status = "CANCELLED"
                t.stage = "CANCELLED"
                t.error_message = "Task stopped by user"
                t.completed_at = datetime.now(UTC)
                await cancel_session.commit()
    except Exception as cancel_db_err:
        logger.warning(
            "Error recording cancelled state in DB for task %d: %s",
            task_id,
            cancel_db_err,
        )


async def process_evaluation_task(
    task_id: int,
    db: AsyncSession | None = None,
    *,
    worker_id: str | None = None,
) -> None:
    """
    Atomically claims and processes a single QUEUED evaluation task within
    the provider's configured concurrency limits, maintaining a renewable lease.
    """
    effective_worker_id = worker_id or get_worker_instance_id()
    async with _CLAIM_LOCK:
        if task_id in _IN_PROCESS_CLAIMED:
            logger.info(
                "Evaluation task %d is already claimed in this worker process; skipping duplicate run.",
                task_id,
            )
            return
        _IN_PROCESS_CLAIMED.add(task_id)

    curr_task = asyncio.current_task()
    if curr_task:
        register_running_task(task_id, curr_task)

    heartbeat_task: asyncio.Task[None] | None = None
    try:
        if db is not None:
            stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.id == task_id
            )
            if db.bind and db.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)
            task = (await db.execute(stmt)).scalar_one_or_none()

            if task and task.task_type == "EMBEDDING":
                logger.info("Skipping disabled embedding task %d", task_id)
                return

            if not task or task.status != "QUEUED":
                logger.info(
                    "Skipping intake task %d (not found or status=%s)",
                    task_id,
                    getattr(task, "status", None),
                )
                return

            task_type = task.task_type or "JOB_ASSESSMENT"
            provider_id, max_concurrency = await _resolve_provider_concurrency(
                db, task_type
            )
            task.status = "PROCESSING"
            if not task.stage or task.stage in ["QUEUED", "FAILED", "CANCELLED"]:
                task.stage = _resume_stage_for_task(task.task_type, task.result_json)
            _acquire_lease_on_checkpoint(
                task, effective_worker_id, increment_attempt=True
            )
            await db.commit()

            async with concurrency_manager.acquire(
                provider_id, max_concurrency, priority=1
            ):
                status_val = (
                    await db.execute(
                        select(IntakeEvaluationTaskModel.status).where(
                            IntakeEvaluationTaskModel.id == task_id
                        )
                    )
                ).scalar_one_or_none()
                if status_val == "CANCELLED":
                    return
                await _execute_evaluation_steps(task, db, worker_id=effective_worker_id)
                return

        async with db_module.AsyncSessionLocal() as session:
            stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.id == task_id
            )
            if session.bind and session.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)
            task = (await session.execute(stmt)).scalar_one_or_none()

            if task and task.task_type == "EMBEDDING":
                logger.info("Skipping disabled embedding task %d", task_id)
                return

            if not task or task.status != "QUEUED":
                logger.info(
                    "Skipping intake task %d (locked, missing, or status=%s)",
                    task_id,
                    getattr(task, "status", None),
                )
                return

            task_type = task.task_type or "JOB_ASSESSMENT"
            provider_id, max_concurrency = await _resolve_provider_concurrency(
                session, task_type
            )

            # Atomically transition QUEUED -> PROCESSING under the row lock before releasing
            task.status = "PROCESSING"
            if not task.stage or task.stage in ["QUEUED", "FAILED", "CANCELLED"]:
                task.stage = _resume_stage_for_task(task.task_type, task.result_json)
            _acquire_lease_on_checkpoint(
                task, effective_worker_id, increment_attempt=True
            )
            await session.commit()

        heartbeat_task = asyncio.create_task(
            _lease_heartbeat_loop(task_id, effective_worker_id)
        )

        # Acquire provider semaphore strictly bounding concurrent execution
        async with concurrency_manager.acquire(
            provider_id, max_concurrency, priority=1
        ):
            async with db_module.AsyncSessionLocal() as session:
                task = await session.get(IntakeEvaluationTaskModel, task_id)
                if not task or task.status != "PROCESSING":
                    return
                cp = (
                    dict(task.result_json.get("_checkpoint"))
                    if isinstance(task.result_json, dict)
                    and isinstance(task.result_json.get("_checkpoint"), dict)
                    else {}
                )
                if cp.get("lease_owner") != effective_worker_id:
                    logger.warning(
                        "Worker %s lost lease for task %d before execution started.",
                        effective_worker_id,
                        task_id,
                    )
                    return

                _acquire_lease_on_checkpoint(task, effective_worker_id)
                await session.commit()
                await _execute_evaluation_steps(
                    task, session, worker_id=effective_worker_id
                )
    except asyncio.CancelledError:
        if is_shutting_down():
            logger.info(
                "Evaluation task %d interrupted by graceful shutdown; re-queuing with checkpoint preserved.",
                task_id,
            )
            await _requeue_task_on_shutdown(
                task_id, db=db, worker_id=effective_worker_id
            )
        else:
            logger.info(
                "Evaluation task %d received in-flight cancellation signal.", task_id
            )
            await _mark_task_cancelled(task_id, db=db, worker_id=effective_worker_id)
        raise
    finally:
        if heartbeat_task is not None and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        unregister_running_task(task_id)
        async with _CLAIM_LOCK:
            _IN_PROCESS_CLAIMED.discard(task_id)


async def recover_and_dispatch_queue_tasks(
    session_factory: Any = None,
    *,
    startup: bool = False,
    stale_after_seconds: int = 300,
    dispatch_limit: int = 20,
) -> dict[str, Any]:
    """
    Recover orphaned PROCESSING tasks whose renewable lease has expired and dispatch QUEUED tasks.
    Uses SELECT ... FOR UPDATE SKIP LOCKED on PostgreSQL so sibling containers never collide.
    """
    if is_shutting_down():
        return {"recovered_count": 0, "dispatched_count": 0, "dispatched_task_ids": []}

    factory = session_factory or db_module.AsyncSessionLocal
    now = datetime.now(UTC)
    recovered_count = 0
    queued_ids_to_dispatch: list[int] = []

    async with factory() as session:
        proc_stmt = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.status == "PROCESSING",
            IntakeEvaluationTaskModel.task_type != "EMBEDDING",
        )
        if session.bind and session.bind.dialect.name == "postgresql":
            proc_stmt = proc_stmt.with_for_update(skip_locked=True)
        processing_tasks = (await session.execute(proc_stmt)).scalars().all()
        for task in processing_tasks:
            tid = int(task.id)
            if is_task_running_locally(tid) or tid in _IN_PROCESS_CLAIMED:
                continue

            cp = (
                dict(task.result_json.get("_checkpoint"))
                if isinstance(task.result_json, dict)
                and isinstance(task.result_json.get("_checkpoint"), dict)
                else {}
            )
            lease_expires_ts = _parse_iso_ts(cp.get("lease_expires_at"))
            should_recover = False
            if lease_expires_ts is not None:
                # Renewable lease is authoritative: only recover once lease genuinely expires.
                should_recover = now >= lease_expires_ts
            else:
                activity_ts = (
                    _parse_iso_ts(cp.get("last_activity_at")) or task.created_at
                )
                if activity_ts is not None and activity_ts.tzinfo is None:
                    activity_ts = activity_ts.replace(tzinfo=UTC)
                age_seconds = (
                    (now - activity_ts).total_seconds()
                    if activity_ts is not None
                    else 0.0
                )
                if startup or age_seconds >= float(stale_after_seconds):
                    should_recover = True

            if should_recover:
                updated_cp = _ensure_checkpoint_meta(task)
                updated_cp["recovery_count"] = (
                    int(updated_cp.get("recovery_count", 0)) + 1
                )
                updated_cp["last_recovered_at"] = now.isoformat()
                _clear_lease_on_checkpoint(task)
                task.status = "QUEUED"
                task.stage = _resume_stage_for_task(task.task_type, task.result_json)
                task.error_message = (
                    "Recovered interrupted task after lease expiry; resuming."
                )
                task.completed_at = None
                flag_modified(task, "result_json")
                recovered_count += 1

        if recovered_count:
            await session.commit()

        queued_stmt = (
            select(IntakeEvaluationTaskModel)
            .where(
                IntakeEvaluationTaskModel.status == "QUEUED",
                IntakeEvaluationTaskModel.task_type != "EMBEDDING",
            )
            .order_by(
                IntakeEvaluationTaskModel.created_at.asc(),
                IntakeEvaluationTaskModel.id.asc(),
            )
            .limit(dispatch_limit)
        )
        queued_tasks = (await session.execute(queued_stmt)).scalars().all()
        for qtask in queued_tasks:
            qtid = int(qtask.id)
            if is_task_running_locally(qtid) or qtid in _IN_PROCESS_CLAIMED:
                continue
            queued_ids_to_dispatch.append(qtid)

    for qtid in queued_ids_to_dispatch:
        bg_task = asyncio.create_task(process_evaluation_task(qtid))
        _DISPATCHED_TASKS.add(bg_task)
        bg_task.add_done_callback(_DISPATCHED_TASKS.discard)

    if recovered_count or queued_ids_to_dispatch:
        logger.info(
            "Queue recovery/dispatcher pass (startup=%s): recovered=%d, dispatched=%s",
            startup,
            recovered_count,
            queued_ids_to_dispatch,
        )
    return {
        "recovered_count": recovered_count,
        "dispatched_count": len(queued_ids_to_dispatch),
        "dispatched_task_ids": queued_ids_to_dispatch,
    }


async def queue_recovery_and_dispatcher_loop(
    session_factory: Any = None,
    *,
    poll_interval_seconds: float = 3.0,
    stale_after_seconds: int = 300,
) -> None:
    """Background loop that recovers orphaned tasks at startup and periodically dispatches QUEUED work."""
    first_pass = True
    while not is_shutting_down():
        try:
            await recover_and_dispatch_queue_tasks(
                session_factory=session_factory,
                startup=first_pass,
                stale_after_seconds=stale_after_seconds,
            )
            first_pass = False
        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.error("Queue recovery/dispatcher loop error: %s", err, exc_info=True)
            first_pass = False

        try:
            await asyncio.sleep(poll_interval_seconds)
        except asyncio.CancelledError:
            break
