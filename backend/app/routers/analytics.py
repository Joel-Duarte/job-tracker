from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics import get_analytics_overview

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
