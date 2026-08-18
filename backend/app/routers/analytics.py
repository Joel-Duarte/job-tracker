from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import (
    ActivityAnalyticsResponse,
    ActivityHistoryResponse,
    AnalyticsOverviewResponse,
)
from app.services.analytics import (
    get_activity_analytics,
    get_activity_history,
    get_analytics_overview,
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


@router.get("/activity", response_model=ActivityAnalyticsResponse)
async def get_activity(
    period: str = Query(
        ..., description="Period (e.g., this_week, last_week, this_month, custom)"
    ),
    start_date: str | None = Query(None, description="ISO date string for start"),
    end_date: str | None = Query(None, description="ISO date string for end"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_activity_analytics(db, period, start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/activity/history", response_model=ActivityHistoryResponse)
async def get_history(
    db: AsyncSession = Depends(get_db),
):
    return await get_activity_history(db)
