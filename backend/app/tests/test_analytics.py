import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.services.seed_data import is_database_empty, seed_development_dataset


@pytest.fixture
def async_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_analytics_overview_empty_db(
    async_client: AsyncClient, db_session: AsyncSession
):
    assert await is_database_empty(db_session) is True

    response = await async_client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()

    assert data["total_applications"] == 0
    assert data["active_pipeline_count"] == 0
    assert data["interview_rate"] == 0.0
    assert data["offer_rate"] == 0.0
    assert data["top_in_demand_skills"] == []
    assert data["priority_skill_gaps"] == []


@pytest.mark.asyncio
async def test_analytics_overview_seeded_data(
    async_client: AsyncClient, db_session: AsyncSession
):
    await seed_development_dataset(db_session)

    response = await async_client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()

    assert data["total_applications"] > 0
    assert "active_pipeline_count" in data
    assert data["interview_rate"] >= 0.0
    assert data["offer_rate"] >= 0.0

    assert isinstance(data["top_in_demand_skills"], list)
    if len(data["top_in_demand_skills"]) > 0:
        assert "skill" in data["top_in_demand_skills"][0]
        assert "count" in data["top_in_demand_skills"][0]
        assert "percentage" in data["top_in_demand_skills"][0]
        assert "is_in_candidate_cv" in data["top_in_demand_skills"][0]

    assert isinstance(data["priority_skill_gaps"], list)
    if len(data["priority_skill_gaps"]) > 0:
        assert "skill" in data["priority_skill_gaps"][0]
        assert "priority_score" in data["priority_skill_gaps"][0]

    assert isinstance(data["pipeline_funnel"], list)
    assert len(data["pipeline_funnel"]) == 4  # Applied, Assessment, Interview, Offer

    assert "work_model_distribution" in data
    assert "salary_insights" in data


@pytest.mark.asyncio
async def test_analytics_overview_with_query_params(
    async_client: AsyncClient, db_session: AsyncSession
):
    await seed_development_dataset(db_session)

    response = await async_client.get(
        "/api/v1/analytics/overview?days=30&work_model=remote&top_n=5"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["top_in_demand_skills"]) <= 5
    assert len(data["priority_skill_gaps"]) <= 5


@pytest.mark.asyncio
async def test_activity_analytics_empty_db(
    async_client: AsyncClient, db_session: AsyncSession
):
    response = await async_client.get("/api/v1/analytics/activity?period=this_week")
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "this_week"
    assert data["applications_submitted"] == 0
    assert data["replies_received"] == 0
    assert data["interviews_scheduled"] == 0
    assert data["tasks_completed"] == 0
    assert data["terminal_outcomes"]["OFFER"] == 0
    assert isinstance(data["daily_breakdown"], list)
    assert len(data["daily_breakdown"]) == 7


@pytest.mark.asyncio
async def test_activity_history_empty_db(
    async_client: AsyncClient, db_session: AsyncSession
):
    response = await async_client.get("/api/v1/analytics/activity/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)
    assert len(data["history"]) >= 12


@pytest.mark.asyncio
async def test_activity_analytics_custom_period(
    async_client: AsyncClient, db_session: AsyncSession
):
    response = await async_client.get(
        "/api/v1/analytics/activity?period=custom&start_date=2023-01-01T00:00:00Z&end_date=2023-01-31T23:59:59Z"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "custom"
    assert len(data["daily_breakdown"]) == 31
