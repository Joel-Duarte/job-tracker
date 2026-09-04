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
from app.services.company_resolver import resolve_or_create_company
from app.services.domain_resolver import resolve_company_domain
from app.services.skill_normalizer import hybrid_extract_skills

logger = logging.getLogger(__name__)


def resolve_job_currency(
    extracted_currency: str | None, raw_text: str | None = None
) -> str:
    if extracted_currency:
        c = extracted_currency.strip().upper()
        if c in ["EUR", "€", "EURO", "EUROS"]:
            return "EUR"
        if c in ["GBP", "£", "POUND", "POUNDS"]:
            return "GBP"
        if c in ["USD", "$"]:
            return "USD"
        if c in ["CAD", "CA$"]:
            return "CAD"
        if c in ["AUD", "AU$"]:
            return "AUD"
        if c in ["CHF"]:
            return "CHF"
        if len(c) == 3:
            return c

    if raw_text:
        text_lower = raw_text.lower()
        if (
            "€" in raw_text
            or " eur " in text_lower
            or " euros" in text_lower
            or " euro " in text_lower
        ):
            return "EUR"
        if "£" in raw_text or " gbp " in text_lower or " pounds" in text_lower:
            return "GBP"
        if "$" in raw_text or " usd " in text_lower:
            return "USD"

    return "EUR"


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
    position_name = (assessment.position or "Unspecified Position").strip()
    position_norm = position_name.lower()
    clean_url = normalize_job_url(job_url)
    now = datetime.now(UTC)
    detected_currency = resolve_job_currency(
        assessment.currency, raw_text or assessment.summary
    )

    all_skills = hybrid_extract_skills(
        raw_text=raw_text or assessment.summary,
        llm_skills=(assessment.matching_skills or [])
        + (assessment.missing_skills or []),
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
            if target_status == "ASSESSMENT":
                app_record.is_assessment = True
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
                    currency=detected_currency,
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
                job_posting.currency = detected_currency
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
            comp_rec = (
                await db.get(CompanyModel, app_record.company_id)
                if app_record.company_id
                else None
            )
            return {
                "application_id": app_record.id,
                "event_id": event.id,
                "company_domain": comp_rec.domain if comp_rec else None,
            }

    # 2. Find or Create Company
    from app.services.domain_resolver import (
        clean_company_name,
        extract_organization_from_ats_url,
    )

    clean_name = clean_company_name(company_name)
    if not clean_name or clean_name.lower() in {
        "unknown",
        "careers",
        "team",
        "engineering",
        "not specified",
    }:
        ats_slug = extract_organization_from_ats_url(clean_url)
        if ats_slug:
            clean_name = ats_slug.title()

    resolved_domain = await resolve_company_domain(
        company_name=clean_name or company_name,
        source_url=clean_url,
        ai_domain=assessment.company_url,
        db=db,
    )

    company, _ = await resolve_or_create_company(
        db=db,
        company_name=clean_name or company_name,
        domain=resolved_domain,
    )

    # 3. Create Application
    app_record = ApplicationModel(
        company_id=company.id,
        position=position_name,
        position_normalized=position_norm,
        status=target_status or "ASSESSMENT",
        is_assessment=(target_status or "ASSESSMENT") == "ASSESSMENT",
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
        currency=detected_currency,
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
        "company_domain": company.domain,
        "position": app_record.position,
        "event_id": event.id,
        "message": f"Job lead saved to pipeline under status '{app_record.status}'.",
        "assessment": assessment.model_dump(),
    }
