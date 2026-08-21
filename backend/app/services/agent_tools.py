import json
import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import StructuredTool
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.applications import (
    ActionItemModel,
    ApplicationEmbeddingModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.agent_tools import (
    AnalyzePipelineMetricsInput,
    ApplicationDetailsInput,
    DetectStalledApplicationsInput,
    EvaluateAIFitScoreInput,
    ListApplicationsInput,
    ManageActionItemsInput,
    ManageIntakeQueueInput,
    QueryMarketBenchmarksInput,
    SemanticSearchInput,
    UpdateApplicationPipelineInput,
)
from app.services.analytics import get_funnel_performance_metrics
from app.services.llm import generate_and_save_application_embedding, generate_embedding

logger = logging.getLogger(__name__)


# 1. Analyze Pipeline Metrics Tool
async def execute_analyze_pipeline_metrics(
    db: AsyncSession,
    period: str = "weekly",
    num_periods: int = 8,
) -> dict[str, Any]:
    """Retrieves aggregated funnel performance metrics, conversion counts, and period-over-period trend deltas."""
    normalized_period = "monthly" if period.strip().lower() == "monthly" else "weekly"
    metrics = await get_funnel_performance_metrics(
        db=db, period=normalized_period, num_periods=num_periods
    )
    return metrics.model_dump()


# 2. Detect Stalled Applications Tool
async def execute_detect_stalled_applications(
    db: AsyncSession,
    inactivity_threshold_days: int = 14,
    status: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Identifies active job applications that have had no recruiter or timeline activity for longer than the inactivity threshold."""
    active_statuses = ["APPLIED", "TECHNICAL_INTERVIEW", "ASSESSMENT"]
    stmt = select(ApplicationModel).options(
        joinedload(ApplicationModel.company),
        selectinload(ApplicationModel.events),
    )

    if status:
        stmt = stmt.where(ApplicationModel.status == status.upper())
    else:
        stmt = stmt.where(ApplicationModel.status.in_(active_statuses))

    stmt = stmt.order_by(ApplicationModel.last_activity_at.asc().nulls_first()).limit(
        limit * 2
    )
    res = await db.execute(stmt)
    apps = res.scalars().all()

    now = datetime.now(UTC)
    stalled = []

    for app in apps:
        last_act = app.last_activity_at or app.updated_at or app.application_date
        if not last_act:
            continue

        if last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=UTC)

        days_inactive = (now - last_act).days
        if days_inactive >= inactivity_threshold_days:
            company_name = app.company.name if app.company else "Unknown"
            stalled.append(
                {
                    "application_id": app.id,
                    "company": company_name,
                    "position": app.position,
                    "status": app.status,
                    "days_inactive": days_inactive,
                    "last_activity_at": last_act.isoformat(),
                    "recommended_action": f"Send follow-up nudge email to {company_name} recruiting team regarding {app.position} status.",
                }
            )
            if len(stalled) >= limit:
                break

    return stalled


# 3. Query Market Benchmarks Tool
async def execute_query_market_benchmarks(
    db: AsyncSession,
    position_keyword: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Aggregates salary ranges, top required skills, and remote/hybrid work distributions across stored job postings and applications."""
    stmt = (
        select(JobPostingModel)
        .options(
            joinedload(JobPostingModel.application).joinedload(ApplicationModel.company)
        )
        .limit(limit)
    )

    if position_keyword:
        kw = f"%{position_keyword.strip().lower()}%"
        stmt = (
            stmt.join(
                ApplicationModel,
                JobPostingModel.application_id == ApplicationModel.id,
                isouter=True,
            )
            .join(
                CompanyModel,
                ApplicationModel.company_id == CompanyModel.id,
                isouter=True,
            )
            .where(
                or_(
                    ApplicationModel.position.ilike(kw),
                    CompanyModel.name.ilike(kw),
                    JobPostingModel.job_url.ilike(kw),
                )
            )
        )

    res = await db.execute(stmt)
    postings = res.scalars().all()

    salaries_min = []
    salaries_max = []
    skill_counts: dict[str, int] = {}
    work_models: dict[str, int] = {"remote": 0, "hybrid": 0, "on-site": 0, "unknown": 0}

    for p in postings:
        if p.salary_min is not None and p.salary_min > 0:
            salaries_min.append(p.salary_min)
        if p.salary_max is not None and p.salary_max > 0:
            salaries_max.append(p.salary_max)

        skills = p.required_skills or p.extracted_keywords or []
        for s in skills:
            if isinstance(s, str) and s.strip():
                s_clean = s.strip().title()
                skill_counts[s_clean] = skill_counts.get(s_clean, 0) + 1

        wm = (p.work_model or "unknown").lower().strip()
        if "remote" in wm:
            work_models["remote"] += 1
        elif "hybrid" in wm:
            work_models["hybrid"] += 1
        elif "site" in wm or "office" in wm:
            work_models["on-site"] += 1
        else:
            work_models["unknown"] += 1

    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    avg_min_sal = sum(salaries_min) / len(salaries_min) if salaries_min else None
    avg_max_sal = sum(salaries_max) / len(salaries_max) if salaries_max else None

    return {
        "sample_size": len(postings),
        "position_filter": position_keyword,
        "salary_benchmarks": {
            "currency": "USD",
            "average_min": round(avg_min_sal, 2) if avg_min_sal else None,
            "average_max": round(avg_max_sal, 2) if avg_max_sal else None,
            "overall_min": min(salaries_min) if salaries_min else None,
            "overall_max": max(salaries_max) if salaries_max else None,
        },
        "top_demanded_skills": [{"skill": k, "count": v} for k, v in top_skills],
        "work_model_distribution": work_models,
    }


# 4. Evaluate AI Fit Score Tool
async def execute_evaluate_ai_fit_score(
    db: AsyncSession, company_or_id: str
) -> dict[str, Any]:
    """Fetches programmatic match scores and qualitative AI evaluation details for a specific application."""
    stmt = select(ApplicationModel).options(
        joinedload(ApplicationModel.company),
        selectinload(ApplicationModel.job_posting),
    )
    if company_or_id.isdigit():
        stmt = stmt.where(ApplicationModel.id == int(company_or_id))
    else:
        stmt = stmt.join(CompanyModel).where(
            CompanyModel.name_normalized.ilike(f"%{company_or_id.strip().lower()}%")
        )

    res = await db.execute(stmt)
    app = res.scalars().first()
    if not app:
        return {"error": f"No application found matching '{company_or_id}'."}

    payload = app.match_analysis_payload or {}
    prog_score = payload.get("programmatic_match_score") or payload.get("match_score")
    fit_score = (
        payload.get("fit_score") or payload.get("overall_fit_score") or prog_score
    )

    return {
        "application_id": app.id,
        "company": app.company.name if app.company else "Unknown",
        "position": app.position,
        "status": app.status,
        "programmatic_match_score": prog_score,
        "fit_score": fit_score,
        "matching_skills": payload.get("matching_skills")
        or payload.get("matched_skills")
        or [],
        "missing_skills": payload.get("missing_skills")
        or payload.get("gap_skills")
        or [],
        "pros": payload.get("pros") or payload.get("strengths") or [],
        "cons": payload.get("cons") or payload.get("weaknesses") or [],
        "recommendations": payload.get("recommendations")
        or payload.get("summary")
        or "No detailed analysis recommendations available.",
    }


# 5. Manage Intake Queue Tool
async def execute_manage_intake_queue(
    db: AsyncSession,
    action: str = "list",
    task_id: int | None = None,
    fix_raw_text: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Interacts with background intake evaluation queue tasks to list, retry, cancel, or fix job postings."""
    action_norm = action.lower().strip()

    if action_norm == "list":
        stmt = (
            select(IntakeEvaluationTaskModel)
            .order_by(IntakeEvaluationTaskModel.id.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        tasks = res.scalars().all()
        return {
            "action": "list",
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "status": t.status,
                    "stage": t.stage,
                    "job_url": t.job_url,
                    "error_message": t.error_message,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
        }

    if not task_id:
        return {"error": f"task_id is required for action '{action}'."}

    task = await db.get(IntakeEvaluationTaskModel, task_id)
    if not task:
        return {"error": f"Intake task #{task_id} not found."}

    if action_norm == "cancel":
        task.status = "FAILED"
        task.stage = "FAILED"
        task.error_message = "Task stopped by user via agent tool."
        task.completed_at = datetime.now(UTC)
        db.add(task)
        await db.commit()
        return {
            "success": True,
            "action": "cancel",
            "task_id": task_id,
            "message": f"Successfully cancelled intake task #{task_id}.",
        }

    if action_norm == "retry":
        task.status = "PENDING"
        task.error_message = None
        task.completed_at = None
        db.add(task)
        await db.commit()
        return {
            "success": True,
            "action": "retry",
            "task_id": task_id,
            "message": f"Successfully re-queued intake task #{task_id} for processing.",
        }

    if action_norm == "fix":
        if not fix_raw_text or not fix_raw_text.strip():
            return {"error": "fix_raw_text is required when action='fix'."}
        task.raw_text = fix_raw_text.strip()
        task.status = "PENDING"
        task.error_message = None
        task.completed_at = None
        db.add(task)
        await db.commit()
        return {
            "success": True,
            "action": "fix",
            "task_id": task_id,
            "message": f"Successfully updated job text and re-queued intake task #{task_id}.",
        }

    return {"error": f"Unsupported queue action '{action}'."}


# 6. Manage Action Items Tool
async def execute_manage_action_items(
    db: AsyncSession,
    action: str = "list",
    item_id: int | None = None,
    urgency: str | None = None,
    title: str | None = None,
    due_date: str | None = None,
    application_id: int | None = None,
) -> dict[str, Any]:
    """Lists, completes, dismisses, or creates candidate tasks and action item deadlines."""
    action_norm = action.lower().strip()

    if action_norm == "list":
        stmt = (
            select(ActionItemModel)
            .options(
                joinedload(ActionItemModel.application).joinedload(
                    ApplicationModel.company
                )
            )
            .where(ActionItemModel.status == "PENDING")
        )
        if urgency:
            stmt = stmt.where(ActionItemModel.urgency == urgency.upper())
        stmt = stmt.order_by(ActionItemModel.due_date.asc().nulls_last())
        res = await db.execute(stmt)
        items = res.scalars().all()
        return {
            "action": "list",
            "action_items": [
                {
                    "id": item.id,
                    "company": (
                        item.application.company.name
                        if (item.application and item.application.company)
                        else "General"
                    ),
                    "title": item.title,
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                    "urgency": item.urgency,
                    "status": item.status,
                }
                for item in items
            ],
        }

    if action_norm in ("complete", "dismiss"):
        if not item_id:
            return {"error": f"item_id is required for action '{action}'."}
        item = await db.get(ActionItemModel, item_id)
        if not item:
            return {"error": f"Action item #{item_id} not found."}

        if action_norm == "complete":
            item.status = "COMPLETED"
            item.completed_at = datetime.now(UTC)
            db.add(item)
            await db.commit()
            return {
                "success": True,
                "action": "complete",
                "item_id": item_id,
                "message": f"Marked action item '{item.title}' as COMPLETED.",
            }
        else:
            await db.delete(item)
            await db.commit()
            return {
                "success": True,
                "action": "dismiss",
                "item_id": item_id,
                "message": f"Dismissed action item #{item_id}.",
            }

    if action_norm == "create":
        if not title or not title.strip():
            return {"error": "title is required when action='create'."}
        parsed_due = None
        if due_date:
            try:
                parsed_due = datetime.fromisoformat(due_date)
            except Exception:
                pass
        new_item = ActionItemModel(
            title=title.strip(),
            urgency=(urgency or "MEDIUM").upper(),
            status="PENDING",
            due_date=parsed_due,
            application_id=application_id,
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        return {
            "success": True,
            "action": "create",
            "item_id": new_item.id,
            "title": new_item.title,
            "message": f"Created new action item '{new_item.title}'.",
        }

    return {"error": f"Unsupported action_items action '{action}'."}


# 7. Semantic Vector Search Tool
async def execute_semantic_vector_search(
    db: AsyncSession, query: str, limit: int = 5
) -> list[dict[str, Any]]:
    """Performs semantic vector search across pgvector application embeddings, with fallback if embeddings are disabled."""
    from app.core.config_manager import get_setting

    if not await get_setting("ENABLE_EMBEDDINGS", True, db):
        words = [w for w in query.strip().split() if len(w) > 2]
        stmt = (
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.company),
                selectinload(ApplicationModel.events),
            )
            .join(CompanyModel, ApplicationModel.company_id == CompanyModel.id)
            .limit(limit)
        )
        if words:
            filters = [
                or_(
                    CompanyModel.name.ilike(f"%{w}%"),
                    ApplicationModel.position.ilike(f"%{w}%"),
                    ApplicationModel.status.ilike(f"%{w}%"),
                )
                for w in words
            ]
            stmt = stmt.where(or_(*filters))
        res = await db.execute(stmt)
        apps = res.scalars().all()
        return [
            {
                "application_id": app.id,
                "company": app.company.name if app.company else "Unknown",
                "position": app.position,
                "status": app.status,
                "similarity_score": "Keyword Match (Fast)",
                "document_content": f"Application for {app.position} at {app.company.name if app.company else 'Unknown'} ({app.status})",
                "metadata": {"fallback": True},
            }
            for app in apps
        ]

    query_vector = await generate_embedding(db, query)
    distance_expr = ApplicationEmbeddingModel.embedding.cosine_distance(
        query_vector
    ).label("distance")
    stmt = (
        select(ApplicationEmbeddingModel, distance_expr)
        .join(
            ApplicationModel,
            ApplicationEmbeddingModel.email_application_id == ApplicationModel.id,
        )
        .options(
            selectinload(ApplicationEmbeddingModel.application).selectinload(
                ApplicationModel.company
            )
        )
        .order_by(distance_expr.asc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    hits = res.all()
    results = []
    for emb, dist in hits:
        app = emb.application
        comp_name = app.company.name if (app and app.company) else "Unknown"
        sim_pct = round(max(0.0, min(100.0, (1.0 - float(dist)) * 100.0)), 1)
        results.append(
            {
                "application_id": app.id if app else None,
                "company": comp_name,
                "position": app.position if app else "Unknown",
                "status": app.status if app else "APPLIED",
                "similarity_score": f"{sim_pct}%",
                "document_content": emb.content,
                "metadata": emb.metadata_,
            }
        )
    return results


# 8. Update Application Pipeline Tool
async def execute_update_application_pipeline(
    db: AsyncSession,
    company_or_id: str,
    new_status: str,
    notes: str | None = None,
    event_type: str = "STATUS_CHANGE",
) -> dict[str, Any]:
    """Updates application pipeline status in DB, creates timeline event, and triggers vector embedding refresh."""
    valid_statuses = [
        "APPLIED",
        "TECHNICAL_INTERVIEW",
        "OFFER",
        "REJECTED",
        "ASSESSMENT",
        "HIRED",
    ]
    status_norm = new_status.upper()
    if status_norm not in valid_statuses:
        return {"error": f"Invalid status '{new_status}'. Allowed: {valid_statuses}"}

    stmt = select(ApplicationModel).options(joinedload(ApplicationModel.company))
    if company_or_id.isdigit():
        stmt = stmt.where(ApplicationModel.id == int(company_or_id))
    else:
        stmt = stmt.join(CompanyModel).where(
            CompanyModel.name_normalized.ilike(f"%{company_or_id.strip().lower()}%")
        )

    res = await db.execute(stmt)
    app = res.scalars().first()
    if not app:
        return {"error": f"No application found matching '{company_or_id}'."}

    old_status = app.status
    app.status = status_norm
    app.last_activity_at = datetime.now(UTC)

    event = ApplicationEventModel(
        email_application_id=app.id,
        email_event_type=event_type,
        email_status_after_event=status_norm,
        email_summary=notes
        or f"Status transitioned from {old_status} to {status_norm} via AI Agent assistant.",
        source_channel="AGENT",
    )
    db.add(event)
    await db.commit()
    await db.refresh(app)

    # Update vector embeddings
    if status_norm != "ASSESSMENT":
        try:
            await generate_and_save_application_embedding(
                db, app.id, skip_llm_summary=True
            )
        except Exception as err:
            logger.warning("Embedding update deferred: %s", err)

    comp_name = app.company.name if app.company else "Unknown"
    return {
        "success": True,
        "application_id": app.id,
        "company": comp_name,
        "old_status": old_status,
        "new_status": status_norm,
        "message": f"Successfully transitioned {comp_name} application from {old_status} to {status_norm}.",
    }


# Retained Legacy Helpers
async def execute_list_applications(
    db: AsyncSession,
    status: str | None = None,
    action_required_only: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Lists applications directly from the database."""
    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.action_items),
        )
        .order_by(ApplicationModel.updated_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(ApplicationModel.status == status.upper())
    res = await db.execute(stmt)
    apps = res.scalars().all()
    out = []
    for a in apps:
        has_action = any(i.status == "PENDING" for i in (a.action_items or []))
        if action_required_only and not has_action:
            continue
        out.append(
            {
                "id": a.id,
                "company": a.company.name if a.company else "Unknown",
                "position": a.position,
                "status": a.status,
                "has_action_required": has_action,
                "application_date": a.application_date.isoformat()
                if a.application_date
                else None,
                "last_activity_at": a.last_activity_at.isoformat()
                if a.last_activity_at
                else None,
            }
        )
    return out


async def execute_get_application_details(
    db: AsyncSession, company_or_id: str
) -> dict[str, Any]:
    """Fetches complete timeline and event history for a specific application."""
    stmt = select(ApplicationModel).options(
        joinedload(ApplicationModel.company),
        selectinload(ApplicationModel.events),
        selectinload(ApplicationModel.job_posting),
        selectinload(ApplicationModel.action_items),
    )
    if company_or_id.isdigit():
        stmt = stmt.where(ApplicationModel.id == int(company_or_id))
    else:
        stmt = stmt.join(CompanyModel).where(
            CompanyModel.name_normalized.ilike(f"%{company_or_id.strip().lower()}%")
        )

    res = await db.execute(stmt)
    app = res.scalars().first()
    if not app:
        return {"error": f"No application found matching '{company_or_id}'."}

    events_out = []
    for e in app.events or []:
        events_out.append(
            {
                "event_type": e.email_event_type,
                "subject": e.email_subject,
                "summary": e.email_summary,
                "received_at": e.email_received_at.isoformat()
                if e.email_received_at
                else None,
                "action_required": e.email_action_required,
                "action": e.email_action,
            }
        )

    actions_out = []
    for a in app.action_items or []:
        actions_out.append(
            {
                "id": a.id,
                "title": a.title,
                "status": a.status,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "urgency": a.urgency,
            }
        )

    return {
        "id": app.id,
        "company": app.company.name if app.company else "Unknown",
        "position": app.position,
        "status": app.status,
        "job_url": app.job_url,
        "events": events_out,
        "action_items": actions_out,
    }


def create_agent_tools(db: AsyncSession) -> list[StructuredTool]:
    """Factory creating bound LangChain tools for the active async database session."""

    async def _analyze_pipeline_metrics(
        period: str = "weekly", num_periods: int = 8
    ) -> str:
        res = await execute_analyze_pipeline_metrics(db, period, num_periods)
        return json.dumps(res, indent=2)

    async def _detect_stalled_applications(
        inactivity_threshold_days: int = 14,
        status: str | None = None,
        limit: int = 10,
    ) -> str:
        res = await execute_detect_stalled_applications(
            db, inactivity_threshold_days, status, limit
        )
        return json.dumps(res, indent=2)

    async def _query_market_benchmarks(
        position_keyword: str | None = None, limit: int = 50
    ) -> str:
        res = await execute_query_market_benchmarks(db, position_keyword, limit)
        return json.dumps(res, indent=2)

    async def _evaluate_ai_fit_score(company_or_id: str) -> str:
        res = await execute_evaluate_ai_fit_score(db, company_or_id)
        return json.dumps(res, indent=2)

    async def _manage_intake_queue(
        action: str = "list",
        task_id: int | None = None,
        fix_raw_text: str | None = None,
        limit: int = 20,
    ) -> str:
        res = await execute_manage_intake_queue(
            db, action, task_id, fix_raw_text, limit
        )
        return json.dumps(res, indent=2)

    async def _manage_action_items(
        action: str = "list",
        item_id: int | None = None,
        urgency: str | None = None,
        title: str | None = None,
        due_date: str | None = None,
        application_id: int | None = None,
    ) -> str:
        res = await execute_manage_action_items(
            db, action, item_id, urgency, title, due_date, application_id
        )
        return json.dumps(res, indent=2)

    async def _semantic_vector_search(query: str, limit: int = 5) -> str:
        res = await execute_semantic_vector_search(db, query, limit)
        return json.dumps(res, indent=2)

    async def _update_application_pipeline(
        company_or_id: str,
        new_status: str,
        notes: str | None = None,
        event_type: str = "STATUS_CHANGE",
    ) -> str:
        res = await execute_update_application_pipeline(
            db, company_or_id, new_status, notes, event_type
        )
        return json.dumps(res, indent=2)

    async def _list_applications(
        status: str | None = None,
        action_required_only: bool = False,
        limit: int = 20,
    ) -> str:
        res = await execute_list_applications(db, status, action_required_only, limit)
        return json.dumps(res, indent=2)

    async def _get_application_details(company_or_id: str) -> str:
        res = await execute_get_application_details(db, company_or_id)
        return json.dumps(res, indent=2)

    return [
        StructuredTool.from_function(
            coroutine=_analyze_pipeline_metrics,
            name="analyze_pipeline_metrics",
            description="Analyzes cohort funnel performance metrics, stage conversion counts, and period-over-period trend deltas (weekly or monthly).",
            args_schema=AnalyzePipelineMetricsInput,
        ),
        StructuredTool.from_function(
            coroutine=_detect_stalled_applications,
            name="detect_stalled_applications",
            description="Queries active applications that have had no recruiter activity exceeding an inactivity threshold (e.g. 14 days) and suggests follow-up actions.",
            args_schema=DetectStalledApplicationsInput,
        ),
        StructuredTool.from_function(
            coroutine=_query_market_benchmarks,
            name="query_market_benchmarks",
            description="Aggregates market salary benchmarks, top in-demand skills, and remote/hybrid work distributions across job postings.",
            args_schema=QueryMarketBenchmarksInput,
        ),
        StructuredTool.from_function(
            coroutine=_evaluate_ai_fit_score,
            name="evaluate_ai_fit_score",
            description="Retrieves both programmatic match score and qualitative AI evaluation details (matching skills, missing skills, pros, cons, recommendations) for an application.",
            args_schema=EvaluateAIFitScoreInput,
        ),
        StructuredTool.from_function(
            coroutine=_manage_intake_queue,
            name="manage_intake_queue",
            description="Manages background job intake evaluation tasks (list, retry, cancel, or fix failed job descriptions).",
            args_schema=ManageIntakeQueueInput,
        ),
        StructuredTool.from_function(
            coroutine=_manage_action_items,
            name="manage_action_items",
            description="Lists, completes, dismisses, or creates candidate action items, deadlines, and tasks.",
            args_schema=ManageActionItemsInput,
        ),
        StructuredTool.from_function(
            coroutine=_semantic_vector_search,
            name="semantic_vector_search",
            description="Searches the vector database for relevant job applications, recruiter emails, and timeline updates using semantic cosine similarity.",
            args_schema=SemanticSearchInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_application_pipeline,
            name="update_application_pipeline",
            description="Updates an application status in the pipeline (e.g. APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT, HIRED), logs a timeline event, and updates vector embeddings.",
            args_schema=UpdateApplicationPipelineInput,
        ),
        StructuredTool.from_function(
            coroutine=_list_applications,
            name="list_applications",
            description="Lists job applications directly from the database with optional status or action required filtering.",
            args_schema=ListApplicationsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_application_details,
            name="get_application_details",
            description="Retrieves chronological timeline events, recruiter emails, and action items for a company or application ID.",
            args_schema=ApplicationDetailsInput,
        ),
    ]
