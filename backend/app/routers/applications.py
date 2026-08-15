from datetime import date, datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.models.applications import (
    ActionItemModel,
    ApplicationEmbeddingModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.schemas.applications import (
    ActionItemDetail,
    AllowedApplicationStatus,
    ApplicationByStatusResult,
    ApplicationDetailResponse,
    ApplicationEventDetail,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationTransitionRequest,
    ApplicationUpdate,
    CompanySummary,
    EventSummary,
    GenerateInterviewGuideRequest,
    JobPostingDetail,
)
from app.services.interview_guide import clear_interview_guide, generate_interview_guide
from app.services.llm import async_enqueue_application_embedding, generate_and_save_application_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List applications with filtering and search",
)
async def list_applications(
    q: Optional[str] = Query(None, description="Search position or company name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    action_required: Optional[bool] = Query(None, description="Filter by pending action required"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    sort_by: str = Query("last_activity_at", pattern="^(last_activity_at|application_date|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Base query joining company and events
    stmt = (
        select(ApplicationModel)
        .join(ApplicationModel.company)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.action_items),
        )
    )

    # Apply filters
    if q:
        search_pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(ApplicationModel.position).like(search_pattern),
                func.lower(CompanyModel.name).like(search_pattern),
            )
        )

    if status_filter:
        stmt = stmt.where(ApplicationModel.status == status_filter.upper())

    if company_id:
        stmt = stmt.where(ApplicationModel.company_id == company_id)

    if action_required is not None:
        event_subq = (
            select(ApplicationEventModel.email_application_id)
            .where(ApplicationEventModel.email_action_required == True)
        )
        action_item_subq = (
            select(ActionItemModel.application_id)
            .where(ActionItemModel.status == "PENDING")
        )
        if action_required:
            stmt = stmt.where(
                or_(
                    ApplicationModel.id.in_(event_subq),
                    ApplicationModel.id.in_(action_item_subq),
                )
            )
        else:
            stmt = stmt.where(
                ~ApplicationModel.id.in_(event_subq),
                ~ApplicationModel.id.in_(action_item_subq),
            )

    # Calculate total count before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply sorting and pagination
    sort_column = getattr(ApplicationModel, sort_by)
    stmt = stmt.order_by(sort_column.desc() if order == "desc" else sort_column.asc())
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    applications = result.scalars().unique().all()

    # Map database records to response format
    items = []
    for app in applications:
        latest_evt = app.events[0] if app.events else None
        has_pending_tasks = any(a.status == "PENDING" for a in (app.action_items or []))
        has_email_action = any(e.email_action_required for e in app.events)
        has_action = has_pending_tasks or has_email_action

        # Compute nearest pending due date across action items & payload deadlines
        due_dates = [
            a.due_date for a in (app.action_items or [])
            if a.status == "PENDING" and a.due_date is not None
        ]
        if latest_evt and latest_evt.raw_payload:
            payload_deadline = latest_evt.raw_payload.get("decision_deadline")
            if payload_deadline:
                try:
                    due_dates.append(datetime.fromisoformat(payload_deadline))
                except Exception:
                    pass

        nearest_due = min(due_dates) if due_dates else None

        # Compute match score from assessment event payload
        match_score = None
        for evt in (app.events or []):
            if evt.raw_payload and isinstance(evt.raw_payload, dict):
                score_val = (
                    evt.raw_payload.get("match_score")
                    or evt.raw_payload.get("fit_score")
                    or evt.raw_payload.get("overall_fit_score")
                )
                if score_val is not None:
                    try:
                        match_score = int(score_val)
                        break
                    except (ValueError, TypeError):
                        pass

        items.append(
            ApplicationListItem(
                id=app.id,
                company=CompanySummary(id=app.company.id, name=app.company.name, domain=app.company.domain),
                position=app.position,
                status=app.status,
                application_date=app.application_date,
                last_activity_at=app.last_activity_at,
                has_action_required=has_action,
                has_interview_guide=bool(app.interview_guide_html),
                match_score=match_score,
                nearest_due_date=nearest_due,
                latest_event=EventSummary(
                    id=latest_evt.id,
                    email_event_type=latest_evt.email_event_type,
                    email_subject=latest_evt.email_subject,
                    email_action_required=latest_evt.email_action_required,
                    email_action=latest_evt.email_action,
                    email_received_at=latest_evt.email_received_at,
                    raw_payload=latest_evt.raw_payload,
                )
                if latest_evt
                else None,
            )
        )

    return ApplicationListResponse(items=items, total=total, limit=limit, offset=offset)

@router.get(
    "/by-status",
    response_model=List[ApplicationByStatusResult],
    summary="Get applications matching a specific status with event metrics",
)
async def get_applications_by_status(
    status: AllowedApplicationStatus = Query(
        ...,
        description="Must be APPLIED, REJECTED, ONLINE_ASSESSMENT, or TECHNICAL_INTERVIEW",
    ),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
):
    """Replicates the status search CTE query to fetch applications, event counts, and latest email dates."""
    stmt = (
        select(
            ApplicationModel.id.label("application_id"),
            CompanyModel.name.label("company"),
            ApplicationModel.position,
            ApplicationModel.status,
            ApplicationModel.updated_at.label("application_updated"),
            func.count(func.distinct(ApplicationEventModel.id)).label("event_count"),
            func.max(ApplicationEventModel.email_received_at).label("latest_email"),
        )
        .join(CompanyModel, CompanyModel.id == ApplicationModel.company_id)
        .outerjoin(
            ApplicationEventModel,
            ApplicationEventModel.email_application_id == ApplicationModel.id,
        )
        .outerjoin(
            ApplicationEmbeddingModel,
            ApplicationEmbeddingModel.email_application_id == ApplicationModel.id,
        )
        .where(ApplicationModel.status == status.value)
        .group_by(
            ApplicationModel.id,
            CompanyModel.name,
            ApplicationModel.position,
            ApplicationModel.status,
            ApplicationModel.updated_at,
            ApplicationEmbeddingModel.email_application_id,
        )
        .order_by(ApplicationModel.updated_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        ApplicationByStatusResult(
            application_id=row.application_id,
            company=row.company,
            position=row.position,
            status=row.status,
            application_updated=row.application_updated,
            event_count=row.event_count,
            latest_email=row.latest_email,
        )
        for row in rows
    ]

@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get single application details",
)
async def get_application(application_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.action_items),
        )
    )
    result = await db.execute(stmt)
    app = result.scalars().first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    sorted_events = sorted(
        app.events or [],
        key=lambda e: (e.email_received_at or e.created_at),
        reverse=True,
    )
    latest_evt = sorted_events[0] if sorted_events else None
    has_action = any(e.email_action_required for e in app.events)

    return ApplicationDetailResponse(
        id=app.id,
        company=CompanySummary(id=app.company.id, name=app.company.name, domain=app.company.domain),
        position=app.position,
        status=app.status,
        application_date=app.application_date,
        last_activity_at=app.last_activity_at,
        has_action_required=has_action,
        has_interview_guide=bool(app.interview_guide_html),
        interview_guide_html=app.interview_guide_html,
        interview_guide_language=app.interview_guide_language,
        interview_guide_generated_at=app.interview_guide_generated_at,
        interview_guide_preferences=app.interview_guide_preferences,
        latest_event=EventSummary(
            id=latest_evt.id,
            email_event_type=latest_evt.email_event_type,
            email_subject=latest_evt.email_subject,
            email_action_required=latest_evt.email_action_required,
            email_action=latest_evt.email_action,
            email_received_at=latest_evt.email_received_at,
        )
        if latest_evt
        else None,
        external_job_id=app.external_job_id,
        job_url=app.job_url,
        application_key=app.application_key,
        created_at=app.created_at,
        updated_at=app.updated_at,
        events=[ApplicationEventDetail.model_validate(e) for e in sorted_events],
        job_posting=JobPostingDetail.model_validate(app.job_posting) if app.job_posting else None,
        action_items=[ActionItemDetail.model_validate(a) for a in (app.action_items or [])],
    )

@router.patch(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Partially update a job application",
)
async def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Partially updates a job application and enqueues background vector embedding refresh."""
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
        )
    )
    result = await db.execute(stmt)
    app = result.scalars().first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update.",
        )

    if "position" in update_data and update_data["position"] is not None:
        app.position_normalized = update_data["position"].strip().lower()

    for key, value in update_data.items():
        if hasattr(app, key):
            setattr(app, key, value)

    await db.commit()

    result = await db.execute(stmt)
    app = result.scalars().first()

    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    # Enqueue non-blocking background embedding generation (only if active stage, not ASSESSMENT)
    if app.status != "ASSESSMENT":
        background_tasks.add_task(async_enqueue_application_embedding, app.id, skip_llm_summary=True)

    latest_evt = app.events[0] if app.events else None
    has_action = any(e.email_action_required for e in app.events)

    return ApplicationDetailResponse(
        id=app.id,
        company=CompanySummary(
            id=app.company.id,
            name=app.company.name,
            domain=app.company.domain,
        ),
        position=app.position,
        status=app.status,
        application_date=app.application_date,
        last_activity_at=app.last_activity_at,
        has_action_required=has_action,
        latest_event=EventSummary(
            id=latest_evt.id,
            email_event_type=latest_evt.email_event_type,
            email_subject=latest_evt.email_subject,
            email_action_required=latest_evt.email_action_required,
            email_action=latest_evt.email_action,
            email_received_at=latest_evt.email_received_at,
        )
        if latest_evt
        else None,
        external_job_id=app.external_job_id,
        job_url=app.job_url,
        application_key=app.application_key,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.post(
    "/{application_id}/transition",
    response_model=ApplicationDetailResponse,
    summary="Transition application pipeline status and record structured timeline event",
)
async def transition_application(
    application_id: int,
    payload: ApplicationTransitionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Transitions application to a new column/stage (e.g. TECHNICAL_INTERVIEW, OFFER, REJECTED),
    records a structured ApplicationEventModel, sets ActionItemModel for deadlines, and enqueues embedding in background.
    """
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.job_posting),
        )
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    old_status = app.status
    new_status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    app.status = new_status
    now = datetime.now(timezone.utc)
    app.last_activity_at = now

    event_time = now

    # Update JobPosting if offered salary provided
    if payload.offered_salary is not None:
        if app.job_posting:
            app.job_posting.salary_min = payload.offered_salary
            app.job_posting.salary_max = payload.offered_salary
            if payload.currency:
                app.job_posting.currency = payload.currency
        else:
            jp = JobPostingModel(
                application_id=app.id,
                job_url=app.job_url or f"app-{app.id}",
                salary_min=payload.offered_salary,
                salary_max=payload.offered_salary,
                currency=payload.currency or "USD",
            )
            db.add(jp)

    # Construct human-readable event summary
    summary_parts = [f"Status changed from {old_status} to {new_status}."]
    if payload.interview_stage:
        summary_parts.append(f"Interview Phase: {payload.interview_stage}.")
    if payload.scheduled_at:
        summary_parts.append(f"Scheduled: {payload.scheduled_at.strftime('%b %d, %Y %I:%M %p')}.")
        # Create reminder Action Item
        action_item = ActionItemModel(
            application_id=app.id,
            title=f"Interview: {payload.interview_stage or 'Technical Round'} ({app.company.name})",
            due_date=payload.scheduled_at,
            urgency="HIGH",
        )
        db.add(action_item)
    elif new_status == "TECHNICAL_INTERVIEW":
        # Create action item to respond and schedule interview
        action_item = ActionItemModel(
            application_id=app.id,
            title=f"Schedule Interview / Reply with Availability ({app.company.name})",
            urgency="HIGH",
        )
        db.add(action_item)

    if payload.offered_salary:
        curr = payload.currency or "USD"
        summary_parts.append(f"Offered Compensation: {payload.offered_salary:,.0f} {curr}.")
    if payload.offer_received_date:
        summary_parts.append(f"Offer Received: {payload.offer_received_date.strftime('%b %d, %Y')}.")
    if payload.decision_deadline:
        summary_parts.append(f"Decision Deadline: {payload.decision_deadline.strftime('%b %d, %Y')}.")
        # Create decision deadline Action Item
        deadline_dt = datetime.combine(payload.decision_deadline, datetime.min.time(), tzinfo=timezone.utc)
        action_item = ActionItemModel(
            application_id=app.id,
            title=f"Respond to Offer: {app.company.name}",
            due_date=deadline_dt,
            urgency="HIGH",
        )
        db.add(action_item)

    if payload.rejection_date:
        summary_parts.append(f"Rejection Date: {payload.rejection_date.strftime('%b %d, %Y')}.")
        event_time = datetime.combine(payload.rejection_date, datetime.min.time(), tzinfo=timezone.utc)
    if payload.rejection_reason:
        summary_parts.append(f"Rejection Reason: {payload.rejection_reason}.")
    if payload.notes:
        summary_parts.append(f"Notes: {payload.notes.strip()}")

    summary_str = " ".join(summary_parts)

    # Record programmatic timeline event
    event = ApplicationEventModel(
        email_application_id=app.id,
        email_conversation_id=f"trans-conv-{app.id}",
        email_event_type="STATUS_CHANGE",
        email_status_after_event=new_status,
        email_summary=summary_str,
        email_received_at=event_time,
        source_channel="MANUAL",
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(event)
    await db.commit()

    # Enqueue non-blocking background embedding generation (only if active stage, not ASSESSMENT)
    if new_status != "ASSESSMENT":
        background_tasks.add_task(async_enqueue_application_embedding, app.id, skip_llm_summary=True)

    # Reload application with updated relations
    stmt_reload = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.action_items),
        )
        .execution_options(populate_existing=True)
    )
    res_refreshed = await db.execute(stmt_reload)
    app_refreshed = res_refreshed.scalar_one()

    sorted_events = sorted(
        app_refreshed.events or [],
        key=lambda e: (e.email_received_at or e.created_at),
        reverse=True,
    )
    latest_evt = sorted_events[0] if sorted_events else event
    has_action = any(e.email_action_required for e in app_refreshed.events)

    return ApplicationDetailResponse(
        id=app_refreshed.id,
        company=CompanySummary(
            id=app_refreshed.company.id,
            name=app_refreshed.company.name,
            domain=app_refreshed.company.domain,
        ),
        position=app_refreshed.position,
        status=app_refreshed.status,
        application_date=app_refreshed.application_date,
        last_activity_at=app_refreshed.last_activity_at,
        has_action_required=has_action,
        latest_event=EventSummary(
            id=latest_evt.id,
            email_event_type=latest_evt.email_event_type,
            email_subject=latest_evt.email_subject,
            email_action_required=latest_evt.email_action_required,
            email_action=latest_evt.email_action,
            email_received_at=latest_evt.email_received_at,
        )
        if latest_evt
        else None,
        external_job_id=app_refreshed.external_job_id,
        job_url=app_refreshed.job_url,
        application_key=app_refreshed.application_key,
        created_at=app_refreshed.created_at,
        updated_at=app_refreshed.updated_at,
        events=[ApplicationEventDetail.model_validate(e) for e in sorted_events],
        job_posting=JobPostingDetail.model_validate(app_refreshed.job_posting) if app_refreshed.job_posting else None,
        action_items=[ActionItemDetail.model_validate(a) for a in (app_refreshed.action_items or [])],
    )


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an application from database",
)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Permanently deletes an application and its associated events, postings, and embeddings."""
    stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    await db.delete(app)
    await db.commit()
    return {
        "status": "success",
        "message": f"Application {application_id} deleted successfully.",
        "application_id": application_id,
    }


@router.post(
    "/{application_id}/interview-guide",
    response_model=ApplicationDetailResponse,
    summary="Generate or regenerate a tailored interview preparation guide",
)
async def generate_app_interview_guide(
    application_id: int,
    payload: GenerateInterviewGuideRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        updated_app = await generate_interview_guide(db, application_id, payload)
        return await get_application(updated_app.id, db)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to generate interview guide: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/{application_id}/interview-guide",
    response_model=ApplicationDetailResponse,
    summary="Clear existing interview preparation guide",
)
async def clear_app_interview_guide(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        updated_app = await clear_interview_guide(db, application_id)
        return await get_application(updated_app.id, db)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to clear interview guide: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))