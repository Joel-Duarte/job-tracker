import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.url_utils import normalize_job_url
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.schemas.llm import JobAssessmentResult
from app.services.domain_resolver import resolve_company_domain
from app.services.skill_normalizer import normalize_skills_list

logger = logging.getLogger(__name__)


async def persist_or_stage_job_assessment(
    db: AsyncSession,
    assessment: JobAssessmentResult,
    raw_text: str | None = None,
    job_url: str | None = None,
    force_new: bool = False,
    target_status: str = "ASSESSMENT",
    structured_spec: dict[str, Any] | None = None,
    target_application_id: int | None = None,
) -> dict[str, Any]:
    """
    Persists an AI job assessment to the database. If target_application_id is provided,
    updates the existing application's match payload and JobPosting without altering its active pipeline status.
    Otherwise creates a new application in target_status.
    """
    company_name = (assessment.company or "Unknown Company").strip()
    company_norm = company_name.lower()
    position_name = (assessment.position or "Unspecified Position").strip()
    position_norm = position_name.lower()
    clean_url = normalize_job_url(job_url)
    now = datetime.now(UTC)

    all_skills = normalize_skills_list(
        list(
            dict.fromkeys(
                (assessment.matching_skills or []) + (assessment.missing_skills or [])
            )
        )
    )

    # 1. Update Existing Target Application (if specified)
    if target_application_id:
        app_stmt = select(ApplicationModel).where(
            ApplicationModel.id == target_application_id
        )
        app_res = await db.execute(app_stmt)
        app_record = app_res.scalar_one_or_none()

        if app_record:
            if clean_url and not app_record.job_url:
                app_record.job_url = clean_url
            app_record.match_analysis_payload = assessment.model_dump()
            app_record.last_activity_at = now

            # Upsert JobPostingModel
            jp_stmt = select(JobPostingModel).where(
                JobPostingModel.application_id == app_record.id
            )
            jp_res = await db.execute(jp_stmt)
            job_posting = jp_res.scalar_one_or_none()

            if not job_posting:
                job_posting = JobPostingModel(
                    application_id=app_record.id,
                    job_url=clean_url or f"lead-{uuid.uuid4().hex[:8]}",
                    description_markdown=raw_text or assessment.summary,
                    salary_min=assessment.salary_min,
                    salary_max=assessment.salary_max,
                    currency=assessment.currency or "USD",
                    location=assessment.location,
                    work_model=assessment.work_model,
                    required_skills=all_skills,
                    structured_spec=structured_spec,
                )
                db.add(job_posting)
            else:
                if raw_text or assessment.summary:
                    job_posting.description_markdown = raw_text or assessment.summary
                if clean_url:
                    job_posting.job_url = clean_url
                if assessment.salary_min is not None:
                    job_posting.salary_min = assessment.salary_min
                if assessment.salary_max is not None:
                    job_posting.salary_max = assessment.salary_max
                if assessment.location:
                    job_posting.location = assessment.location
                if assessment.work_model:
                    job_posting.work_model = assessment.work_model
                if all_skills:
                    job_posting.required_skills = all_skills
                if structured_spec:
                    job_posting.structured_spec = structured_spec

            # Record Timeline Event
            event = ApplicationEventModel(
                email_application_id=app_record.id,
                email_conversation_id=f"lead-conv-{app_record.id}",
                email_event_type="JOB_EVALUATION",
                email_status_after_event=app_record.status,
                email_summary=assessment.summary
                or f"AI Job fit assessment completed for {app_record.position}.",
                email_received_at=now,
                source_channel="INTAKE",
                raw_payload=assessment.model_dump(),
            )
            db.add(event)
            await db.commit()
            await db.refresh(app_record)
            await db.refresh(event)

            logger.info(
                "Updated existing Application %d with AI job evaluation & spec",
                app_record.id,
            )
            return {"application_id": app_record.id, "event_id": event.id}

    # 2. Find or Create Company
    resolved_domain = await resolve_company_domain(
        company_name=company_name,
        source_url=clean_url,
        ai_domain=assessment.company_url,
    )

    comp_stmt = select(CompanyModel).where(CompanyModel.name_normalized == company_norm)
    comp_res = await db.execute(comp_stmt)
    company = comp_res.scalar_one_or_none()

    if not company:
        company = CompanyModel(
            name=company_name,
            name_normalized=company_norm,
            domain=resolved_domain,
        )
        db.add(company)
        await db.flush()
    elif not company.domain and resolved_domain:
        company.domain = resolved_domain
        await db.flush()

    # 3. Create Application
    app_record = ApplicationModel(
        company_id=company.id,
        position=position_name,
        position_normalized=position_norm,
        status=target_status or "ASSESSMENT",
        job_url=clean_url,
        application_date=now,
        last_activity_at=now,
    )
    db.add(app_record)
    await db.flush()

    # 4. Create Job Posting Record
    job_posting = JobPostingModel(
        application_id=app_record.id,
        job_url=clean_url or f"lead-{uuid.uuid4().hex[:8]}",
        description_markdown=raw_text or assessment.summary,
        salary_min=assessment.salary_min,
        salary_max=assessment.salary_max,
        currency=assessment.currency or "USD",
        location=assessment.location,
        work_model=assessment.work_model,
        required_skills=all_skills,
        structured_spec=structured_spec,
    )
    db.add(job_posting)

    # Save assessment payload directly to application row
    app_record.match_analysis_payload = assessment.model_dump()

    # 5. Create Assessment Timeline Event
    event = ApplicationEventModel(
        email_application_id=app_record.id,
        email_conversation_id=f"lead-conv-{app_record.id}",
        email_event_type="PRE_APPLICATION_ASSESSMENT",
        email_status_after_event=app_record.status,
        email_summary=assessment.summary
        or f"Pre-application AI assessment completed for {position_name} at {company_name}.",
        email_received_at=now,
        source_channel="INTAKE",
        raw_payload=assessment.model_dump(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(app_record)
    await db.refresh(event)

    # 6. Vector embedding generation is deferred during job assessment persistence in intake flows.
    logger.info(
        "Application %d created via intake job assessment; vector embedding deferred to application management lifecycle.",
        app_record.id,
    )

    logger.info(
        "Successfully persisted job assessment for '%s - %s' to Application %d",
        company_name,
        position_name,
        app_record.id,
    )

    return {
        "status": "success",
        "route": "commit",
        "is_application": True,
        "is_duplicate": False,
        "application_id": app_record.id,
        "company": company.name,
        "position": app_record.position,
        "event_id": event.id,
        "message": f"Job lead saved to pipeline under status '{app_record.status}'.",
        "assessment": assessment.model_dump(),
    }
