import datetime
from collections import defaultdict

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.schemas.analytics import (
    ActivityAnalyticsResponse,
    ActivityDailyBreakdown,
    ActivityHistoryBucket,
    ActivityHistoryResponse,
    AnalyticsOverviewResponse,
    FunnelStageItem,
    SkillDemandItem,
    SkillGapItem,
    TerminalOutcomes,
    WorkModelBreakdown,
)


async def get_analytics_overview(
    db: AsyncSession,
    days_limit: int | None = None,
    work_model: str | None = None,
    top_n_skills: int | None = None,
) -> AnalyticsOverviewResponse:
    # 1. Fetch the active candidate CV to get extracted_skills
    cv_query = select(CandidateCVModel).where(CandidateCVModel.is_active).limit(1)
    cv_result = await db.execute(cv_query)
    cv = cv_result.scalar_one_or_none()
    candidate_skills = set(cv.extracted_skills) if cv and cv.extracted_skills else set()

    # 2. Build the base query for Applications and JobPostings
    base_filters = []
    if days_limit is not None:
        cutoff_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            days=days_limit
        )
        base_filters.append(ApplicationModel.application_date >= cutoff_date)

    if work_model and work_model.lower() != "all":
        base_filters.append(JobPostingModel.work_model.ilike(f"%{work_model}%"))

    query = (
        select(ApplicationModel, JobPostingModel, CompanyModel)
        .outerjoin(
            JobPostingModel, ApplicationModel.id == JobPostingModel.application_id
        )
        .outerjoin(CompanyModel, ApplicationModel.company_id == CompanyModel.id)
    )

    if base_filters:
        query = query.where(and_(*base_filters))

    result = await db.execute(query)
    rows = result.all()

    # 3. Initialize metrics
    total_applications = len(rows)
    active_pipeline_count = 0

    # Funnel counts
    funnel_counts = {
        "Applied": 0,
        "Assessment": 0,
        "Interview": 0,
        "Offer": 0,
    }

    work_models = {"remote": 0, "hybrid": 0, "onsite": 0, "unknown": 0}

    skill_counts = defaultdict(int)
    skill_salaries = defaultdict(lambda: {"min": [], "max": []})

    gap_frequencies = defaultdict(int)
    gap_companies = defaultdict(set)
    gap_job_counts = defaultdict(int)
    gap_salaries = defaultdict(list)

    fit_scores = []

    # Map status to generic funnel stages
    def get_funnel_stage(status: str) -> str | None:
        status = status.upper()
        if status in ["APPLIED", "IN_PROGRESS"]:
            return "Applied"
        elif status == "ONLINE_ASSESSMENT":
            return "Assessment"
        elif status == "TECHNICAL_INTERVIEW" or "INTERVIEW" in status:
            return "Interview"
        elif status == "OFFER":
            return "Offer"
        return None

    def get_funnel_level(stage: str) -> int:
        levels = {"Applied": 1, "Assessment": 2, "Interview": 3, "Offer": 4}
        return levels.get(stage, 0)

    def get_level(status: str) -> int:
        status = status.upper() if status else ""
        if status == "OFFER":
            return 4
        if status == "TECHNICAL_INTERVIEW" or "INTERVIEW" in status:
            return 3
        if status == "ONLINE_ASSESSMENT":
            return 2
        if status in ["APPLIED", "IN_PROGRESS", "REJECTED"]:
            return 1
        return 1

    for app, job, company in rows:
        status = app.status.upper() if app.status else "PENDING"
        if status not in ["REJECTED", "PENDING", "COMPLETED"]:
            active_pipeline_count += 1

        app_level = get_level(status)
        if app_level >= 1:
            funnel_counts["Applied"] += 1
        if app_level >= 2:
            funnel_counts["Assessment"] += 1
        if app_level >= 3:
            funnel_counts["Interview"] += 1
        if app_level >= 4:
            funnel_counts["Offer"] += 1

        if app.match_analysis_payload:
            if "fit_score" in app.match_analysis_payload:
                try:
                    score = float(app.match_analysis_payload["fit_score"])
                    fit_scores.append(score)
                except Exception:
                    pass

            # Analyze missing skills from match analysis
            if "missing_skills" in app.match_analysis_payload:
                missing = app.match_analysis_payload["missing_skills"]
                if isinstance(missing, list):
                    for skill in missing:
                        skill_str = str(skill)
                        if skill_str not in candidate_skills:
                            gap_frequencies[skill_str] += 1
                            gap_job_counts[skill_str] += 1
                            if company:
                                gap_companies[skill_str].add(company.name)
                            if job and job.salary_min:
                                gap_salaries[skill_str].append(job.salary_min)
            elif (
                "programmatic_match_score" in app.match_analysis_payload
            ):  # Fallback analysis
                pass

        if job:
            wm = job.work_model.lower() if job.work_model else "unknown"
            if "remote" in wm:
                work_models["remote"] += 1
            elif "hybrid" in wm:
                work_models["hybrid"] += 1
            elif "onsite" in wm or "office" in wm:
                work_models["onsite"] += 1
            else:
                work_models["unknown"] += 1

            if job.required_skills:
                for skill in job.required_skills:
                    skill_counts[skill] += 1
                    if job.salary_min is not None:
                        skill_salaries[skill]["min"].append(job.salary_min)
                    if job.salary_max is not None:
                        skill_salaries[skill]["max"].append(job.salary_max)

                    # Also fallback gap calculation
                    if skill not in candidate_skills:
                        gap_frequencies[skill] += 1
                        gap_job_counts[skill] += 1
                        if company:
                            gap_companies[skill].add(company.name)
                        if job.salary_min:
                            gap_salaries[skill].append(job.salary_min)

    # 4. Calculate final metrics
    interview_rate = 0.0
    offer_rate = 0.0
    if total_applications > 0:
        interview_rate = (funnel_counts["Interview"] / total_applications) * 100.0
        offer_rate = (funnel_counts["Offer"] / total_applications) * 100.0

    avg_fit_score = sum(fit_scores) / len(fit_scores) if fit_scores else None

    # Top Demand Skills
    top_skills_sorted = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    if top_n_skills is not None and top_n_skills > 0:
        top_skills_sorted = top_skills_sorted[:top_n_skills]
    top_in_demand_skills = []
    for skill, count in top_skills_sorted:
        pct = (count / total_applications * 100) if total_applications > 0 else 0
        s_min_list = skill_salaries[skill]["min"]
        s_max_list = skill_salaries[skill]["max"]
        avg_s_min = sum(s_min_list) / len(s_min_list) if s_min_list else None
        avg_s_max = sum(s_max_list) / len(s_max_list) if s_max_list else None

        top_in_demand_skills.append(
            SkillDemandItem(
                skill=skill,
                count=count,
                percentage=pct,
                avg_salary_min=avg_s_min,
                avg_salary_max=avg_s_max,
                is_in_candidate_cv=skill in candidate_skills,
            )
        )

    # Skill Gaps
    gap_skills_sorted = sorted(
        gap_frequencies.items(), key=lambda x: x[1], reverse=True
    )
    if top_n_skills is not None and top_n_skills > 0:
        gap_skills_sorted = gap_skills_sorted[:top_n_skills]
    priority_skill_gaps = []
    for skill, freq in gap_skills_sorted:
        salaries = gap_salaries[skill]
        avg_sal = sum(salaries) / len(salaries) if salaries else 0
        priority_score = freq * (1 + (avg_sal / 100000))  # Simple priority formula

        priority_skill_gaps.append(
            SkillGapItem(
                skill=skill,
                missing_frequency=freq,
                target_job_count=gap_job_counts[skill],
                priority_score=priority_score,
                sample_companies=list(gap_companies[skill])[:3],
            )
        )

    # Funnel
    pipeline_funnel = []
    stages = ["Applied", "Assessment", "Interview", "Offer"]
    for i, stage in enumerate(stages):
        count = funnel_counts[stage]
        conv_rate = (count / total_applications * 100) if total_applications > 0 else 0

        dropoff_rate = 0.0
        if i > 0:
            prev_count = funnel_counts[stages[i - 1]]
            if prev_count > 0:
                dropoff_rate = ((prev_count - count) / prev_count) * 100
            else:
                dropoff_rate = 100.0 if count == 0 else 0.0

        pipeline_funnel.append(
            FunnelStageItem(
                stage=stage,
                count=count,
                conversion_rate=conv_rate,
                dropoff_rate=dropoff_rate,
            )
        )

    # Work Model
    work_model_distribution = WorkModelBreakdown(
        remote_count=work_models["remote"],
        hybrid_count=work_models["hybrid"],
        onsite_count=work_models["onsite"],
        unknown_count=work_models["unknown"],
    )

    # Salary Insights (basic overall calculation)
    # Using top skills salary info
    salary_insights = [
        {
            "skill": item.skill,
            "avg_min": item.avg_salary_min,
            "avg_max": item.avg_salary_max,
        }
        for item in top_in_demand_skills
        if item.avg_salary_min or item.avg_salary_max
    ]

    return AnalyticsOverviewResponse(
        total_applications=total_applications,
        active_pipeline_count=active_pipeline_count,
        interview_rate=interview_rate,
        offer_rate=offer_rate,
        average_fit_score=avg_fit_score,
        top_in_demand_skills=top_in_demand_skills,
        priority_skill_gaps=priority_skill_gaps,
        pipeline_funnel=pipeline_funnel,
        work_model_distribution=work_model_distribution,
        salary_insights=salary_insights,
    )


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    return sourcedate.replace(year=year, month=month)


def get_utc_bounds(
    period: str, start_date: str | None = None, end_date: str | None = None
) -> tuple[datetime.datetime, datetime.datetime]:
    now = datetime.datetime.now(datetime.UTC)
    if period == "this_week":
        start = now - datetime.timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == "last_week":
        start = now - datetime.timedelta(days=now.weekday() + 7)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = add_months(start, 1)
        end = next_month - datetime.timedelta(seconds=1)
    elif period == "last_month":
        last_month_start = add_months(
            now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), -1
        )
        start = last_month_start
        next_month = add_months(start, 1)
        end = next_month - datetime.timedelta(seconds=1)
    elif period == "custom":
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required for custom period")
        start = datetime.datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end = datetime.datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        raise ValueError(f"Invalid period: {period}")
    return start, end


async def get_activity_analytics(
    db: AsyncSession,
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> ActivityAnalyticsResponse:
    start, end = get_utc_bounds(period, start_date, end_date)

    app_query = select(ApplicationModel).where(
        and_(ApplicationModel.created_at >= start, ApplicationModel.created_at <= end)
    )
    app_res = await db.execute(app_query)
    apps = app_res.scalars().all()
    applications_submitted = len(apps)

    reply_query = select(ApplicationEventModel).where(
        and_(
            ApplicationEventModel.created_at >= start,
            ApplicationEventModel.created_at <= end,
            ApplicationEventModel.email_event_type.notin_(
                ["EMAIL_SENT", "SYSTEM_EVENT"]
            ),
        )
    )
    reply_res = await db.execute(reply_query)
    replies = reply_res.scalars().all()
    replies_received = len(replies)

    interview_query = select(ApplicationEventModel).where(
        and_(
            ApplicationEventModel.created_at >= start,
            ApplicationEventModel.created_at <= end,
            ApplicationEventModel.email_event_type.ilike("%INTERVIEW%"),
        )
    )
    interview_res = await db.execute(interview_query)
    interviews_scheduled = len(interview_res.scalars().all())

    app_interview_query = select(ApplicationModel).where(
        and_(
            ApplicationModel.updated_at >= start,
            ApplicationModel.updated_at <= end,
            ApplicationModel.status.ilike("%INTERVIEW%"),
        )
    )
    app_interview_res = await db.execute(app_interview_query)
    interviews_scheduled += len(app_interview_res.scalars().all())

    task_query = select(ActionItemModel).where(
        and_(
            ActionItemModel.updated_at >= start,
            ActionItemModel.updated_at <= end,
            ActionItemModel.status == "COMPLETED",
        )
    )
    task_res = await db.execute(task_query)
    tasks = task_res.scalars().all()
    tasks_completed = len(tasks)

    terminal = {"OFFER": 0, "HIRED": 0, "REJECTED": 0, "WITHDRAWN": 0}
    term_app_query = select(ApplicationModel).where(
        and_(
            ApplicationModel.updated_at >= start,
            ApplicationModel.updated_at <= end,
            ApplicationModel.status.in_(["OFFER", "HIRED", "REJECTED", "WITHDRAWN"]),
        )
    )
    term_app_res = await db.execute(term_app_query)
    term_apps = term_app_res.scalars().all()
    for app in term_apps:
        if app.status.upper() in terminal:
            terminal[app.status.upper()] += 1

    daily_map = defaultdict(
        lambda: {"applications": 0, "replies": 0, "interviews": 0, "tasks": 0}
    )

    for a in apps:
        dt_str = a.created_at.strftime("%Y-%m-%d")
        daily_map[dt_str]["applications"] += 1

    for r in replies:
        dt_str = r.created_at.strftime("%Y-%m-%d")
        daily_map[dt_str]["replies"] += 1

    for t in tasks:
        dt_str = t.updated_at.strftime("%Y-%m-%d")
        daily_map[dt_str]["tasks"] += 1

    daily_breakdown = []
    curr_date = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date_clean = end.replace(hour=0, minute=0, second=0, microsecond=0)

    while curr_date <= end_date_clean:
        dt_str = curr_date.strftime("%Y-%m-%d")
        daily_breakdown.append(
            ActivityDailyBreakdown(
                date=dt_str,
                applications=daily_map[dt_str]["applications"],
                replies=daily_map[dt_str]["replies"],
                interviews=0,
                tasks=daily_map[dt_str]["tasks"],
            )
        )
        curr_date += datetime.timedelta(days=1)

    return ActivityAnalyticsResponse(
        period=period,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        applications_submitted=applications_submitted,
        replies_received=replies_received,
        interviews_scheduled=interviews_scheduled,
        tasks_completed=tasks_completed,
        terminal_outcomes=TerminalOutcomes(**terminal),
        daily_breakdown=daily_breakdown,
    )


async def get_activity_history(db: AsyncSession) -> ActivityHistoryResponse:
    now = datetime.datetime.now(datetime.UTC)
    twelve_weeks_ago = now - datetime.timedelta(weeks=12)

    query = text("""
        WITH weeks AS (
            SELECT generate_series(
                date_trunc('week', :start_date::timestamp),
                date_trunc('week', :end_date::timestamp),
                '1 week'::interval
            ) AS week_start
        ),
        app_counts AS (
            SELECT date_trunc('week', created_at) AS week_start, COUNT(*) as app_count
            FROM email_applications
            WHERE created_at >= :start_date
            GROUP BY 1
        ),
        task_counts AS (
            SELECT date_trunc('week', updated_at) AS week_start, COUNT(*) as task_count
            FROM action_items
            WHERE updated_at >= :start_date AND status = 'COMPLETED'
            GROUP BY 1
        ),
        reply_counts AS (
            SELECT date_trunc('week', created_at) AS week_start, COUNT(*) as reply_count
            FROM email_application_events
            WHERE created_at >= :start_date AND email_event_type NOT IN ('EMAIL_SENT', 'SYSTEM_EVENT')
            GROUP BY 1
        )
        SELECT
            w.week_start,
            COALESCE(a.app_count, 0) as applications,
            COALESCE(t.task_count, 0) as tasks,
            COALESCE(r.reply_count, 0) as replies
        FROM weeks w
        LEFT JOIN app_counts a ON w.week_start = a.week_start
        LEFT JOIN task_counts t ON w.week_start = t.week_start
        LEFT JOIN reply_counts r ON w.week_start = r.week_start
        ORDER BY w.week_start ASC
    """)

    result = await db.execute(query, {"start_date": twelve_weeks_ago, "end_date": now})
    rows = result.all()

    history = []
    for row in rows:
        week_start = row.week_start
        if not isinstance(week_start, datetime.datetime):
            week_start = datetime.datetime.fromisoformat(str(week_start))
        week_end = week_start + datetime.timedelta(
            days=6, hours=23, minutes=59, seconds=59
        )
        history.append(
            ActivityHistoryBucket(
                week_start=week_start.isoformat(),
                week_end=week_end.isoformat(),
                applications=row.applications,
                replies=row.replies,
                interviews=0,
                tasks=row.tasks,
            )
        )

    return ActivityHistoryResponse(history=history)
