from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import FunnelMetricsResponse
from app.services.analytics import get_funnel_performance_metrics

router = APIRouter(prefix="/metrics", tags=["Metrics"])


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
