import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.services.analytics import clear_analytics_cache


@pytest.fixture(autouse=True)
def override_db(db_session: AsyncSession):
    clear_analytics_cache()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    clear_analytics_cache()
    app.dependency_overrides.pop(get_db, None)


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
        assert "total_analyzed_jobs" in data


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
        assert isinstance(data["detected_tracks"], list)


@pytest.mark.asyncio
async def test_recalculate_analytics_endpoint(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Pre-populate cache
        await client.get("/api/v1/analytics/overview")
        await client.get("/api/v1/analytics/funnel")
        await client.get("/api/v1/analytics/role-alignment?role_track=all")

        # Flush cache via recalculate
        res = await client.post("/api/v1/analytics/recalculate")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

        # Subsequent fetch succeeds
        res_after = await client.get("/api/v1/analytics/overview")
        assert res_after.status_code == 200


@pytest.mark.asyncio
async def test_auto_recalculate_when_db_has_more_data(db_session: AsyncSession):
    from datetime import UTC, datetime

    from app.models.applications import ApplicationModel, CompanyModel

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Initial request: total_applications = 0
        r1 = await client.get("/api/v1/analytics/overview")
        assert r1.status_code == 200
        assert r1.json()["total_applications"] == 0

        # Create a company and new application in DB
        comp = CompanyModel(name="Acme Corp", name_normalized="acme corp")
        db_session.add(comp)
        await db_session.flush()

        app1 = ApplicationModel(
            company_id=comp.id,
            position="Senior Backend Engineer",
            status="APPLIED",
            application_date=datetime.now(UTC),
            match_analysis_payload={
                "tailoring_strategy": {
                    "vocabulary_translation": [
                        {
                            "cv_term": "REST",
                            "jd_term": "gRPC",
                            "rationale": "gRPC is preferred",
                        }
                    ],
                    "impact_reframing": [],
                }
            },
        )
        db_session.add(app1)
        await db_session.commit()

        # Next query: automatically detects DB has more records, recalculates without manual flush!
        r2 = await client.get("/api/v1/analytics/overview")
        assert r2.status_code == 200
        assert r2.json()["total_applications"] == 1

        # Role alignment also automatically detects new analyzed jobs
        r_align = await client.get("/api/v1/analytics/role-alignment?role_track=all")
        assert r_align.status_code == 200
        assert r_align.json()["total_analyzed_jobs"] == 1
        assert len(r_align.json()["vocabulary_shifts"]) == 1


@pytest.mark.asyncio
async def test_role_alignment_dossier_flow(db_session: AsyncSession, monkeypatch):
    import json
    from unittest.mock import AsyncMock, MagicMock

    from app.models.candidate_profile import CandidateCVModel

    # 1. Create candidate CV
    cv = CandidateCVModel(
        raw_text="Staff Backend Engineer with 10 years experience in Python, FastAPI, and Postgres.",
        extracted_skills=["Python", "FastAPI", "PostgreSQL", "Kafka"],
        years_of_experience=10.0,
        domain_expertise=["Distributed Systems"],
        summary="Experienced Staff Backend Engineer",
    )
    db_session.add(cv)
    await db_session.commit()

    # 2. Mock LLM response for dossier synthesis
    mock_dossier_json = {
        "executive_fit": {
            "market_competitiveness_rating": "EXCEPTIONAL",
            "positioning_summary": "Top-tier distributed systems backend profile.",
            "competitive_advantages": [
                "10 years Python/FastAPI mastery",
                "Kafka streaming scale",
            ],
            "primary_vulnerabilities": ["Add Kubernetes operator examples"],
        },
        "bullet_rewrites": [
            {
                "original_bullet": "Built backend APIs.",
                "rewritten_bullet": "Engineered distributed async microservices scaling to 10M daily requests.",
                "target_competency": "High-Throughput Architecture",
                "impact_quantification": "10M daily requests",
            }
        ],
        "talking_points": [
            {
                "topic_area": "Distributed Idempotency",
                "technical_story_hook": "Resolved duplicate processing in Kafka stream.",
                "key_takeaway": "Guaranteed exactly-once consistency.",
                "sample_questions": ["How do you ensure idempotent event consumers?"],
            }
        ],
        "skill_bridge_roadmap": [
            {
                "skill_or_tool": "Kubernetes",
                "category": "Cloud Infrastructure",
                "rationale": "High market frequency for backend roles.",
                "learning_priority": "HIGH",
                "recommended_actions": ["Deploy KinD cluster with custom Helm charts."],
            }
        ],
    }

    mock_chat = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps(mock_dossier_json)
    mock_response.usage_metadata = {"input_tokens": 1200, "output_tokens": 600}
    mock_chat.ainvoke.return_value = mock_response
    mock_chat.model_name = "mock-gpt-4o"

    async def mock_get_task_chat_model(task_type, db=None, **kwargs):
        return mock_chat

    monkeypatch.setattr(
        "app.services.role_alignment_dossier_service.get_task_chat_model",
        mock_get_task_chat_model,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # GET before enhancement should return null
        res_before = await client.get(
            "/api/v1/analytics/role-alignment/dossier?role_track=backend"
        )
        assert res_before.status_code == 200
        assert res_before.json() is None

        from app.services.evaluation_worker import process_evaluation_task

        # POST /enhance enqueues background task
        res_enhance = await client.post(
            "/api/v1/analytics/role-alignment/enhance?role_track=backend"
        )
        assert res_enhance.status_code == 200
        data = res_enhance.json()
        assert data["role_track"] == "backend"
        assert data["task_type"] == "ROLE_ALIGNMENT_DOSSIER"
        assert data["status"] == "QUEUED"
        task_id = data["task_id"]

        # Run worker processing for the enqueued task
        await process_evaluation_task(task_id=task_id, db=db_session)

        # Subsequent GET retrieves persisted dossier from PostgreSQL
        res_after = await client.get(
            "/api/v1/analytics/role-alignment/dossier?role_track=backend"
        )
        assert res_after.status_code == 200
        after_data = res_after.json()
        assert after_data["role_track"] == "backend"
        assert (
            after_data["dossier"]["executive_fit"]["market_competitiveness_rating"]
            == "EXCEPTIONAL"
        )
        assert len(after_data["dossier"]["bullet_rewrites"]) == 1
        assert len(after_data["dossier"]["talking_points"]) == 1
        assert len(after_data["dossier"]["skill_bridge_roadmap"]) == 1
