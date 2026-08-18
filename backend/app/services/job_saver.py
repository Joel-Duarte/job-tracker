import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.staging import StagingItemModel
from app.schemas.llm import JobAssessmentResult
from app.services.domain_resolver import resolve_company_domain
from app.services.llm import generate_and_save_application_embedding

logger = logging.getLogger(__name__)


async def persist_or_stage_job_assessment(
    db: AsyncSession,
    assessment: JobAssessmentResult,
    raw_text: str | None = None,
    job_url: str | None = None,
    force_new: bool = False,
    target_status: str = "ASSESSMENT",
) -> dict[str, Any]:
    """
    Persists an AI job assessment to the database in ASSESSMENT status.
    If an existing application for the normalized company and position (or matching URL) exists,
    routes to the Staging queue with match_reason="DUPLICATE_APPLICATION_FOUND" unless force_new=True.
    """
    company_name = (assessment.company or "Unknown Company").strip()
    company_norm = company_name.lower()
    position_name = (assessment.position or "Unspecified Position").strip()
    position_norm = position_name.lower()
    clean_url = job_url.strip() if job_url else None

    # 1. Check for Duplicate / Existing Application
    if not force_new:
        # Search by company + position or exact URL
        dup_query = (
            select(ApplicationModel)
            .join(CompanyModel, ApplicationModel.company_id == CompanyModel.id)
            .where(
                or_(
                    (CompanyModel.name_normalized == company_norm)
                    & (ApplicationModel.position_normalized == position_norm),
                    (ApplicationModel.job_url == clean_url) if clean_url else False,
                )
            )
        )
        dup_res = await db.execute(dup_query)
        existing_app = dup_res.scalars().first()

        if existing_app:
            logger.info(
                "Duplicate application detected for '%s' - '%s' (Application ID %d). Routing to Staging.",
                company_name,
                position_name,
                existing_app.id,
            )
            staging_item = StagingItemModel(
                email_subject=f"Duplicate Application Lead: {position_name} at {company_name}",
                email_raw_body=raw_text
                or assessment.summary
                or f"Job assessment for {position_name} at {company_name}",
                extracted_data=assessment.model_dump(),
                match_score=1.0,
                match_reason="DUPLICATE_APPLICATION_FOUND",
                status="PENDING",
            )
            db.add(staging_item)
            await db.commit()
            await db.refresh(staging_item)

            return {
                "status": "staged",
                "route": "staging",
                "is_duplicate": True,
                "staging_item_id": staging_item.id,
                "existing_application_id": existing_app.id,
                "company": company_name,
                "position": position_name,
                "message": f"Existing application found for '{company_name} - {position_name}'. Routed to Staging Queue for review.",
                "assessment": assessment.model_dump(),
            }

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
    now = datetime.now(UTC)
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
    all_skills = list(
        dict.fromkeys(
            (assessment.matching_skills or []) + (assessment.missing_skills or [])
        )
    )
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

    # 6. Generate Vector Embedding (Only when application is moved into active stages e.g. APPLIED, TECHNICAL_INTERVIEW, etc., never in ASSESSMENT)
    if app_record.status != "ASSESSMENT":
        try:
            await generate_and_save_application_embedding(
                db, app_record.id, skip_llm_summary=True
            )
        except Exception as err:
            logger.warning(
                "Vector embedding generation deferred for Application %d: %s",
                app_record.id,
                err,
            )
    else:
        logger.info(
            "Application %d is in ASSESSMENT stage; vector embedding deferred until moved to APPLIED.",
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
