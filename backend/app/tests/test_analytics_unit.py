from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.services.analytics import (
    clear_analytics_cache,
    get_analytics_overview,
    get_funnel_performance_metrics,
)


@pytest.fixture(autouse=True)
def reset_analytics_cache():
    clear_analytics_cache()
    yield
    clear_analytics_cache()


@pytest.mark.asyncio
async def test_get_analytics_overview_unit():
    mock_db = AsyncMock()

    # CV query
    mock_cv_res = MagicMock()
    mock_cv_res.scalar_one_or_none.return_value = None

    # App query
    company = CompanyModel(id=1, name="TechCorp")

    # 5 job postings with salaries: [100k, 120k, 150k, 180k, 500k (outlier)]
    salaries = [
        (100000, 120000),
        (110000, 130000),
        (140000, 160000),
        (170000, 190000),
        (450000, 550000),
    ]
    rows = []
    for i, (s_min, s_max) in enumerate(salaries):
        app = ApplicationModel(
            id=i + 1, company_id=1, status="APPLIED", application_date=datetime.now(UTC)
        )
        jp = JobPostingModel(
            application_id=i + 1,
            work_model="Remote",
            required_skills=["python", "fastapi"],
            salary_min=s_min,
            salary_max=s_max,
        )
        rows.append((app, jp, company))

    mock_app_res = MagicMock()
    mock_app_res.all.return_value = rows

    mock_db.execute.side_effect = [mock_cv_res, mock_app_res]

    overview = await get_analytics_overview(mock_db, use_cache=False)

    assert overview.total_applications == 5
    assert len(overview.top_in_demand_skills) >= 2
    # Check normalized skill names
    skills = [s.skill for s in overview.top_in_demand_skills]
    assert "Python" in skills
    assert "FastAPI" in skills

    assert len(overview.salary_insights) >= 2
    python_insight = next(s for s in overview.salary_insights if s.skill == "Python")
    assert python_insight.sample_count == 5
    assert python_insight.median_salary is not None
    # 500k outlier should be trimmed in calculations
    assert python_insight.avg_max < 300000

    # 3-Stage Pipeline Funnel: Applied, Interview, Offer
    assert len(overview.pipeline_funnel) == 3
    stages = [f.stage for f in overview.pipeline_funnel]
    assert stages == ["Applied", "Interview", "Offer"]
    assert overview.pipeline_funnel[0].count == 5
    assert overview.pipeline_funnel[0].active_count == 5
    assert overview.pipeline_funnel[0].dropped_count == 0


@pytest.mark.asyncio
async def test_pipeline_funnel_active_and_dropped_unit():
    mock_db = AsyncMock()

    # CV query
    mock_cv_res = MagicMock()
    mock_cv_res.scalar_one_or_none.return_value = None

    company = CompanyModel(id=1, name="TechCorp")

    # 4 applications:
    # App 1: In Applied (Active)
    # App 2: In Technical Interview (Active)
    # App 3: In Offer (Active)
    # App 4: Rejected at Applied stage (Dropped)
    app1 = ApplicationModel(
        id=1, status="APPLIED", company_id=1, application_date=datetime.now(UTC)
    )
    app1.events = []
    app2 = ApplicationModel(
        id=2,
        status="TECHNICAL_INTERVIEW",
        company_id=1,
        application_date=datetime.now(UTC),
    )
    app2.events = []
    app3 = ApplicationModel(
        id=3, status="OFFER", company_id=1, application_date=datetime.now(UTC)
    )
    app3.events = []
    app4 = ApplicationModel(
        id=4, status="REJECTED", company_id=1, application_date=datetime.now(UTC)
    )
    app4.events = []

    rows = [
        (app1, None, company),
        (app2, None, company),
        (app3, None, company),
        (app4, None, company),
    ]

    mock_app_res = MagicMock()
    mock_app_res.all.return_value = rows

    mock_db.execute.side_effect = [mock_cv_res, mock_app_res]

    overview = await get_analytics_overview(mock_db, use_cache=False)

    assert overview.total_applications == 4
    assert len(overview.pipeline_funnel) == 3

    applied_stage = overview.pipeline_funnel[0]
    interview_stage = overview.pipeline_funnel[1]
    offer_stage = overview.pipeline_funnel[2]

    # Applied: all 4 reached, 1 active (app1), 1 dropped (app4)
    assert applied_stage.stage == "Applied"
    assert applied_stage.count == 4
    assert applied_stage.active_count == 1
    assert applied_stage.dropped_count == 1
    assert applied_stage.dropoff_rate == 25.0

    # Interview: 2 reached (app2, app3), 1 active (app2), 0 dropped
    assert interview_stage.stage == "Interview"
    assert interview_stage.count == 2
    assert interview_stage.active_count == 1
    assert interview_stage.dropped_count == 0
    assert interview_stage.dropoff_rate == 0.0

    # Offer: 1 reached (app3), 1 active (app3), 0 dropped
    assert offer_stage.stage == "Offer"
    assert offer_stage.count == 1
    assert offer_stage.active_count == 1
    assert offer_stage.dropped_count == 0
    assert offer_stage.dropoff_rate == 0.0


@pytest.mark.asyncio
async def test_get_funnel_performance_metrics_unit():
    mock_db = AsyncMock()

    # Create mock execution results for intake, app, and event queries
    mock_res_intake = MagicMock()
    mock_res_intake.scalars.return_value.all.return_value = []

    mock_res_apps = MagicMock()
    mock_res_apps.all.return_value = []

    mock_res_events = MagicMock()
    mock_res_events.all.return_value = []

    mock_db.execute.side_effect = [mock_res_intake, mock_res_apps, mock_res_events]

    result = await get_funnel_performance_metrics(
        mock_db, period="weekly", num_periods=4
    )
    assert result.period_type == "weekly"
    assert len(result.chart_data) == 4
    assert len(result.table_data) == 4
    assert "intakes" in result.summary_kpis
    assert result.summary_kpis["intakes"].value == 0


@pytest.mark.asyncio
async def test_get_role_alignment_unit():
    mock_db = AsyncMock()

    # CV query
    mock_cv_res = MagicMock()
    mock_cv_res.scalar_one_or_none.return_value = None

    # Application with match_analysis_payload
    payload = {
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "cv_term": "SQL database",
                    "jd_term": "PostgreSQL",
                    "replacement_guidance": "Explicitly mention PostgreSQL.",
                }
            ],
            "impact_reframing": [
                {
                    "bullet_point": "Engineered scalable services.",
                    "suggested_rewrite": "Architected microservices handling 20k req/sec.",
                    "reason": "Quantifies throughput.",
                }
            ],
        },
        "missing_skills": ["ISO 20022"],
        "optimization_gaps": {"missing_completely": ["eBPF"]},
    }

    app = ApplicationModel(
        id=1,
        company_id=1,
        position="Senior Backend Engineer",
        status="APPLIED",
        application_date=datetime.now(UTC),
        match_analysis_payload=payload,
    )

    mock_app_res = MagicMock()
    mock_app_res.scalars.return_value.all.return_value = [app]

    mock_db.execute.return_value = mock_app_res

    from app.services.analytics import get_role_alignment

    res = await get_role_alignment(mock_db, role_track="backend")

    assert res.selected_track == "backend"
    assert res.total_analyzed_jobs == 1
    assert len(res.vocabulary_shifts) == 1
    assert res.vocabulary_shifts[0].cv_term == "SQL database"
    assert res.vocabulary_shifts[0].jd_term == "PostgreSQL"
    assert len(res.bullet_reframes) == 1
    assert res.bullet_reframes[0].original_bullet == "Engineered scalable services."
