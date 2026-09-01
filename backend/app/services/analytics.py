import datetime
import logging
from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    BulletReframeItem,
    FunnelChartStage,
    FunnelCohortPeriod,
    FunnelKpiCard,
    FunnelMetricsResponse,
    FunnelStageItem,
    RoleAlignmentResponse,
    RoleTrackCluster,
    SalaryInsightItem,
    SkillDemandItem,
    SkillGapItem,
    VocabularyShiftItem,
    WorkModelBreakdown,
)
from app.services.skill_normalizer import normalize_skill, normalize_skills_list

logger = logging.getLogger(__name__)

# Cache stores: { cache_key: (fingerprint, response_model) }
_OVERVIEW_CACHE: dict[tuple, tuple[tuple[int, int], AnalyticsOverviewResponse]] = {}
_FUNNEL_CACHE: dict[tuple, tuple[tuple[int, int, int], FunnelMetricsResponse]] = {}
_ROLE_ALIGNMENT_CACHE: dict[tuple, tuple[tuple[int, int], RoleAlignmentResponse]] = {}


async def _get_applications_fingerprint(db: AsyncSession) -> tuple[int, int]:
    """Lightweight indexed check returning (total_applications_count, max_application_id)."""
    try:
        stmt = select(
            func.count(ApplicationModel.id),
            func.coalesce(func.max(ApplicationModel.id), 0),
        )
        res = await db.execute(stmt)
        row = res.first()
        if row:
            return (int(row[0] or 0), int(row[1] or 0))
    except Exception:
        pass
    return (0, 0)


async def _get_role_alignment_fingerprint(db: AsyncSession) -> tuple[int, int]:
    """Lightweight indexed check returning (analyzed_applications_count, max_analyzed_id)."""
    try:
        stmt = select(
            func.count(ApplicationModel.id),
            func.coalesce(func.max(ApplicationModel.id), 0),
        ).where(ApplicationModel.match_analysis_payload.isnot(None))
        res = await db.execute(stmt)
        row = res.first()
        if row:
            return (int(row[0] or 0), int(row[1] or 0))
    except Exception:
        pass
    return (0, 0)


async def _get_funnel_fingerprint(db: AsyncSession) -> tuple[int, int, int]:
    """Lightweight indexed check returning (apps_count, max_app_id, intake_tasks_count)."""
    try:
        app_stmt = select(
            func.count(ApplicationModel.id),
            func.coalesce(func.max(ApplicationModel.id), 0),
        )
        app_row = (await db.execute(app_stmt)).first()
        app_count = int(app_row[0] or 0) if app_row else 0
        max_app_id = int(app_row[1] or 0) if app_row else 0

        intake_stmt = select(func.count(IntakeEvaluationTaskModel.id))
        intake_res = (await db.execute(intake_stmt)).scalar() or 0
        return (app_count, max_app_id, int(intake_res))
    except Exception:
        pass
    return (0, 0, 0)


def clear_analytics_cache(domain: str | None = None) -> None:
    """
    Clears in-memory caches for analytics computations.
    If domain is provided ('overview', 'funnel', 'alignment'), clears only that domain.
    Otherwise clears all analytics caches.
    """
    global _OVERVIEW_CACHE, _FUNNEL_CACHE, _ROLE_ALIGNMENT_CACHE
    if domain == "overview":
        _OVERVIEW_CACHE.clear()
    elif domain == "funnel":
        _FUNNEL_CACHE.clear()
    elif domain == "alignment":
        _ROLE_ALIGNMENT_CACHE.clear()
    else:
        _OVERVIEW_CACHE.clear()
        _FUNNEL_CACHE.clear()
        _ROLE_ALIGNMENT_CACHE.clear()


async def get_analytics_overview(
    db: AsyncSession,
    days_limit: int | None = None,
    work_model: str | None = None,
    top_n_skills: int | None = None,
    use_cache: bool = True,
) -> AnalyticsOverviewResponse:
    cache_key = (days_limit, (work_model or "").strip().lower(), top_n_skills)
    current_fp = (0, 0)
    if use_cache:
        current_fp = await _get_applications_fingerprint(db)
        if cache_key in _OVERVIEW_CACHE:
            cached_fp, cached_res = _OVERVIEW_CACHE[cache_key]
            if cached_fp == current_fp:
                return cached_res

    candidate_skills = set()
    rows = []

    try:
        # 1. Fetch the candidate CV to get extracted_skills
        cv_query = select(CandidateCVModel).limit(1)
        cv_result = await db.execute(cv_query)
        cv = cv_result.scalar_one_or_none()
        candidate_skills = set(
            normalize_skills_list(cv.extracted_skills)
            if cv and cv.extracted_skills
            else []
        )

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
    except Exception as exc:
        logger.warning(f"Error querying database for analytics overview: {exc}")

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
    skill_salaries = defaultdict(lambda: {"min": [], "max": [], "midpoints": []})

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
                        skill_str = normalize_skill(str(skill))
                        if skill_str and skill_str not in candidate_skills:
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
                norm_req_skills = normalize_skills_list(job.required_skills)
                for skill in norm_req_skills:
                    skill_counts[skill] += 1
                    midpoint = None
                    if job.salary_min is not None and job.salary_max is not None:
                        midpoint = (job.salary_min + job.salary_max) / 2.0
                    elif job.salary_min is not None:
                        midpoint = float(job.salary_min)
                    elif job.salary_max is not None:
                        midpoint = float(job.salary_max)

                    if job.salary_min is not None:
                        skill_salaries[skill]["min"].append(float(job.salary_min))
                    if job.salary_max is not None:
                        skill_salaries[skill]["max"].append(float(job.salary_max))
                    if midpoint is not None:
                        skill_salaries[skill]["midpoints"].append(midpoint)

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

    def trim_outliers(values: list[float]) -> list[float]:
        if len(values) < 3:
            return values
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if 3 <= n <= 4:
            return sorted_vals[1:-1]
        import math

        low_idx = int(math.floor(n * 0.10))
        high_idx = int(math.ceil(n * 0.90))
        trimmed = sorted_vals[low_idx:high_idx]
        return trimmed if trimmed else sorted_vals

    def calc_median(values: list[float]) -> float | None:
        if not values:
            return None
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 1:
            return sorted_vals[mid]
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

    # Top Demand Skills
    top_skills_sorted = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    if top_n_skills is not None and top_n_skills > 0:
        top_skills_sorted = top_skills_sorted[:top_n_skills]
    top_in_demand_skills = []
    salary_insights = []

    for skill, count in top_skills_sorted:
        pct = (count / total_applications * 100) if total_applications > 0 else 0
        s_min_list = skill_salaries[skill]["min"]
        s_max_list = skill_salaries[skill]["max"]
        s_mid_list = skill_salaries[skill]["midpoints"]

        trimmed_min = trim_outliers(s_min_list)
        trimmed_max = trim_outliers(s_max_list)
        trimmed_mid = trim_outliers(s_mid_list)

        avg_s_min = sum(trimmed_min) / len(trimmed_min) if trimmed_min else None
        avg_s_max = sum(trimmed_max) / len(trimmed_max) if trimmed_max else None
        median_sal = calc_median(trimmed_mid)
        sample_cnt = len(s_mid_list) if s_mid_list else 1

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

        if avg_s_min or avg_s_max or median_sal:
            salary_insights.append(
                SalaryInsightItem(
                    skill=skill,
                    avg_min=avg_s_min,
                    avg_max=avg_s_max,
                    median_salary=median_sal,
                    sample_count=sample_cnt,
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

    overview_resp = AnalyticsOverviewResponse(
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
    if use_cache:
        _OVERVIEW_CACHE[cache_key] = (current_fp, overview_resp)
    return overview_resp


async def get_funnel_performance_metrics(
    db: AsyncSession,
    period: str = "weekly",
    num_periods: int = 8,
    use_cache: bool = True,
) -> FunnelMetricsResponse:
    """
    Aggregates intake leads, applications, interviews, and offers by cohort periods (weekly or monthly).
    Calculates summary KPIs with trend deltas vs the previous period and builds cohort tables and chart data.
    """
    normalized_period = (
        "monthly" if (period or "").strip().lower() == "monthly" else "weekly"
    )
    cache_key = (normalized_period, num_periods)
    current_fp = (0, 0, 0)
    if use_cache:
        current_fp = await _get_funnel_fingerprint(db)
        if cache_key in _FUNNEL_CACHE:
            cached_fp, cached_res = _FUNNEL_CACHE[cache_key]
            if cached_fp == current_fp:
                return cached_res

    now = datetime.datetime.now(datetime.UTC)

    # Build cohort periods boundaries
    periods = []
    if period == "monthly":
        # Current month
        year = now.year
        month = now.month
        for _ in range(num_periods):
            # Calculate start and end of month
            start_dt = datetime.datetime(year, month, 1, tzinfo=datetime.UTC)
            if month == 12:
                next_month_start = datetime.datetime(
                    year + 1, 1, 1, tzinfo=datetime.UTC
                )
            else:
                next_month_start = datetime.datetime(
                    year, month + 1, 1, tzinfo=datetime.UTC
                )
            end_dt = next_month_start - datetime.timedelta(microseconds=1)
            period_key = f"{year}-{month:02d}"
            period_label = start_dt.strftime("%b %Y")

            periods.append(
                {
                    "key": period_key,
                    "label": period_label,
                    "start": start_dt,
                    "end": end_dt,
                }
            )

            # Move back 1 month
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
    else:  # weekly (Mon-Sun)
        # Start of current week (Monday)
        current_mon = now - datetime.timedelta(days=now.weekday())
        current_mon = current_mon.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.UTC
        )

        for i in range(num_periods):
            start_dt = current_mon - datetime.timedelta(weeks=i)
            end_dt = start_dt + datetime.timedelta(
                days=6, hours=23, minutes=59, seconds=59, microseconds=999999
            )
            period_key = start_dt.strftime("%Y-W%U")
            period_label = f"W{start_dt.strftime('%U')} ({start_dt.strftime('%b %d')})"

            periods.append(
                {
                    "key": period_key,
                    "label": period_label,
                    "start": start_dt,
                    "end": end_dt,
                }
            )

    # 1. Fetch Intake Tasks, Applications, and Application Events
    oldest_start = periods[-1]["start"]
    latest_end = periods[0]["end"]

    intake_dates = []
    app_rows = []
    event_rows = []

    try:
        intake_query = select(IntakeEvaluationTaskModel.created_at).where(
            and_(
                IntakeEvaluationTaskModel.created_at >= oldest_start,
                IntakeEvaluationTaskModel.created_at <= latest_end,
                IntakeEvaluationTaskModel.task_type != "CV_EXTRACTION",
            )
        )
        intake_res = await db.execute(intake_query)
        intake_dates = intake_res.scalars().all()

        app_query = select(
            ApplicationModel.id,
            ApplicationModel.application_date,
            ApplicationModel.created_at,
            ApplicationModel.status,
        ).where(
            and_(
                ApplicationModel.created_at >= oldest_start,
                ApplicationModel.created_at <= latest_end,
            )
        )
        app_res = await db.execute(app_query)
        app_rows = app_res.all()

        event_query = select(
            ApplicationEventModel.email_application_id,
            ApplicationEventModel.email_event_type,
            ApplicationEventModel.email_status_after_event,
            ApplicationEventModel.email_received_at,
            ApplicationEventModel.created_at,
        ).where(
            and_(
                ApplicationEventModel.created_at >= oldest_start,
                ApplicationEventModel.created_at <= latest_end,
            )
        )
        event_res = await db.execute(event_query)
        event_rows = event_res.all()
    except Exception as exc:
        logger.warning(f"Error querying database for funnel metrics: {exc}")

    # Aggregate counts by period key
    cohort_data = []

    for p in periods:
        p_start = p["start"]
        p_end = p["end"]

        # Intakes count
        intakes_cnt = sum(1 for d in intake_dates if d and p_start <= d <= p_end)

        # Applications count
        apps_cnt = sum(
            1
            for row in app_rows
            if (row.application_date or row.created_at)
            and p_start <= (row.application_date or row.created_at) <= p_end
        )

        # Interviews count (Apps created or transitioned to Interview stage during this period)
        interviews_apps = set()
        for row in app_rows:
            st = (row.status or "").upper()
            dt = row.application_date or row.created_at
            if ("INTERVIEW" in st or st == "TECHNICAL_INTERVIEW") and (
                dt and p_start <= dt <= p_end
            ):
                interviews_apps.add(row.id)

        for evt in event_rows:
            evt_dt = evt.email_received_at or evt.created_at
            if evt_dt and p_start <= evt_dt <= p_end:
                st = (evt.email_status_after_event or "").upper()
                et = (evt.email_event_type or "").upper()
                if (
                    "INTERVIEW" in st
                    or st == "TECHNICAL_INTERVIEW"
                    or "INTERVIEW" in et
                ):
                    interviews_apps.add(evt.email_application_id)

        interviews_cnt = len(interviews_apps)

        # Offers count (Apps created or transitioned to Offer stage during this period)
        offers_apps = set()
        for row in app_rows:
            st = (row.status or "").upper()
            dt = row.application_date or row.created_at
            if st in ["OFFER", "HIRED"] and (dt and p_start <= dt <= p_end):
                offers_apps.add(row.id)

        for evt in event_rows:
            evt_dt = evt.email_received_at or evt.created_at
            if evt_dt and p_start <= evt_dt <= p_end:
                st = (evt.email_status_after_event or "").upper()
                et = (evt.email_event_type or "").upper()
                if st in ["OFFER", "HIRED"] or "OFFER" in et:
                    offers_apps.add(evt.email_application_id)

        offers_cnt = len(offers_apps)

        conv_rate = round(
            (interviews_cnt / apps_cnt * 100.0) if apps_cnt > 0 else 0.0, 1
        )

        stages = [
            FunnelChartStage(stage="Intake", count=intakes_cnt),
            FunnelChartStage(stage="Applications", count=apps_cnt),
            FunnelChartStage(stage="Interviews", count=interviews_cnt),
            FunnelChartStage(stage="Offers", count=offers_cnt),
        ]

        cohort = FunnelCohortPeriod(
            period_key=p["key"],
            period_label=p["label"],
            start_date=p_start.strftime("%Y-%m-%d"),
            end_date=p_end.strftime("%Y-%m-%d"),
            intakes=intakes_cnt,
            applications=apps_cnt,
            interviews=interviews_cnt,
            offers=offers_cnt,
            conversion_rate=conv_rate,
            stages=stages,
        )
        cohort_data.append(cohort)

    # Current period (index 0) and previous period (index 1 if exists)
    curr = cohort_data[0]
    prev = cohort_data[1] if len(cohort_data) > 1 else None

    def calc_trend(curr_val: float, prev_val: float | None) -> float | None:
        if prev_val is None or prev_val == 0:
            return 100.0 if curr_val > 0 else 0.0
        return round(((curr_val - prev_val) / prev_val) * 100.0, 1)

    intake_trend = calc_trend(curr.intakes, prev.intakes if prev else None)
    app_trend = calc_trend(curr.applications, prev.applications if prev else None)
    interview_trend = calc_trend(curr.interviews, prev.interviews if prev else None)
    offer_trend = calc_trend(curr.offers, prev.offers if prev else None)

    summary_kpis = {
        "intakes": FunnelKpiCard(
            label="Total Intake Leads",
            value=curr.intakes,
            trend_percentage=intake_trend,
            is_positive=(intake_trend >= 0 if intake_trend is not None else True),
        ),
        "applications": FunnelKpiCard(
            label="Submitted Applications",
            value=curr.applications,
            trend_percentage=app_trend,
            is_positive=(app_trend >= 0 if app_trend is not None else True),
        ),
        "interviews": FunnelKpiCard(
            label="Interview Conversions",
            value=curr.interviews,
            trend_percentage=interview_trend,
            is_positive=(interview_trend >= 0 if interview_trend is not None else True),
        ),
        "offers": FunnelKpiCard(
            label="Offers Received",
            value=curr.offers,
            trend_percentage=offer_trend,
            is_positive=(offer_trend >= 0 if offer_trend is not None else True),
        ),
    }

    # Reverse chart_data so chronological order (oldest to newest) is rendered left-to-right
    chart_data = list(reversed(cohort_data))

    funnel_resp = FunnelMetricsResponse(
        period_type=normalized_period,
        summary_kpis=summary_kpis,
        chart_data=chart_data,
        table_data=cohort_data,
    )
    if use_cache:
        _FUNNEL_CACHE[cache_key] = (current_fp, funnel_resp)
    return funnel_resp


TRACK_DEFINITIONS = [
    {"key": "backend", "label": "Backend Engineering"},
    {"key": "fullstack", "label": "Full-Stack Engineering"},
    {"key": "frontend", "label": "Frontend Engineering"},
    {"key": "data_ai", "label": "AI & Data Engineering"},
    {"key": "devops", "label": "DevOps & Cloud SRE"},
    {"key": "mobile", "label": "Mobile Engineering"},
    {"key": "security", "label": "Security Engineering"},
    {"key": "other", "label": "Other Roles"},
]


def classify_position_to_track(position: str | None) -> str:
    if not position:
        return "other"
    pos = position.lower()
    if any(
        k in pos
        for k in [
            "ai",
            "ml",
            "machine learning",
            "data",
            "analytics",
            "mlops",
            "llm",
            "vector",
        ]
    ):
        return "data_ai"
    if any(
        k in pos
        for k in ["devops", "cloud", "sre", "reliability", "kubernetes", "network"]
    ):
        return "devops"
    if any(k in pos for k in ["mobile", "ios", "android", "flutter", "react native"]):
        return "mobile"
    if any(k in pos for k in ["security", "secops", "appsec", "cyber"]):
        return "security"
    if any(
        k in pos
        for k in ["frontend", "front-end", "ui", "ux", "web client", "react", "vue"]
    ):
        return "frontend"
    if any(k in pos for k in ["full-stack", "fullstack", "full stack"]):
        return "fullstack"
    if any(
        k in pos
        for k in [
            "backend",
            "back-end",
            "server",
            "distributed",
            "microservice",
            "api",
            "systems",
            "platform",
            "infrastructure",
            "database",
            "postgres",
        ]
    ):
        return "backend"
    return "fullstack" if "engineer" in pos or "developer" in pos else "other"


async def get_role_alignment(
    db: AsyncSession,
    role_track: str | None = "all",
    days: int | None = None,
    use_cache: bool = True,
) -> RoleAlignmentResponse:
    """
    Aggregates vocabulary translations, ATS keyword shifts, bullet-point reframings,
    and missing prerequisites across evaluated job dossiers grouped by role track.
    """
    selected_track_norm = (role_track or "all").strip().lower()
    cache_key = (selected_track_norm, days)
    current_fp = (0, 0)
    if use_cache:
        current_fp = await _get_role_alignment_fingerprint(db)
        if cache_key in _ROLE_ALIGNMENT_CACHE:
            cached_fp, cached_res = _ROLE_ALIGNMENT_CACHE[cache_key]
            if cached_fp == current_fp:
                return cached_res
    # Query applications with match_analysis_payload
    query = select(ApplicationModel).where(
        ApplicationModel.match_analysis_payload.isnot(None)
    )

    if days is not None:
        cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
        query = query.where(ApplicationModel.application_date >= cutoff)

    result = await db.execute(query)
    all_apps = result.scalars().all()

    # Cluster all applications by track
    track_counts = defaultdict(int)
    for app in all_apps:
        t_key = classify_position_to_track(app.position)
        track_counts[t_key] += 1

    total_all_jobs = len(all_apps)
    detected_tracks = [
        RoleTrackCluster(key="all", label="All Tracks", job_count=total_all_jobs)
    ]
    for t_def in TRACK_DEFINITIONS:
        c_cnt = track_counts[t_def["key"]]
        if c_cnt > 0 or total_all_jobs > 0:
            detected_tracks.append(
                RoleTrackCluster(
                    key=t_def["key"], label=t_def["label"], job_count=c_cnt
                )
            )

    selected_track_norm = (role_track or "all").strip().lower()

    # Filter applications for selected track / query
    filtered_apps = []
    known_keys = {t["key"] for t in TRACK_DEFINITIONS} | {"all"}

    if selected_track_norm == "all":
        filtered_apps = all_apps
    elif selected_track_norm in known_keys:
        filtered_apps = [
            app
            for app in all_apps
            if classify_position_to_track(app.position) == selected_track_norm
        ]
    else:
        # Custom search query against position title
        filtered_apps = [
            app
            for app in all_apps
            if app.position and selected_track_norm in app.position.lower()
        ]

    total_analyzed = len(filtered_apps)

    # Helper: Text similarity consensus string calculation
    def compute_consensus_text(variants: list[str]) -> str:
        if not variants:
            return ""
        if len(variants) == 1:
            return variants[0]
        # Choose string with highest average similarity to all other variants
        best_candidate = variants[0]
        best_avg_score = -1.0
        for cand in variants:
            total_sim = 0.0
            for other in variants:
                sim = SequenceMatcher(None, cand.lower(), other.lower()).ratio()
                total_sim += sim
            avg_score = total_sim / len(variants)
            if avg_score > best_avg_score:
                best_avg_score = avg_score
                best_candidate = cand
        return best_candidate

    # Global aggregation across role track by Target CV Term / Original Bullet
    vocab_groups = defaultdict(lambda: {"count": 0, "jd_terms": [], "rationales": []})
    bullet_groups = defaultdict(lambda: {"count": 0, "rewrites": [], "reasons": []})

    for app in filtered_apps:
        payload = app.match_analysis_payload or {}
        tailoring = payload.get("tailoring_strategy") or {}

        # 1. Vocabulary Translations (Grouped by cv_term)
        vocab_list = tailoring.get("vocabulary_translation") or []
        for item in vocab_list:
            if not isinstance(item, dict):
                continue
            cv_term = str(item.get("cv_term") or "").strip()
            jd_term = str(item.get("jd_term") or "").strip()
            rationale = str(
                item.get("rationale") or item.get("replacement_guidance") or ""
            ).strip()
            if cv_term and jd_term:
                vocab_groups[cv_term]["count"] += 1
                vocab_groups[cv_term]["jd_terms"].append(jd_term)
                if rationale:
                    vocab_groups[cv_term]["rationales"].append(rationale)

        # 2. Impact / Bullet Reframing (Grouped by original_bullet)
        bullet_list = tailoring.get("impact_reframing") or []
        for item in bullet_list:
            if not isinstance(item, dict):
                continue
            orig = str(
                item.get("original_bullet") or item.get("bullet_point") or ""
            ).strip()
            sugg = str(item.get("suggested_rewrite") or "").strip()
            reason = str(item.get("reason") or "").strip()
            if orig and sugg:
                bullet_groups[orig]["count"] += 1
                bullet_groups[orig]["rewrites"].append(sugg)
                if reason:
                    bullet_groups[orig]["reasons"].append(reason)

    # Format Vocabulary Shifts (Top 10 highest-impact consensus items)
    sorted_vocab = sorted(
        vocab_groups.items(), key=lambda x: x[1]["count"], reverse=True
    )[:10]
    vocab_items = []
    for cv_t, data in sorted_vocab:
        pct = (
            round((data["count"] / total_analyzed * 100.0), 1)
            if total_analyzed > 0
            else 0.0
        )
        consensus_jd = compute_consensus_text(data["jd_terms"])
        consensus_rationale = (
            compute_consensus_text(data["rationales"])
            if data["rationales"]
            else f"Aligns candidate experience with employer ATS standard for {consensus_jd}."
        )
        vocab_items.append(
            VocabularyShiftItem(
                cv_term=cv_t,
                jd_term=consensus_jd,
                frequency_count=data["count"],
                frequency_pct=pct,
                rationale=consensus_rationale,
            )
        )

    # Format Bullet Reframes (Top 10 highest-impact consensus items)
    sorted_bullets = sorted(
        bullet_groups.items(), key=lambda x: x[1]["count"], reverse=True
    )[:10]
    bullet_items = []
    for orig_b, data in sorted_bullets:
        consensus_rewrite = compute_consensus_text(data["rewrites"])
        consensus_reason = (
            compute_consensus_text(data["reasons"])
            if data["reasons"]
            else "Quantifies impact and aligns with role requirements."
        )
        bullet_items.append(
            BulletReframeItem(
                original_bullet=orig_b,
                suggested_rewrite=consensus_rewrite,
                reason=consensus_reason,
                frequency_count=data["count"],
            )
        )

    role_alignment_resp = RoleAlignmentResponse(
        detected_tracks=detected_tracks,
        selected_track=selected_track_norm,
        total_analyzed_jobs=total_analyzed,
        vocabulary_shifts=vocab_items,
        bullet_reframes=bullet_items,
    )
    if use_cache:
        _ROLE_ALIGNMENT_CACHE[cache_key] = (current_fp, role_alignment_resp)
    return role_alignment_resp
