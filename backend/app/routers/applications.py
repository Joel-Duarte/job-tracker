from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.models.applications import (
    ApplicationEmbeddingModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.schemas.applications import (
    ApplicationDetailResponse,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationUpdate,
    CompanySummary,
    EventSummary,
)

from app.schemas.applications import AllowedApplicationStatus, ApplicationByStatusResult
from app.services.llm import generate_and_save_application_embedding

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
        subq = (
            select(ApplicationEventModel.email_application_id)
            .where(ApplicationEventModel.email_action_required == action_required)
            .scalar_subquery()
        )
        stmt = stmt.where(ApplicationModel.id.in_(subq))

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
        has_action = any(e.email_action_required for e in app.events)

        items.append(
            ApplicationListItem(
                id=app.id,
                company=CompanySummary(id=app.company.id, name=app.company.name, domain=app.company.domain),
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
        )
    )
    result = await db.execute(stmt)
    app = result.scalars().first()

    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    latest_evt = app.events[0] if app.events else None
    has_action = any(e.email_action_required for e in app.events)

    return ApplicationDetailResponse(
        id=app.id,
        company=CompanySummary(id=app.company.id, name=app.company.name, domain=app.company.domain),
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

@router.patch(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Partially update a job application",
)
async def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially updates a job application and refreshes its semantic vector embedding."""
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
        setattr(app, key, value)

    await db.commit()

    result = await db.execute(stmt)
    app = result.scalars().first()

    try:
        await generate_and_save_application_embedding(db, app.id)
    except Exception as e:
        print(f"[Warning] Failed to refresh embedding for Application ID {app.id}: {e}")

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