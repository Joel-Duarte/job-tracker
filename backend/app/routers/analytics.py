from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    FunnelMetricsResponse,
    RoleAlignmentDossierResponse,
    RoleAlignmentEnhanceResponse,
    RoleAlignmentResponse,
)
from app.services.analytics import (
    clear_analytics_cache,
    get_analytics_overview,
    get_funnel_performance_metrics,
    get_role_alignment,
)
from app.services.evaluation_worker import process_evaluation_task
from app.services.role_alignment_dossier_service import (
    get_role_alignment_dossier,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post("/recalculate")
@router.post("/cache/clear")
async def recalculate_analytics():
    """
    Clears all server-side analytics caches across Overview, Funnel, and Role Alignment
    so subsequent queries re-compute fresh data from PostgreSQL.
    """
    clear_analytics_cache()
    return {
        "status": "ok",
        "message": "Analytics cache flushed and ready for recalculation",
    }


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


@router.get(
    "/role-alignment/dossier",
    response_model=RoleAlignmentDossierResponse | None,
)
async def get_role_alignment_dossier_endpoint(
    role_track: str = Query("all", description="Role track key (e.g., 'backend')"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches the existing AI Strategic Dossier for the given role track if generated,
    or null if no analysis exists yet.
    """
    return await get_role_alignment_dossier(db=db, role_track=role_track)


@router.post(
    "/role-alignment/enhance",
    response_model=RoleAlignmentEnhanceResponse,
)
async def enhance_role_alignment_endpoint(
    background_tasks: BackgroundTasks,
    role_track: str = Query("all", description="Role track key (e.g., 'backend')"),
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueues an asynchronous AI Strategic Dossier synthesis task through the shared background worker queue.
    """
    norm_track = (role_track or "all").strip().lower()
    task = IntakeEvaluationTaskModel(
        task_type="ROLE_ALIGNMENT_DOSSIER",
        raw_text=norm_track,
        title_hint=f"AI Dossier ({norm_track.upper()})",
        status="QUEUED",
        stage="QUEUED",
        result_json={"role_track": norm_track},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Dispatch to shared background worker queue bounded by provider concurrency limits
    background_tasks.add_task(process_evaluation_task, task_id=task.id)

    return RoleAlignmentEnhanceResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        stage=task.stage,
        role_track=norm_track,
    )
