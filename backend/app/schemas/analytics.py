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


class SalaryInsightItem(BaseModel):
    skill: str
    avg_min: float | None = None
    avg_max: float | None = None
    median_salary: float | None = None
    sample_count: int = 1

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
    salary_insights: list[SalaryInsightItem]

    model_config = ConfigDict(from_attributes=True)


class FunnelKpiCard(BaseModel):
    label: str
    value: int | float
    unit: str = ""
    trend_percentage: float | None = None
    is_positive: bool = True

    model_config = ConfigDict(from_attributes=True)


class FunnelChartStage(BaseModel):
    stage: str
    count: int

    model_config = ConfigDict(from_attributes=True)


class FunnelCohortPeriod(BaseModel):
    period_key: str
    period_label: str
    start_date: str
    end_date: str
    intakes: int
    applications: int
    interviews: int
    offers: int
    conversion_rate: float
    stages: list[FunnelChartStage] = []

    model_config = ConfigDict(from_attributes=True)


class FunnelMetricsResponse(BaseModel):
    period_type: str  # 'weekly' or 'monthly'
    summary_kpis: dict[str, FunnelKpiCard]
    chart_data: list[FunnelCohortPeriod]
    table_data: list[FunnelCohortPeriod]

    model_config = ConfigDict(from_attributes=True)


class VocabularyShiftItem(BaseModel):
    cv_term: str
    jd_term: str
    frequency_count: int
    frequency_pct: float
    rationale: str

    model_config = ConfigDict(from_attributes=True)


class BulletReframeItem(BaseModel):
    original_bullet: str
    suggested_rewrite: str
    reason: str
    frequency_count: int

    model_config = ConfigDict(from_attributes=True)


class RoleTrackCluster(BaseModel):
    key: str
    label: str
    job_count: int

    model_config = ConfigDict(from_attributes=True)


class RoleAlignmentResponse(BaseModel):
    detected_tracks: list[RoleTrackCluster]
    selected_track: str
    total_analyzed_jobs: int
    vocabulary_shifts: list[VocabularyShiftItem]
    bullet_reframes: list[BulletReframeItem]

    model_config = ConfigDict(from_attributes=True)
