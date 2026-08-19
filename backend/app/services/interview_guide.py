import json
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.applications import ApplicationModel
from app.models.candidate_profile import CandidateCVModel
from app.schemas.applications import GenerateInterviewGuideRequest
from app.services.interview_guide_graph import interview_guide_graph
from app.services.postgres_tracer import PostgresTracer

logger = logging.getLogger(__name__)


async def generate_interview_guide(
    db: AsyncSession,
    application_id: int,
    request: GenerateInterviewGuideRequest,
) -> ApplicationModel:
    """
    Coordinates candidate profile retrieval, job posting lookup, LangGraph execution,
    and persistence of the tailored Interview Preparation Guide.
    """
    # 1. Fetch Application with related Company and Job Posting
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            selectinload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.events),
        )
    )
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    company_name = application.company.name if application.company else "Target Company"
    position = application.position or "Target Role"

    # 2. Fetch Active Candidate Profile
    cv_stmt = select(CandidateCVModel).limit(1)
    cv_res = await db.execute(cv_stmt)
    active_cv = cv_res.scalars().first()

    cv_text = ""
    if active_cv:
        skills_str = ", ".join(active_cv.extracted_skills or [])
        domain_str = ", ".join(
            [
                f"{d.get('domain')} ({d.get('years')} yrs)"
                for d in (active_cv.domain_experience or [])
                if d.get("is_active", True)
            ]
        )
        cv_text = (
            f"Candidate Summary: {active_cv.summary or 'Experienced professional'}\n"
            f"Core Technical Skills: {skills_str}\n"
            f"Active Domain Experience: {domain_str}\n\n"
            f"Sanitized Resume Content:\n{active_cv.anonymized_text or active_cv.raw_text}"
        )
    else:
        cv_text = "Candidate background in software engineering and technical product delivery."

    # 3. Formulate Job Details
    jd_text = ""
    if application.job_posting and application.job_posting.description_markdown:
        req_skills = ", ".join(application.job_posting.required_skills or [])
        jd_text = (
            f"Position: {position} at {company_name}\n"
            f"Location / Work Model: {application.job_posting.location or 'Not Specified'} ({application.job_posting.work_model or 'Not Specified'})\n"
            f"Required Skills: {req_skills}\n\n"
            f"Job Description:\n{application.job_posting.description_markdown}"
        )
    else:
        # Fallback to recent event summaries or title
        event_notes = " | ".join(
            [e.email_summary for e in application.events if e.email_summary]
        )
        jd_text = f"Position: {position} at {company_name}.\nRecent Communications & Timeline: {event_notes or 'Active recruitment process.'}"

    # 4. Prepare Initial State & Invoke LangGraph
    initial_state = {
        "cv_text": cv_text,
        "jd_text": jd_text,
        "company_name": company_name,
        "position": position,
        "company_context": [],
        "target_sections": request.selected_sections,
        "current_section_index": 0,
        "completed_sections": [],
        "language": request.language,
        "error": None,
    }

    recursion_limit = max(5, min(request.recursion_limit, 100))
    logger.info(
        "Invoking LangGraph interview guide generator for app %d (%s at %s), sections: %s, recursion_limit: %d",
        application_id,
        position,
        company_name,
        request.selected_sections,
        recursion_limit,
    )

    final_state = await interview_guide_graph.ainvoke(
        initial_state,
        config={
            "recursion_limit": recursion_limit,
            "configurable": {"db": db, "thread_id": str(application_id)},
            "callbacks": [PostgresTracer()],
        },
    )

    completed_sections = final_state.get("completed_sections", [])
    combined_html = "\n\n".join(completed_sections)
    if not combined_html.strip():
        combined_html = f"<div class='guide-section'><h2>Interview Preparation Guide</h2><p>Preparation guide for {position} at {company_name}.</p></div>"

    # 5. Persist to Postgres
    application.interview_guide_html = combined_html
    application.interview_guide_language = request.language
    application.interview_guide_generated_at = datetime.now(UTC)
    application.interview_guide_preferences = request.model_dump()

    await db.commit()
    await db.refresh(application)

    return application


async def generate_interview_guide_stream(
    db: AsyncSession,
    application_id: int,
    request: GenerateInterviewGuideRequest,
):
    """
    Async generator that executes `interview_guide_graph.astream(...)` and yields
    Server-Sent Events (SSE) data chunks (`data: ...\n\n`), updating state in real-time
    and persisting the completed guide to Postgres at the end of the stream.
    """
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            selectinload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.events),
        )
    )
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()
    if not application:
        err_payload = json.dumps(
            {"error": f"Application ID {application_id} not found."}
        )
        yield f"data: {err_payload}\n\n"
        return

    company_name = application.company.name if application.company else "Target Company"
    position = application.position or "Target Role"

    cv_stmt = select(CandidateCVModel).limit(1)
    cv_res = await db.execute(cv_stmt)
    active_cv = cv_res.scalars().first()

    cv_text = ""
    if active_cv:
        skills_str = ", ".join(active_cv.extracted_skills or [])
        domain_str = ", ".join(
            [
                f"{d.get('domain')} ({d.get('years')} yrs)"
                for d in (active_cv.domain_experience or [])
                if d.get("is_active", True)
            ]
        )
        cv_text = (
            f"Candidate Summary: {active_cv.summary or 'Experienced professional'}\n"
            f"Core Technical Skills: {skills_str}\n"
            f"Active Domain Experience: {domain_str}\n\n"
            f"Sanitized Resume Content:\n{active_cv.anonymized_text or active_cv.raw_text}"
        )
    else:
        cv_text = "Candidate background in software engineering and technical product delivery."

    jd_text = ""
    if application.job_posting and application.job_posting.description_markdown:
        req_skills = ", ".join(application.job_posting.required_skills or [])
        jd_text = (
            f"Position: {position} at {company_name}\n"
            f"Location / Work Model: {application.job_posting.location or 'Not Specified'} ({application.job_posting.work_model or 'Not Specified'})\n"
            f"Required Skills: {req_skills}\n\n"
            f"Job Description:\n{application.job_posting.description_markdown}"
        )
    else:
        event_notes = " | ".join(
            [e.email_summary for e in application.events if e.email_summary]
        )
        jd_text = f"Position: {position} at {company_name}.\nRecent Communications & Timeline: {event_notes or 'Active recruitment process.'}"

    initial_state = {
        "cv_text": cv_text,
        "jd_text": jd_text,
        "company_name": company_name,
        "position": position,
        "company_context": [],
        "target_sections": request.selected_sections,
        "current_section_index": 0,
        "completed_sections": [],
        "language": request.language,
        "error": None,
    }

    recursion_limit = max(5, min(request.recursion_limit, 100))

    completed_sections = []
    async for event in interview_guide_graph.astream(
        initial_state,
        config={
            "recursion_limit": recursion_limit,
            "configurable": {"db": db, "thread_id": str(application_id)},
            "callbacks": [PostgresTracer()],
        },
    ):
        for node_name, state_update in event.items():
            if isinstance(state_update, dict) and "completed_sections" in state_update:
                completed_sections = state_update["completed_sections"]

            event_payload = {
                "step": node_name,
                "completed_sections_count": len(completed_sections),
                "total_target_sections": len(request.selected_sections),
                "latest_section": completed_sections[-1]
                if completed_sections
                else None,
            }
            yield f"data: {json.dumps(event_payload)}\n\n"

    combined_html = "\n\n".join(completed_sections)
    if not combined_html.strip():
        combined_html = f"<div class='guide-section'><h2>Interview Preparation Guide</h2><p>Preparation guide for {position} at {company_name}.</p></div>"

    application.interview_guide_html = combined_html
    application.interview_guide_language = request.language
    application.interview_guide_generated_at = datetime.now(UTC)
    application.interview_guide_preferences = request.model_dump()

    await db.commit()

    final_payload = {
        "type": "complete",
        "completed": True,
        "application_id": application_id,
        "interview_guide_html": combined_html,
        "interview_guide_language": request.language,
        "interview_guide_generated_at": application.interview_guide_generated_at.isoformat(),
    }
    yield f"data: {json.dumps(final_payload)}\n\n"


async def clear_interview_guide(
    db: AsyncSession, application_id: int
) -> ApplicationModel:
    """Clears the existing interview guide for an application."""
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            selectinload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.events),
        )
    )
    result = await db.execute(stmt)
    application = result.scalar_one_or_none()
    if not application:
        raise ValueError(f"Application with ID {application_id} not found.")

    application.interview_guide_html = None
    application.interview_guide_generated_at = None
    application.interview_guide_preferences = None

    await db.commit()
    await db.refresh(application)
    return application
