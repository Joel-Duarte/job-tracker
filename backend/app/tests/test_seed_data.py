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
from app.models.diagnostics import TraceEventModel
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

    assert stats["companies"] == 25
    assert stats["applications"] == 25
    assert stats["job_postings"] == 25
    assert stats["action_items"] == 4
    assert stats["staging_items"] == 4
    assert stats["intake_tasks"] == 8
    assert stats["ai_providers"] == 1
    assert stats["ai_task_bindings"] == 7
    assert stats["email_accounts"] == 2
    assert stats["candidate_cvs"] == 1
    assert stats["trace_events"] == 3

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
    assert apps == 25

    companies = (
        await db_session.execute(select(func.count(CompanyModel.id)))
    ).scalar_one()
    assert companies == 25

    job_postings = (
        await db_session.execute(select(func.count(JobPostingModel.id)))
    ).scalar_one()
    assert job_postings == 25

    events = (
        await db_session.execute(select(func.count(ApplicationEventModel.id)))
    ).scalar_one()
    assert events == stats["application_events"]

    actions = (
        await db_session.execute(select(func.count(ActionItemModel.id)))
    ).scalar_one()
    assert actions == 4

    other_events = (
        await db_session.execute(select(func.count(OtherEventModel.id)))
    ).scalar_one()
    assert other_events == 3

    staging = (
        await db_session.execute(select(func.count(StagingItemModel.id)))
    ).scalar_one()
    assert staging == 4

    tasks = (
        await db_session.execute(select(func.count(IntakeEvaluationTaskModel.id)))
    ).scalar_one()
    assert tasks == 8

    providers = (
        await db_session.execute(select(func.count(AIProviderModel.id)))
    ).scalar_one()
    assert providers == 1

    bindings = (
        await db_session.execute(select(func.count(AITaskBindingModel.id)))
    ).scalar_one()
    assert bindings == 7

    accounts = (
        await db_session.execute(select(func.count(EmailAccountModel.id)))
    ).scalar_one()
    assert accounts == 2

    traces = (
        await db_session.execute(select(func.count(TraceEventModel.id)))
    ).scalar_one()
    assert traces == 3

    # 5. Crucial requirement: No embeddings generated or stored during mock seed!
    embeddings_count = (
        await db_session.execute(
            select(func.count(ApplicationEmbeddingModel.email_application_id))
        )
    ).scalar_one()
    assert embeddings_count == 0

    # 6. Verify dossier information and status alignment on applications
    apps_list = (await db_session.execute(select(ApplicationModel))).scalars().all()
    for a in apps_list:
        assert a.match_analysis_payload is not None
        assert "fit_score" in a.match_analysis_payload

        # High fit score for interview/offer/hired
        if a.status in ["TECHNICAL_INTERVIEW", "OFFER", "HIRED"]:
            assert a.match_analysis_payload["fit_score"] >= 80
        # Low fit score for rejected/archived/online assessment
        elif a.status in ["REJECTED", "ARCHIVED", "ONLINE_ASSESSMENT"]:
            assert a.match_analysis_payload["fit_score"] <= 55

        # Check interview guide attached for technical interview stage
        if a.status == "TECHNICAL_INTERVIEW" and a.company_id in [3, 6, 11, 18]:
            assert a.interview_guide_html is not None

        # Check cover letters attached
        if a.cover_letter_text:
            assert a.cover_letter_status == "GENERATED"

    # 7. Verify AI evaluation tasks include diverse states and error messages
    failed_tasks = (
        (
            await db_session.execute(
                select(IntakeEvaluationTaskModel).where(
                    IntakeEvaluationTaskModel.status == "FAILED"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(failed_tasks) == 3
    for ft in failed_tasks:
        assert ft.error_message is not None


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
        assert data["seeded_counts"]["applications"] == 25

        # Second call without force=true conflicts (409)
        conflict_resp = await client.post("/api/v1/admin/seed-demo-data")
        assert conflict_resp.status_code == 409

    app.dependency_overrides.clear()
