import json
import logging
from datetime import UTC, datetime, timedelta
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
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.agent_tools import (
    AnalyzePipelineMetricsInput,
    ApplicationDetailsInput,
    BulkTransitionApplicationsInput,
    DetectStalledApplicationsInput,
    EnqueueApplicationQuestionsInput,
    EnqueueCompanyResearchInput,
    EnqueueCoverLetterGenerationInput,
    EvaluateAIFitScoreInput,
    FetchWebpageContentInput,
    GetApplicationQuestionsInput,
    GetCandidateProfileInput,
    GetCompanyDetailsInput,
    GetCoverLetterInput,
    GetMockInterviewHistoryInput,
    GetRoleAlignmentDossierInput,
    GetUpcomingInterviewsInput,
    ListApplicationsInput,
    ListCompaniesInput,
    ManageActionItemsInput,
    ManageIntakeQueueInput,
    QueryMarketBenchmarksInput,
    SearchWebInput,
    SemanticSearchInput,
    StartMockInterviewInput,
    UpdateApplicationPipelineInput,
    UpdateCompanyNotesInput,
)
from app.services.analytics import get_funnel_performance_metrics
from app.services.interview_simulator_service import InterviewSimulatorService
from app.services.llm import generate_and_save_application_embedding, generate_embedding
from app.services.web_search import fetch_webpage_content, search_web

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

    if not await get_setting("ENABLE_EMBEDDINGS", False, db):
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
                "similarity_score": "Keyword Match",
                "search_mode": "keyword_search",
                "embeddings_enabled": False,
                "document_content": f"Application for {app.position} at {app.company.name if app.company else 'Unknown'} ({app.status})",
                "metadata": {
                    "fallback": True,
                    "note": "Vector embeddings are disabled in system settings. Performed database text keyword match.",
                },
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
                "search_mode": "vector_similarity",
                "embeddings_enabled": True,
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
            from app.core.config_manager import get_setting

            if await get_setting("ENABLE_EMBEDDINGS", False, db=db):
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


def _resolve_scheduled_interview_info(
    app: ApplicationModel,
) -> tuple[datetime | None, str | None]:
    """Helper extracting confirmed scheduled interview datetime and sub-phase for an application."""
    scheduled_dt: datetime | None = None
    sub_stage: str | None = None

    sorted_events = sorted(
        app.events or [],
        key=lambda e: (
            (
                e.email_received_at
                if e.email_received_at.tzinfo
                else e.email_received_at.replace(tzinfo=UTC)
            )
            if e.email_received_at
            else datetime.min.replace(tzinfo=UTC)
        ),
        reverse=True,
    )
    latest_interview_evt = None
    for evt in sorted_events:
        if evt.raw_payload and isinstance(evt.raw_payload, dict):
            if (
                "interview_stage" in evt.raw_payload
                or "scheduled_at" in evt.raw_payload
            ):
                latest_interview_evt = evt
                break

    if latest_interview_evt:
        payload_stage = latest_interview_evt.raw_payload.get("interview_stage")
        sub_stage = payload_stage
        if payload_stage != "Task Completed / Awaiting Response":
            sched_val = latest_interview_evt.raw_payload.get("scheduled_at")
            if sched_val:
                try:
                    scheduled_dt = datetime.fromisoformat(str(sched_val))
                except Exception:
                    pass

    if not scheduled_dt:
        for act in app.action_items or []:
            if (
                act.status == "PENDING"
                and "interview" in (act.title or "").lower()
                and act.due_date
            ):
                scheduled_dt = act.due_date
                if not sub_stage:
                    sub_stage = act.title
                break

    return scheduled_dt, sub_stage


# Retained Legacy Helpers
async def execute_list_applications(
    db: AsyncSession,
    status: str | None = None,
    action_required_only: bool = False,
    include_assessments: bool = False,
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
    )

    if not include_assessments:
        stmt = stmt.where(
            ApplicationModel.is_assessment.is_(False),
            ApplicationModel.status != "ASSESSMENT",
        )

    if status:
        status_norm = status.strip().upper()
        if status_norm == "ACTIVE":
            stmt = stmt.where(
                ApplicationModel.status.in_(
                    ["APPLIED", "ONLINE_ASSESSMENT", "TECHNICAL_INTERVIEW", "OFFER"]
                )
            )
        else:
            stmt = stmt.where(ApplicationModel.status == status_norm)

    stmt = stmt.limit(limit)
    res = await db.execute(stmt)
    apps = res.scalars().all()
    out = []
    for a in apps:
        has_action = any(i.status == "PENDING" for i in (a.action_items or []))
        if action_required_only and not has_action:
            continue
        sched_dt, sub_stage = _resolve_scheduled_interview_info(a)
        out.append(
            {
                "id": a.id,
                "company": a.company.name if a.company else "Unknown",
                "position": a.position,
                "status": a.status,
                "has_action_required": has_action,
                "scheduled_interview_at": sched_dt.isoformat() if sched_dt else None,
                "interview_stage": sub_stage,
                "application_date": a.application_date.isoformat()
                if a.application_date
                else None,
                "last_activity_at": a.last_activity_at.isoformat()
                if a.last_activity_at
                else None,
            }
        )
    return out


async def execute_get_upcoming_interviews(
    db: AsyncSession,
    days_ahead: int = 30,
    include_pending_scheduling: bool = True,
) -> dict[str, Any]:
    """
    Fetches upcoming interviews and interview-stage applications,
    strictly distinguishing confirmed interviews (with dates) from applications
    awaiting scheduling or recruiter responses.
    """
    now = datetime.now(UTC)
    max_date = now + timedelta(days=days_ahead)

    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.action_items),
        )
        .where(
            ApplicationModel.is_assessment.is_(False),
            ApplicationModel.status.in_(
                ["TECHNICAL_INTERVIEW", "ONLINE_ASSESSMENT", "OFFER", "APPLIED"]
            ),
        )
        .order_by(ApplicationModel.updated_at.desc())
    )
    res = await db.execute(stmt)
    apps = res.scalars().all()

    confirmed_interviews: list[dict[str, Any]] = []
    awaiting_scheduling: list[dict[str, Any]] = []

    for a in apps:
        comp_name = a.company.name if a.company else "Unknown"
        sched_dt, sub_stage = _resolve_scheduled_interview_info(a)

        if sched_dt:
            norm_dt = sched_dt if sched_dt.tzinfo else sched_dt.replace(tzinfo=UTC)
            if (now - timedelta(hours=24)) <= norm_dt <= max_date:
                confirmed_interviews.append(
                    {
                        "application_id": a.id,
                        "company": comp_name,
                        "position": a.position,
                        "status": a.status,
                        "scheduled_at": sched_dt.isoformat(),
                        "formatted_date": sched_dt.strftime(
                            "%A, %b %d, %Y at %I:%M %p UTC"
                        ),
                        "interview_stage": sub_stage or "Technical Interview",
                    }
                )
        elif include_pending_scheduling and a.status in [
            "TECHNICAL_INTERVIEW",
            "ONLINE_ASSESSMENT",
        ]:
            is_awaiting_reply = sub_stage == "Task Completed / Awaiting Response"
            awaiting_scheduling.append(
                {
                    "application_id": a.id,
                    "company": comp_name,
                    "position": a.position,
                    "status": a.status,
                    "sub_phase": sub_stage
                    or (
                        "Task Completed / Awaiting Response"
                        if is_awaiting_reply
                        else "Interview Requested / Scheduling Needed"
                    ),
                    "scheduled_at": None,
                    "state": (
                        "awaiting_recruiter_reply"
                        if is_awaiting_reply
                        else "scheduling_needed"
                    ),
                    "notes": (
                        "Completed previous round/task; currently awaiting recruiter feedback."
                        if is_awaiting_reply
                        else "Interview requested/in-progress, but specific date/time has not been scheduled yet."
                    ),
                }
            )

    confirmed_interviews.sort(key=lambda x: x["scheduled_at"])

    return {
        "lookahead_days": days_ahead,
        "total_confirmed_interviews": len(confirmed_interviews),
        "confirmed_interviews": confirmed_interviews,
        "awaiting_scheduling_or_response": (
            awaiting_scheduling if include_pending_scheduling else []
        ),
    }


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


# 11. Start Mock Interview Tool
async def execute_start_mock_interview(
    db: AsyncSession,
    company_or_id: str | None = None,
    question_mode: str = "TEXT_CONVERSATIONAL",
    interviewer_persona: str = "TECHNICAL_BAR_RAISER",
) -> dict[str, Any]:
    """Launches an interactive live mock interview simulation tailored to a target application or general practice."""
    app_id = None
    company_name = "General Software Engineering"
    position = "Software Engineer"
    if company_or_id:
        app_id_val = None
        try:
            app_id_val = int(company_or_id)
        except (ValueError, TypeError):
            pass

        if app_id_val is not None:
            stmt = (
                select(ApplicationModel)
                .options(joinedload(ApplicationModel.company))
                .where(ApplicationModel.id == app_id_val)
            )
        else:
            stmt = (
                select(ApplicationModel)
                .join(CompanyModel)
                .options(joinedload(ApplicationModel.company))
                .where(CompanyModel.name.ilike(f"%{str(company_or_id).strip()}%"))
            )

        res = await db.execute(stmt)
        app = res.scalars().first()
        if app:
            app_id = app.id
            company_name = app.company.name if app.company else "Company"
            position = app.position or "Software Engineer"

    # Normalize question_mode
    mode_str = str(question_mode).upper().strip()
    if mode_str not in ("TEXT_CONVERSATIONAL", "MULTIPLE_CHOICE", "HYBRID"):
        mode_str = "TEXT_CONVERSATIONAL"

    # Normalize interviewer_persona
    persona_norm = str(interviewer_persona).upper().strip()
    if persona_norm not in (
        "TECHNICAL_BAR_RAISER",
        "HIRING_MANAGER",
        "BEHAVIORAL_CULTURE",
        "SUPPORTIVE_COACH",
    ):
        persona_norm = "TECHNICAL_BAR_RAISER"

    session = await InterviewSimulatorService.start_session(
        db=db,
        application_id=app_id,
        persona=persona_norm,
        question_mode=mode_str,
    )

    first_q = session.turns_data[0].get("question") if session.turns_data else ""

    return {
        "status": "started",
        "session_id": session.id,
        "application_id": app_id,
        "company_name": company_name,
        "position": position,
        "question_mode": session.question_mode,
        "interviewer_persona": persona_norm,
        "first_question": first_q,
        "message": f"Live mock interview session #{session.id} ({persona_norm}) started for {company_name} ({position}).",
    }


# 12. Candidate Profile Tool
async def execute_get_candidate_profile(
    db: AsyncSession,
    section: str = "all",
) -> dict[str, Any]:
    """Retrieves verified candidate CV data, skills, domain tenures, or raw resume text."""
    stmt = (
        select(CandidateCVModel).order_by(CandidateCVModel.updated_at.desc()).limit(1)
    )
    res = await db.execute(stmt)
    cv = res.scalar_one_or_none()
    if not cv:
        return {
            "status": "not_found",
            "message": "No candidate CV profile has been uploaded yet.",
        }

    if section == "skills":
        return {
            "extracted_skills": cv.extracted_skills or [],
            "spoken_languages": cv.spoken_languages or [],
            "years_of_experience": cv.years_of_experience,
        }
    elif section == "experience":
        return {
            "years_of_experience": cv.years_of_experience,
            "domain_expertise": cv.domain_expertise or [],
            "domain_experience": cv.domain_experience or [],
            "summary": cv.summary or "",
        }
    elif section == "raw_cv":
        text_content = cv.anonymized_text or cv.raw_text or ""
        if len(text_content) > 4000:
            text_content = text_content[:4000] + "\n... [Truncated for brevity]"
        return {"cv_text": text_content}
    else:
        return {
            "summary": cv.summary or "",
            "years_of_experience": cv.years_of_experience,
            "extracted_skills": cv.extracted_skills or [],
            "domain_expertise": cv.domain_expertise or [],
            "domain_experience": cv.domain_experience or [],
            "spoken_languages": cv.spoken_languages or [],
        }


# 13. Web Search Tool
async def execute_search_web(
    db: AsyncSession,
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    """Performs live internet search via DuckDuckGo and returns concise snippets."""
    return await search_web(query=query, max_results=max_results, db=db)


# 14. Fetch Webpage Content Tool
async def execute_fetch_webpage_content(
    db: AsyncSession,
    url: str,
    max_chars: int = 3000,
) -> str:
    """Scrapes clean text content from a target URL using stealth scraper."""
    return await fetch_webpage_content(url=url, max_chars=max_chars, db=db)


# Helper for company resolution
async def _resolve_company(db: AsyncSession, company_or_id: str) -> CompanyModel | None:
    """Resolves a company by integer ID, application ID, or name (exact, normalized, or substring)."""
    if not company_or_id:
        return None
    raw = str(company_or_id).strip()

    # Check if numeric ID
    if raw.isdigit():
        c_id = int(raw)
        res = await db.execute(select(CompanyModel).where(CompanyModel.id == c_id))
        comp = res.scalar_one_or_none()
        if comp:
            return comp
        # Check if it was an application ID
        app_res = await db.execute(
            select(ApplicationModel)
            .options(joinedload(ApplicationModel.company))
            .where(ApplicationModel.id == c_id)
        )
        app = app_res.scalar_one_or_none()
        if app and app.company:
            return app.company

    norm_name = raw.lower()
    stmt = (
        select(CompanyModel)
        .where(
            or_(
                CompanyModel.name.ilike(raw),
                CompanyModel.name_normalized == norm_name,
                CompanyModel.name.ilike(f"%{raw}%"),
                CompanyModel.domain.ilike(f"%{raw}%"),
            )
        )
        .order_by((CompanyModel.name.ilike(raw)).desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    comp = res.scalars().first()
    if comp:
        return comp

    app_stmt = (
        select(ApplicationModel)
        .join(CompanyModel)
        .options(joinedload(ApplicationModel.company))
        .where(CompanyModel.name.ilike(f"%{raw}%"))
        .limit(1)
    )
    app_res = await db.execute(app_stmt)
    app = app_res.scalars().first()
    if app and app.company:
        return app.company

    return None


# 15. Get Company Details Tool
async def execute_get_company_details(
    db: AsyncSession,
    company_or_id: str,
) -> dict[str, Any]:
    """Retrieves comprehensive company entity details, candidate notes, pros/red flags, and AI web research summary."""
    company = await _resolve_company(db, company_or_id)
    if not company:
        return {
            "status": "not_found",
            "message": f"Company '{company_or_id}' could not be resolved from tracked companies or applications.",
        }

    app_stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.company_id == company.id)
        .order_by(ApplicationModel.updated_at.desc())
    )
    app_res = await db.execute(app_stmt)
    apps = app_res.scalars().all()
    apps_summary = [
        {
            "application_id": a.id,
            "position": a.position,
            "status": a.status,
            "application_date": (
                a.application_date.isoformat() if a.application_date else None
            ),
            "cover_letter_status": a.cover_letter_status,
        }
        for a in apps
    ]

    return {
        "status": "success",
        "company_id": company.id,
        "name": company.name,
        "domain": company.domain,
        "rating": company.rating,
        "candidate_rating": company.rating,
        "notes": company.notes or "",
        "pros": company.pros or [],
        "red_flags": company.red_flags or [],
        "research_status": company.research_status,
        "researched_at": (
            company.researched_at.isoformat() if company.researched_at else None
        ),
        "company_research": company.company_research or {},
        "applications": apps_summary,
        "applications_count": len(apps_summary),
    }


# 16. List Companies Tool
async def execute_list_companies(
    db: AsyncSession,
    has_research: bool | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Lists tracked companies with domain, candidate rating, application counts, and research status."""
    stmt = (
        select(CompanyModel)
        .options(selectinload(CompanyModel.applications))
        .order_by(CompanyModel.updated_at.desc())
    )
    res = await db.execute(stmt)
    companies = res.scalars().all()

    result = []
    for c in companies:
        has_summary = bool(c.company_research and c.company_research.get("summary"))
        if has_research is True and not has_summary:
            continue
        if has_research is False and has_summary:
            continue

        result.append(
            {
                "company_id": c.id,
                "name": c.name,
                "domain": c.domain,
                "rating": c.rating,
                "candidate_rating": c.rating,
                "research_status": c.research_status,
                "has_research": has_summary,
                "applications_count": len(c.applications) if c.applications else 0,
            }
        )
        if len(result) >= limit:
            break

    return result


# 17. Update Company Notes Tool
async def execute_update_company_notes(
    db: AsyncSession,
    company_or_id: str,
    notes: str | None = None,
    pros: list[str] | None = None,
    red_flags: list[str] | None = None,
    rating: int | None = None,
) -> dict[str, Any]:
    """Updates candidate notes, pros, red flags, or star rating (1-5) for a company."""
    company = await _resolve_company(db, company_or_id)
    if not company:
        return {
            "status": "not_found",
            "message": f"Company '{company_or_id}' could not be resolved.",
        }

    if notes is not None:
        company.notes = notes
    if pros is not None:
        company.pros = pros
    if red_flags is not None:
        company.red_flags = red_flags
    if rating is not None:
        company.rating = max(1, min(5, rating))

    await db.commit()
    await db.refresh(company)

    return {
        "status": "success",
        "company_id": company.id,
        "name": company.name,
        "rating": company.rating,
        "candidate_rating": company.rating,
        "notes": company.notes,
        "pros": company.pros,
        "red_flags": company.red_flags,
        "message": f"Updated candidate notes and profile for {company.name}.",
    }


# 18. Enqueue Company Research Tool
async def execute_enqueue_company_research(
    db: AsyncSession,
    company_or_id: str,
) -> dict[str, Any]:
    """Enqueues a background AI web research task for a target company."""
    import asyncio

    from app.services.evaluation_worker import process_evaluation_task

    company = await _resolve_company(db, company_or_id)
    if not company:
        return {
            "status": "not_found",
            "message": f"Company '{company_or_id}' could not be resolved.",
        }

    stmt = (
        select(IntakeEvaluationTaskModel)
        .where(
            IntakeEvaluationTaskModel.task_type == "COMPANY_RESEARCH",
            IntakeEvaluationTaskModel.raw_text == str(company.id),
            IntakeEvaluationTaskModel.status.in_(["QUEUED", "PROCESSING"]),
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return {
            "status": "already_active",
            "task_id": existing.id,
            "company_id": company.id,
            "company_name": company.name,
            "message": f"Company research for '{company.name}' is already active in AI Queue (Task #{existing.id}).",
        }

    task = IntakeEvaluationTaskModel(
        task_type="COMPANY_RESEARCH",
        raw_text=str(company.id),
        title_hint=f"Company Research: {company.name}",
        status="QUEUED",
        stage="QUEUED",
        result_json={
            "company_id": company.id,
            "company_name": company.name,
            "domain": company.domain,
        },
    )
    db.add(task)
    company.research_status = "QUEUED"
    await db.commit()
    await db.refresh(task)

    try:
        asyncio.create_task(process_evaluation_task(task_id=task.id))
    except Exception as e:
        logger.warning("Could not dispatch evaluation worker background task: %s", e)

    return {
        "status": "queued",
        "task_id": task.id,
        "company_id": company.id,
        "company_name": company.name,
        "message": f"Enqueued background company web research task #{task.id} for '{company.name}'.",
    }


# 19. Get Mock Interview History Tool
async def execute_get_mock_interview_history(
    db: AsyncSession,
    limit: int = 10,
    application_id: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieves history of past mock interview sessions, readiness ratings, STAR evaluation feedback, and overall scores."""
    from app.models.interview_session import InterviewSessionModel

    stmt = select(InterviewSessionModel).order_by(
        InterviewSessionModel.created_at.desc()
    )
    if application_id is not None:
        stmt = stmt.where(InterviewSessionModel.application_id == application_id)
    stmt = stmt.limit(limit)

    res = await db.execute(stmt)
    sessions = res.scalars().all()

    out = []
    for s in sessions:
        out.append(
            {
                "session_id": s.id,
                "application_id": s.application_id,
                "status": s.status,
                "persona": s.persona,
                "question_mode": s.question_mode,
                "overall_score": s.overall_score,
                "readiness_rating": s.readiness_rating,
                "summary_feedback": s.summary_feedback or "",
                "turns_count": len(s.turns_data) if s.turns_data else 0,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
    return out


# 20. Get Cover Letter Tool
async def execute_get_cover_letter(
    db: AsyncSession,
    application_id: int,
) -> dict[str, Any]:
    """Retrieves current cover letter status, text, and last generation timestamp for an application."""
    stmt = (
        select(ApplicationModel)
        .options(joinedload(ApplicationModel.company))
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        return {
            "status": "not_found",
            "message": f"Application #{application_id} not found.",
        }

    return {
        "status": "success",
        "application_id": app.id,
        "company": app.company.name if app.company else "Unknown",
        "position": app.position,
        "cover_letter_status": app.cover_letter_status or "NOT_GENERATED",
        "cover_letter_generated_at": (
            app.cover_letter_generated_at.isoformat()
            if app.cover_letter_generated_at
            else None
        ),
        "cover_letter_text": app.cover_letter_text or "",
    }


# 21. Enqueue Cover Letter Generation Tool
async def execute_enqueue_cover_letter_generation(
    db: AsyncSession,
    application_id: int,
    tone: str = "professional",
    length: str = "standard",
    custom_instructions: str | None = None,
    include_company_research: bool = True,
) -> dict[str, Any]:
    """Enqueues a background evaluation task to draft or regenerate a tailored cover letter for an application."""
    import asyncio

    from app.services.evaluation_worker import process_evaluation_task

    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
        )
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        return {
            "status": "not_found",
            "message": f"Application #{application_id} not found.",
        }

    comp_name = app.company.name if app.company else "Company"
    pos_name = app.position or "Position"
    comp_research = (
        app.company.company_research
        if (app.company and include_company_research)
        else None
    )

    task_record = IntakeEvaluationTaskModel(
        task_type="COVER_LETTER",
        job_url=app.job_url,
        raw_text=str(app.id),
        title_hint=f"Cover Letter ({tone}): {comp_name} - {pos_name}",
        status="QUEUED",
        stage="QUEUED",
        result_json={
            "application_id": app.id,
            "company": comp_name,
            "position": pos_name,
            "tone": tone,
            "length": length,
            "custom_instructions": custom_instructions,
            "include_company_research": include_company_research,
            "company_research": comp_research,
        },
    )
    db.add(task_record)
    app.cover_letter_status = "DRAFTED"
    await db.commit()
    await db.refresh(task_record)

    try:
        asyncio.create_task(process_evaluation_task(task_id=task_record.id))
    except Exception as e:
        logger.warning("Could not dispatch evaluation worker background task: %s", e)

    return {
        "status": "queued",
        "task_id": task_record.id,
        "application_id": app.id,
        "company": comp_name,
        "position": pos_name,
        "message": f"Enqueued cover letter generation task #{task_record.id} for {comp_name} ({pos_name}).",
    }


# 22. Get Application Questions Tool
async def execute_get_application_questions(
    db: AsyncSession,
    application_id: int,
) -> dict[str, Any]:
    """Retrieves custom application form Q&A pairs for an application."""
    stmt = (
        select(ApplicationModel)
        .options(joinedload(ApplicationModel.company))
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        return {
            "status": "not_found",
            "message": f"Application #{application_id} not found.",
        }

    raw_questions = app.application_questions or []
    return {
        "status": "success",
        "application_id": app.id,
        "company": app.company.name if app.company else "Unknown",
        "position": app.position,
        "questions_count": len(raw_questions),
        "questions": raw_questions,
    }


# 23. Enqueue Application Questions Tool
async def execute_enqueue_application_questions(
    db: AsyncSession,
    application_id: int,
    questions: list[str],
) -> dict[str, Any]:
    """Attaches custom application questions and enqueues a background task to generate tailored answers from candidate CV."""
    import asyncio

    from app.services.evaluation_worker import process_evaluation_task

    stmt = (
        select(ApplicationModel)
        .options(joinedload(ApplicationModel.company))
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        return {
            "status": "not_found",
            "message": f"Application #{application_id} not found.",
        }

    formatted_questions = [
        {
            "id": f"q_{idx + 1}",
            "question": q.strip(),
            "answer": None,
            "status": "QUEUED",
        }
        for idx, q in enumerate(questions)
        if q.strip()
    ]
    if not formatted_questions:
        return {
            "status": "error",
            "message": "No valid questions were provided.",
        }

    app.application_questions = formatted_questions
    task_record = IntakeEvaluationTaskModel(
        task_type="APPLICATION_QA",
        job_url=app.job_url,
        raw_text=str(app.id),
        title_hint=f"Application Q&A ({len(formatted_questions)} questions): {app.company.name if app.company else 'Company'}",
        status="QUEUED",
        stage="QUEUED",
        result_json={
            "application_id": app.id,
            "questions": formatted_questions,
        },
    )
    db.add(task_record)
    await db.commit()
    await db.refresh(task_record)

    try:
        asyncio.create_task(process_evaluation_task(task_id=task_record.id))
    except Exception as e:
        logger.warning("Could not dispatch evaluation worker background task: %s", e)

    return {
        "status": "queued",
        "task_id": task_record.id,
        "application_id": app.id,
        "questions_count": len(formatted_questions),
        "message": f"Enqueued Q&A answer generation task #{task_record.id} for {len(formatted_questions)} questions.",
    }


# 24. Get Role Alignment Career Dossier Tool
async def execute_get_role_alignment_dossier(
    db: AsyncSession,
    role_track: str | None = None,
) -> dict[str, Any]:
    """Retrieves high-impact role alignment career dossier (executive market positioning, tailored bullet rewrites, talking points, skill roadmaps)."""
    from app.services.role_alignment_dossier_service import get_role_alignment_dossier

    dossier = await get_role_alignment_dossier(db=db, role_track=role_track)
    if not dossier or not getattr(dossier, "role_track", None):
        return {
            "status": "not_found",
            "message": "No role alignment dossier found. Ensure a candidate CV profile is uploaded and evaluated.",
        }

    return {
        "status": "success",
        "dossier_id": getattr(dossier, "id", None),
        "role_track": dossier.role_track,
        "executive_positioning": getattr(dossier, "executive_positioning", {}) or {},
        "bullet_rewrites": getattr(dossier, "bullet_rewrites", []) or [],
        "interview_talking_points": (
            getattr(dossier, "interview_talking_points", []) or []
        ),
        "skill_bridge_roadmap": getattr(dossier, "skill_bridge_roadmap", []) or [],
        "generated_at": (
            dossier.generated_at.isoformat()
            if getattr(dossier, "generated_at", None)
            else None
        ),
    }


# 25. Bulk Transition Applications Tool
async def execute_bulk_transition_applications(
    db: AsyncSession,
    target_status: str,
    source_statuses: list[str] | None = None,
    application_ids: list[int] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Bulk transitions active non-terminal applications to a new status and logs timeline events."""
    TERMINAL = {"HIRED", "ARCHIVED", "WITHDRAWN", "REJECTED"}
    target = str(target_status).upper().strip()

    if not source_statuses:
        source_statuses = [
            "APPLIED",
            "ONLINE_ASSESSMENT",
            "TECHNICAL_INTERVIEW",
            "OFFER",
        ]

    safe_from = [
        s.upper().strip() for s in source_statuses if s.upper().strip() not in TERMINAL
    ]
    if not safe_from:
        return {
            "status": "ignored",
            "updated_count": 0,
            "updated_ids": [],
            "message": "No non-terminal source statuses provided to transition from.",
        }

    stmt = select(ApplicationModel).where(ApplicationModel.status.in_(safe_from))
    if application_ids:
        stmt = stmt.where(ApplicationModel.id.in_(application_ids))

    res = await db.execute(stmt)
    apps = res.scalars().all()

    now = datetime.now(UTC)
    note = reason or f"Bulk transitioned to {target} via AI Agent."
    updated_ids = []

    for app in apps:
        app.status = target
        app.last_activity_at = now
        event = ApplicationEventModel(
            email_application_id=app.id,
            email_event_type="STATUS_CHANGE",
            email_status_after_event=target,
            email_summary=note,
            source_channel="AGENT",
            raw_payload={"bulk_action": True, "target_status": target},
        )
        db.add(event)

        if target in TERMINAL:
            ai_stmt = select(ActionItemModel).where(
                ActionItemModel.application_id == app.id,
                ActionItemModel.status == "PENDING",
            )
            ai_res = await db.execute(ai_stmt)
            for ai in ai_res.scalars().all():
                ai.status = "DISMISSED"

        updated_ids.append(app.id)

    await db.commit()
    return {
        "status": "success",
        "target_status": target,
        "updated_count": len(updated_ids),
        "updated_ids": updated_ids,
        "message": f"Successfully transitioned {len(updated_ids)} applications to {target}.",
    }


def create_agent_tools(
    db: AsyncSession, enable_web_search: bool = False
) -> list[StructuredTool]:
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
        include_assessments: bool = False,
        limit: int = 20,
    ) -> str:
        res = await execute_list_applications(
            db, status, action_required_only, include_assessments, limit
        )
        return json.dumps(res, indent=2)

    async def _get_upcoming_interviews(
        days_ahead: int = 30,
        include_pending_scheduling: bool = True,
    ) -> str:
        res = await execute_get_upcoming_interviews(
            db, days_ahead, include_pending_scheduling
        )
        return json.dumps(res, indent=2)

    async def _get_application_details(company_or_id: str) -> str:
        res = await execute_get_application_details(db, company_or_id)
        return json.dumps(res, indent=2)

    async def _start_mock_interview(
        company_or_id: str | None = None,
        question_mode: str = "TEXT_CONVERSATIONAL",
        interviewer_persona: str = "TECHNICAL_BAR_RAISER",
    ) -> str:
        res = await execute_start_mock_interview(
            db, company_or_id, question_mode, interviewer_persona
        )
        return json.dumps(res, indent=2)

    async def _get_mock_interview_history(
        limit: int = 10,
        application_id: int | None = None,
    ) -> str:
        res = await execute_get_mock_interview_history(db, limit, application_id)
        return json.dumps(res, indent=2)

    async def _get_candidate_profile(section: str = "all") -> str:
        res = await execute_get_candidate_profile(db, section)
        return json.dumps(res, indent=2)

    async def _get_company_details(company_or_id: str) -> str:
        res = await execute_get_company_details(db, company_or_id)
        return json.dumps(res, indent=2)

    async def _list_companies(
        has_research: bool | None = None,
        limit: int = 20,
    ) -> str:
        res = await execute_list_companies(db, has_research, limit)
        return json.dumps(res, indent=2)

    async def _update_company_notes(
        company_or_id: str,
        notes: str | None = None,
        pros: list[str] | None = None,
        red_flags: list[str] | None = None,
        rating: int | None = None,
    ) -> str:
        res = await execute_update_company_notes(
            db, company_or_id, notes, pros, red_flags, rating
        )
        return json.dumps(res, indent=2)

    async def _enqueue_company_research(company_or_id: str) -> str:
        res = await execute_enqueue_company_research(db, company_or_id)
        return json.dumps(res, indent=2)

    async def _get_cover_letter(application_id: int) -> str:
        res = await execute_get_cover_letter(db, application_id)
        return json.dumps(res, indent=2)

    async def _enqueue_cover_letter_generation(
        application_id: int,
        tone: str = "professional",
        length: str = "standard",
        custom_instructions: str | None = None,
        include_company_research: bool = True,
    ) -> str:
        res = await execute_enqueue_cover_letter_generation(
            db,
            application_id,
            tone,
            length,
            custom_instructions,
            include_company_research,
        )
        return json.dumps(res, indent=2)

    async def _get_application_questions(application_id: int) -> str:
        res = await execute_get_application_questions(db, application_id)
        return json.dumps(res, indent=2)

    async def _enqueue_application_questions(
        application_id: int,
        questions: list[str],
    ) -> str:
        res = await execute_enqueue_application_questions(db, application_id, questions)
        return json.dumps(res, indent=2)

    async def _get_role_alignment_dossier(role_track: str | None = None) -> str:
        res = await execute_get_role_alignment_dossier(db, role_track)
        return json.dumps(res, indent=2)

    async def _bulk_transition_applications(
        target_status: str,
        source_statuses: list[str] | None = None,
        application_ids: list[int] | None = None,
        reason: str | None = None,
    ) -> str:
        res = await execute_bulk_transition_applications(
            db, target_status, source_statuses, application_ids, reason
        )
        return json.dumps(res, indent=2)

    async def _search_web(query: str, max_results: int = 5) -> str:
        res = await execute_search_web(db, query, max_results)
        return json.dumps(res, indent=2)

    async def _fetch_webpage_content(url: str, max_chars: int = 3000) -> str:
        res = await execute_fetch_webpage_content(db, url, max_chars)
        return str(res)

    tools = [
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
            description="Searches application records and recruitment correspondence. Uses pgvector semantic similarity when embeddings are enabled, or fast keyword search when embeddings are disabled.",
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
            description="Lists job applications directly from the database. Use status='ACTIVE' for all 4 active stages (APPLIED, ONLINE_ASSESSMENT, TECHNICAL_INTERVIEW, OFFER). Pre-application AI job fit assessments (is_assessment=True) are excluded by default.",
            args_schema=ListApplicationsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_upcoming_interviews,
            name="get_upcoming_interviews",
            description="Retrieves upcoming interviews with confirmed dates and times, plus applications in interview stages awaiting scheduling or recruiter replies. Always use this tool when the user asks about upcoming interviews or interview dates.",
            args_schema=GetUpcomingInterviewsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_application_details,
            name="get_application_details",
            description="Retrieves chronological timeline events, recruiter emails, and action items for a company or application ID.",
            args_schema=ApplicationDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_start_mock_interview,
            name="start_mock_interview",
            description="Launches an interactive live mock interview simulation for a target application or general software engineering practice.",
            args_schema=StartMockInterviewInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_mock_interview_history,
            name="get_mock_interview_history",
            description="Retrieves history of past mock interview simulations, overall scores, readiness ratings, and rubric feedback.",
            args_schema=GetMockInterviewHistoryInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_candidate_profile,
            name="get_candidate_profile",
            description="Retrieves the candidate's verified profile, top technical skills, spoken languages, domain expertise breakdown, or raw CV text.",
            args_schema=GetCandidateProfileInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_company_details,
            name="get_company_details",
            description="Retrieves comprehensive company entity details, domain, user notes, pros/red flags, and synthesized AI web research dossier.",
            args_schema=GetCompanyDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_list_companies,
            name="list_companies",
            description="Lists tracked companies with domain, candidate star rating, application counts, and research completion status.",
            args_schema=ListCompaniesInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_company_notes,
            name="update_company_notes",
            description="Updates candidate notes, pros, red flags, or 1-5 star rating for a tracked company.",
            args_schema=UpdateCompanyNotesInput,
        ),
        StructuredTool.from_function(
            coroutine=_enqueue_company_research,
            name="enqueue_company_research",
            description="Enqueues a background AI web research task in the intake evaluation queue to gather intelligence, mission, tech culture, and reviews for a company.",
            args_schema=EnqueueCompanyResearchInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_cover_letter,
            name="get_cover_letter",
            description="Retrieves the drafted or generated cover letter markdown text, generation timestamp, and status for an application ID.",
            args_schema=GetCoverLetterInput,
        ),
        StructuredTool.from_function(
            coroutine=_enqueue_cover_letter_generation,
            name="enqueue_cover_letter_generation",
            description="Enqueues a background task in the evaluation queue to generate or regenerate a tailored cover letter grounded in candidate CV and company research.",
            args_schema=EnqueueCoverLetterGenerationInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_application_questions,
            name="get_application_questions",
            description="Retrieves custom application form questions, drafted answers, and generation statuses for an application ID.",
            args_schema=GetApplicationQuestionsInput,
        ),
        StructuredTool.from_function(
            coroutine=_enqueue_application_questions,
            name="enqueue_application_questions",
            description="Attaches custom application questions to an application and enqueues a background task to generate tailored answers from candidate CV.",
            args_schema=EnqueueApplicationQuestionsInput,
        ),
        StructuredTool.from_function(
            coroutine=_get_role_alignment_dossier,
            name="get_role_alignment_dossier",
            description="Retrieves high-impact role alignment career dossier (executive market positioning, tailored bullet rewrites, talking points, skill roadmaps) for a role track.",
            args_schema=GetRoleAlignmentDossierInput,
        ),
        StructuredTool.from_function(
            coroutine=_bulk_transition_applications,
            name="bulk_transition_applications",
            description="Transitions batches of non-terminal applications simultaneously (e.g. archiving or withdrawing remaining active jobs upon offer/hired).",
            args_schema=BulkTransitionApplicationsInput,
        ),
    ]

    if enable_web_search:
        tools.extend(
            [
                StructuredTool.from_function(
                    coroutine=_search_web,
                    name="search_web",
                    description="Searches the live internet via DuckDuckGo for recent company news, engineering blogs, salaries, or real-time information.",
                    args_schema=SearchWebInput,
                ),
                StructuredTool.from_function(
                    coroutine=_fetch_webpage_content,
                    name="fetch_webpage_content",
                    description="Scrapes clean text from a specific webpage URL found in search results to read articles, job details, or documentation.",
                    args_schema=FetchWebpageContentInput,
                ),
            ]
        )

    return tools
