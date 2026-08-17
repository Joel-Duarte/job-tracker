import datetime
from collections import defaultdict

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.models.candidate_profile import CandidateCVModel
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    FunnelStageItem,
    SkillDemandItem,
    SkillGapItem,
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
