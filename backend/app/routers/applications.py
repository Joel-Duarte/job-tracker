import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_admin_access
from app.models.applications import (
    ActionItemModel,
    ApplicationEmbeddingModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.schemas.applications import (
    AllowedApplicationStatus,
    ApplicationByStatusResult,
    ApplicationDetailResponse,
    ApplicationListResponse,
    ApplicationTransitionRequest,
    ApplicationUpdate,
    BulkTransitionRequest,
    BulkTransitionResult,
    GenerateInterviewGuideRequest,
)
from app.services.application_service import ApplicationService
from app.services.interview_guide import (
    clear_interview_guide,
    generate_interview_guide,
    generate_interview_guide_stream,
)
from app.services.llm import (
    async_enqueue_application_embedding,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List applications with filtering and search",
)
async def list_applications(
    q: str | None = Query(None, description="Search position or company name"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status"
    ),
    action_required: bool | None = Query(
        None, description="Filter by pending action required"
    ),
    company_id: int | None = Query(None, description="Filter by company ID"),
    sort_by: str = Query(
        "last_activity_at", pattern="^(last_activity_at|application_date|created_at)$"
    ),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.list_applications(
        db=db,
        q=q,
        status_filter=status_filter,
        action_required=action_required,
        company_id=company_id,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/by-status",
    response_model=list[ApplicationByStatusResult],
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
    return await ApplicationService.get_applications_by_status(
        db=db, status=status, limit=limit
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get single application details",
)
async def get_application(application_id: int, db: AsyncSession = Depends(get_db)):
    return await ApplicationService.get_application(
        db=db, application_id=application_id
    )


@router.patch(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Partially update a job application",
    dependencies=[Depends(verify_admin_access)],
)
async def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.update_application(
        db=db,
        application_id=application_id,
        payload=payload,
        background_tasks=background_tasks,
    )


@router.post(
    "/{application_id}/transition",
    response_model=ApplicationDetailResponse,
    summary="Transition application pipeline status and record structured timeline event",
    dependencies=[Depends(verify_admin_access)],
)
async def transition_application(
    application_id: int,
    payload: ApplicationTransitionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.transition_application(
        db=db,
        application_id=application_id,
        payload=payload,
        background_tasks=background_tasks,
    )


@router.post(
    "/bulk-transition",
    response_model=BulkTransitionResult,
    summary="Bulk-transition multiple applications to a new status",
    dependencies=[Depends(verify_admin_access)],
)
async def bulk_transition_applications(
    payload: BulkTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> BulkTransitionResult:
    return await ApplicationService.bulk_transition_applications(db=db, payload=payload)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an application from database",
    dependencies=[Depends(verify_admin_access)],
)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.delete_application(
        db=db, application_id=application_id
    )


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
        return await ApplicationService.get_application(
            db=db, application_id=updated_app.id
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to generate interview guide: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.post(
    "/{application_id}/interview-guide/stream",
    summary="Stream tailored interview preparation guide generation via SSE",
)
async def generate_app_interview_guide_stream(
    application_id: int,
    payload: GenerateInterviewGuideRequest,
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        generate_interview_guide_stream(db, application_id, payload),
        media_type="text/event-stream",
    )


@router.delete(
    "/{application_id}/interview-guide",
    response_model=ApplicationDetailResponse,
    summary="Clear existing interview preparation guide",
    dependencies=[Depends(verify_admin_access)],
)
async def clear_app_interview_guide(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        updated_app = await clear_interview_guide(db, application_id)
        return await ApplicationService.get_application(
            db=db, application_id=updated_app.id
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to clear interview guide: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )