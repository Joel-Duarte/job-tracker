import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.applications import (
    ActionItemModel,
    ApplicationEmbeddingModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
    OtherEventModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.email_accounts import EmailAccountModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel
from app.services.seed_data import is_database_empty, seed_development_dataset


@pytest.mark.asyncio
async def test_seed_development_dataset_populates_all_entities_without_embeddings(
    db_session: AsyncSession,
):
    # 1. Verify DB is initially empty
    assert await is_database_empty(db_session) is True

    # 2. Seed development dataset
    stats = await seed_development_dataset(db_session)

    assert stats["companies"] == 5
    assert stats["applications"] == 5
    assert stats["job_postings"] == 5
    assert stats["action_items"] == 5
    assert stats["staging_items"] == 3
    assert stats["intake_tasks"] == 3
    assert stats["ai_providers"] == 1
    assert stats["ai_task_bindings"] == 5
    assert stats["email_accounts"] == 2
    assert stats["candidate_cvs"] == 1

    # 3. Database should no longer be reported as empty
    assert await is_database_empty(db_session) is False

    # 4. Verify entities are present in DB
    cvs = (
        await db_session.execute(select(func.count(CandidateCVModel.id)))
    ).scalar_one()
    assert cvs == 1

    apps = (
        await db_session.execute(select(func.count(ApplicationModel.id)))
    ).scalar_one()
    assert apps == 5

    companies = (
        await db_session.execute(select(func.count(CompanyModel.id)))
    ).scalar_one()
    assert companies == 5

    job_postings = (
        await db_session.execute(select(func.count(JobPostingModel.id)))
    ).scalar_one()
    assert job_postings == 5

    events = (
        await db_session.execute(select(func.count(ApplicationEventModel.id)))
    ).scalar_one()
    assert events == 8

    actions = (
        await db_session.execute(select(func.count(ActionItemModel.id)))
    ).scalar_one()
    assert actions == 5

    other_events = (
        await db_session.execute(select(func.count(OtherEventModel.id)))
    ).scalar_one()
    assert other_events == 3

    staging = (
        await db_session.execute(select(func.count(StagingItemModel.id)))
    ).scalar_one()
    assert staging == 3

    tasks = (
        await db_session.execute(select(func.count(IntakeEvaluationTaskModel.id)))
    ).scalar_one()
    assert tasks == 3

    providers = (
        await db_session.execute(select(func.count(AIProviderModel.id)))
    ).scalar_one()
    assert providers == 1

    bindings = (
        await db_session.execute(select(func.count(AITaskBindingModel.id)))
    ).scalar_one()
    assert bindings == 5

    accounts = (
        await db_session.execute(select(func.count(EmailAccountModel.id)))
    ).scalar_one()
    assert accounts == 2

    # 5. Crucial requirement: No embeddings generated or stored during mock seed!
    embeddings_count = (
        await db_session.execute(
            select(func.count(ApplicationEmbeddingModel.email_application_id))
        )
    ).scalar_one()
    assert embeddings_count == 0

    # 6. Verify dossier information (match_analysis_payload) on applications
    apps_list = (await db_session.execute(select(ApplicationModel))).scalars().all()
    for a in apps_list:
        assert a.match_analysis_payload is not None
        assert "fit_score" in a.match_analysis_payload
        assert "hard_matches" in a.match_analysis_payload
        assert "tailoring_strategy" in a.match_analysis_payload
        assert "pros" in a.match_analysis_payload
        assert "cons" in a.match_analysis_payload

    # 7. Verify completed intake evaluation tasks contain full dossiers
    completed_task = (
        (
            await db_session.execute(
                select(IntakeEvaluationTaskModel).where(
                    IntakeEvaluationTaskModel.status == "COMPLETED"
                )
            )
        )
        .scalars()
        .first()
    )
    assert completed_task is not None
    assert completed_task.result_json is not None
    assert "fit_score" in completed_task.result_json
    assert "tailoring_strategy" in completed_task.result_json


@pytest.mark.asyncio
async def test_admin_seed_demo_data_endpoint(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call seeds successfully
        resp = await client.post("/api/v1/admin/seed-demo-data")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "success"
        assert data["seeded_counts"]["applications"] == 5

        # Second call without force=true conflicts (409)
        conflict_resp = await client.post("/api/v1/admin/seed-demo-data")
        assert conflict_resp.status_code == 409

    app.dependency_overrides.clear()


def test_in_memory_fallback_repository():
    from app.services.fallback_store import (
        InMemoryFallbackRepository,
        get_fallback_repository,
    )

    repo = InMemoryFallbackRepository()
    stats = repo.get_stats()

    assert stats["applications"] == 5
    assert stats["companies"] == 5
    assert stats["candidate_cvs"] == 1
    assert stats["job_postings"] == 5
    assert stats["action_items"] == 5
    assert stats["staging_items"] == 2
    assert stats["intake_tasks"] == 2

    # Filtering applications
    stripe_apps = repo.get_applications(q="stripe")
    assert len(stripe_apps) == 1
    assert stripe_apps[0]["company"]["name"] == "Stripe"

    applied_apps = repo.get_applications(status_filter="APPLIED")
    assert len(applied_apps) == 1

    # App by ID
    app_1 = repo.get_application_by_id(1)
    assert app_1 is not None
    assert app_1["id"] == 1

    assert repo.get_application_by_id(999) is None

    # Getters
    assert repo.get_candidate_cv()["is_active"] is True
    assert len(repo.get_companies()) == 5
    assert len(repo.get_action_items()) == 5
    assert len(repo.get_staging_items()) == 2
    assert len(repo.get_intake_tasks()) == 2

    # Singleton accessor
    singleton_repo = get_fallback_repository()
    assert singleton_repo is not None


@pytest.mark.asyncio
async def test_health_check_fallback_mode(monkeypatch):
    import app.main as main_module
    from app.main import app

    async def mock_check_db_disconnected():
        return False

    monkeypatch.setattr(main_module, "check_db_connection", mock_check_db_disconnected)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        assert data["fallback_mode"] == "in_memory_repository"
        assert "fallback_stats" in data
        assert data["fallback_stats"]["applications"] == 5


@pytest.mark.asyncio
async def test_cli_main_entrypoint(monkeypatch):
    import sys

    from app.services.seed_data import cli_main

    async def mock_db_check():
        return True

    async def mock_ensure_schema():
        pass

    async def mock_is_empty(session):
        return True

    async def mock_seed(session):
        return {"applications": 5, "companies": 5}

    monkeypatch.setattr("app.core.database.check_db_connection", mock_db_check)
    monkeypatch.setattr("app.core.database.ensure_db_schema", mock_ensure_schema)
    monkeypatch.setattr("app.services.seed_data.is_database_empty", mock_is_empty)
    monkeypatch.setattr("app.services.seed_data.seed_development_dataset", mock_seed)

    monkeypatch.setattr(sys, "argv", ["seed_data.py", "--force"])

    # Should run without error
    await cli_main()
