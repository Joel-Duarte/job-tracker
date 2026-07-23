from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.schemas.applications import (
    ApplicationDetailResponse,
    ApplicationFilterParams,
    ApplicationListResponse,
    StatusHistoryItem,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="List applications with filtering and search",
)
async def list_applications(
    q: Optional[str] = Query(None, description="Search position or company name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    action_required: Optional[bool] = Query(None, description="Filter by action required status"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    sort_by: str = Query("last_activity_at", pattern="^(last_activity_at|application_date|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Primary endpoint for loading job applications.
    
    Supports:
    - Text search (`q`) across positions and company names.
    - Status filtering (`status`).
    - Filtering by pending action required (`action_required`).
    - Pagination (`limit`, `offset`) and custom sorting.
    """
    # Database logic will be attached here
    pass


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Get single application details",
)
async def get_application(application_id: int):
    """Retrieves complete details for a single job application record."""
    pass


@router.get(
    "/{application_id}/history",
    response_model=List[StatusHistoryItem],
    summary="Get application status progression history",
)
async def get_application_history(application_id: int):
    """Returns the full status history timeline for tracking progression."""
    pass


@router.patch(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    summary="Update application status or position details",
)
async def update_application(application_id: int):
    """Allows updating position names, manual status overrides, or job URLs."""
    pass