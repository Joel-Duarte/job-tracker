from pydantic import BaseModel, ConfigDict


class SkillDemandItem(BaseModel):
    skill: str
    count: int
    percentage: float
    avg_salary_min: float | None = None
    avg_salary_max: float | None = None
    is_in_candidate_cv: bool

    model_config = ConfigDict(from_attributes=True)


class SkillGapItem(BaseModel):
    skill: str
    missing_frequency: int
    target_job_count: int
    priority_score: float
    sample_companies: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class FunnelStageItem(BaseModel):
    stage: str
    count: int
    conversion_rate: float
    dropoff_rate: float

    model_config = ConfigDict(from_attributes=True)


class WorkModelBreakdown(BaseModel):
    remote_count: int
    hybrid_count: int
    onsite_count: int
    unknown_count: int

    model_config = ConfigDict(from_attributes=True)


class AnalyticsOverviewResponse(BaseModel):
    total_applications: int
    active_pipeline_count: int
    interview_rate: float
    offer_rate: float
    average_fit_score: float | None = None
    top_in_demand_skills: list[SkillDemandItem]
    priority_skill_gaps: list[SkillGapItem]
    pipeline_funnel: list[FunnelStageItem]
    work_model_distribution: WorkModelBreakdown
    salary_insights: list[dict]

    model_config = ConfigDict(from_attributes=True)


class ActivityDailyBreakdown(BaseModel):
    date: str
    applications: int = 0
    replies: int = 0
    interviews: int = 0
    tasks: int = 0


class TerminalOutcomes(BaseModel):
    OFFER: int = 0
    HIRED: int = 0
    REJECTED: int = 0
    WITHDRAWN: int = 0


class ActivityAnalyticsResponse(BaseModel):
    period: str
    start_date: str
    end_date: str
    applications_submitted: int
    replies_received: int
    interviews_scheduled: int
    tasks_completed: int
    terminal_outcomes: TerminalOutcomes
    daily_breakdown: list[ActivityDailyBreakdown]


class ActivityHistoryBucket(BaseModel):
    week_start: str
    week_end: str
    applications: int
    replies: int
    interviews: int
    tasks: int


class ActivityHistoryResponse(BaseModel):
    history: list[ActivityHistoryBucket]
