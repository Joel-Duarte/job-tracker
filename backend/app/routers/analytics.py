from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    FunnelMetricsResponse,
    RoleAlignmentResponse,
)
from app.services.analytics import (
    get_analytics_overview,
    get_funnel_performance_metrics,
    get_role_alignment,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_overview(
    days: int | None = Query(None, description="Number of days to look back"),
    work_model: str | None = Query(
        None, description="Filter by work model (e.g., remote, hybrid)"
    ),
    top_n: int | None = Query(
        None,
        description="Optional number of top skills/gaps to return (defaults to all)",
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_analytics_overview(
        db=db, days_limit=days, work_model=work_model, top_n_skills=top_n
    )


@router.get("/funnel", response_model=FunnelMetricsResponse)
async def get_funnel_metrics(
    period: str = Query(
        "weekly", description="Period granularity: 'weekly' or 'monthly'"
    ),
    num_periods: int = Query(8, description="Number of past periods to return"),
    db: AsyncSession = Depends(get_db),
):
    normalized_period = "monthly" if period.strip().lower() == "monthly" else "weekly"
    return await get_funnel_performance_metrics(
        db=db, period=normalized_period, num_periods=num_periods
    )


@router.get("/role-alignment", response_model=RoleAlignmentResponse)
async def get_role_alignment_endpoint(
    role_track: str | None = Query(
        "all",
        description="Role track key or search query (e.g., 'backend', 'fullstack')",
    ),
    days: int | None = Query(None, description="Timeframe filter in days"),
    db: AsyncSession = Depends(get_db),
):
    return await get_role_alignment(db=db, role_track=role_track, days=days)
