import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_analytics_overview(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/analytics/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_applications" in data
        assert "pipeline_funnel" in data
        assert "top_in_demand_skills" in data


@pytest.mark.asyncio
async def test_get_funnel_metrics_weekly(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/analytics/funnel?period=weekly")
        assert response.status_code == 200
        data = response.json()
        assert data["period_type"] == "weekly"
        assert "summary_kpis" in data
        assert "intakes" in data["summary_kpis"]
        assert "applications" in data["summary_kpis"]
        assert "interviews" in data["summary_kpis"]
        assert "offers" in data["summary_kpis"]
        assert isinstance(data["chart_data"], list)
        assert isinstance(data["table_data"], list)


@pytest.mark.asyncio
async def test_get_funnel_metrics_monthly(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/analytics/funnel?period=monthly")
        assert response.status_code == 200
        data = response.json()
        assert data["period_type"] == "monthly"
        assert len(data["chart_data"]) > 0


@pytest.mark.asyncio
async def test_get_role_alignment(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/analytics/role-alignment?role_track=all")
        assert response.status_code == 200
        data = response.json()
        assert "detected_tracks" in data
        assert "selected_track" in data
        assert data["selected_track"] == "all"
        assert "vocabulary_shifts" in data
        assert "bullet_reframes" in data
        assert "missing_prerequisites" in data


@pytest.mark.asyncio
async def test_get_role_alignment_filtered_track(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/analytics/role-alignment?role_track=backend"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["selected_track"] == "backend"
        assert isinstance(data["vocabulary_shifts"], list)
        assert isinstance(data["bullet_reframes"], list)
        assert isinstance(data["missing_prerequisites"], list)
