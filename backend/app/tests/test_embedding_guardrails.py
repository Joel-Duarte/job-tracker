from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import set_setting
from app.core.database import get_db
from app.main import app
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.processed_email import ProcessedEmailModel
from app.models.staging import StagingItemModel
from app.services.evaluation_worker import process_evaluation_task
from app.services.llm import (
    async_enqueue_application_embedding,
    generate_and_save_application_embedding,
)


@pytest.mark.asyncio
async def test_generate_and_save_application_embedding_skips_when_disabled(
    db_session: AsyncSession,
):
    """Verify generate_and_save_application_embedding returns None and never calls embedding model when embeddings are off."""
    await set_setting("ENABLE_EMBEDDINGS", False, db=db_session)

    company = CompanyModel(name="Test Corp", name_normalized="test corp")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="AI Engineer",
        position_normalized="ai engineer",
        status="REJECTED",
    )
    db_session.add(application)
    await db_session.commit()

    with patch(
        "app.services.llm.generate_embedding",
        new_callable=AsyncMock,
    ) as mock_gen:
        res = await generate_and_save_application_embedding(db_session, application.id)
        assert res is None
        mock_gen.assert_not_called()


@pytest.mark.asyncio
async def test_async_enqueue_application_embedding_skips_when_disabled(
    db_session: AsyncSession,
):
    """Verify async_enqueue_application_embedding returns immediately without creating tasks when embeddings are off."""
    await set_setting("ENABLE_EMBEDDINGS", False, db=db_session)

    company = CompanyModel(name="Test Corp 2", name_normalized="test corp 2")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Software Engineer",
        position_normalized="software engineer",
        status="REJECTED",
    )
    db_session.add(application)
    await db_session.commit()

    with patch(
        "app.services.llm.generate_and_save_application_embedding",
        new_callable=AsyncMock,
    ) as mock_gen_save:
        await async_enqueue_application_embedding(application.id)
        mock_gen_save.assert_not_called()

        tasks_res = await db_session.execute(
            select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.task_type == "EMBEDDING"
            )
        )
        assert len(tasks_res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_staging_resolve_does_not_trigger_embeddings_when_disabled(
    db_session: AsyncSession,
):
    """Verify staging resolve endpoint does not trigger embedding generation when embeddings are disabled."""
    await set_setting("ENABLE_EMBEDDINGS", False, db=db_session)

    staged_item = StagingItemModel(
        email_conversation_id="conv-stg-guard-01",
        email_subject="Application Update: AI Engineer",
        email_received_at=datetime.now(UTC),
        email_raw_body="We regret to inform you that we will not proceed...",
        extracted_data={"company": "NN Group", "position": "AI Engineer"},
        match_score=0.40,
        match_reason="UNMATCHED_STATUS_UPDATE",
        status="PENDING",
    )
    db_session.add(staged_item)
    await db_session.commit()
    await db_session.refresh(staged_item)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/staging/{staged_item.id}/resolve",
            json={
                "company_name": "NN Group",
                "position": "AI Engineer",
                "status": "REJECTED",
                "event_type": "REJECTION_RECEIVED",
                "summary": "Candidate rejected.",
            },
        )
        assert res.status_code == 200

    tasks = (
        (await db_session.execute(select(IntakeEvaluationTaskModel))).scalars().all()
    )
    assert tasks == []


@pytest.mark.asyncio
async def test_generate_and_save_application_embedding_stays_disabled_when_enabled(
    db_session: AsyncSession,
):
    """Verify stale settings cannot re-enable embedding persistence."""
    await set_setting("ENABLE_EMBEDDINGS", True, db=db_session)

    company = CompanyModel(name="Enabled Corp", name_normalized="enabled corp")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="ML Engineer",
        position_normalized="ml engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()

    res = await generate_and_save_application_embedding(db_session, application.id)
    assert res is None


@pytest.mark.asyncio
async def test_staging_resolve_never_enqueues_ai_tasks_when_enabled(
    db_session: AsyncSession,
):
    """Resolving an email records it but never starts an AI queue task."""
    await set_setting("ENABLE_EMBEDDINGS", True, db=db_session)

    staged_item = StagingItemModel(
        email_message_id="msg-stg-guard-02",
        email_conversation_id="conv-stg-guard-02",
        email_subject="Application Update: ML Engineer",
        email_received_at=datetime.now(UTC),
        email_raw_body="Congratulations, let's interview...",
        extracted_data={"company": "Stripe", "position": "ML Engineer"},
        match_score=0.40,
        match_reason="UNMATCHED_STATUS_UPDATE",
        status="PENDING",
    )
    db_session.add(staged_item)
    db_session.add(
        ProcessedEmailModel(
            message_id="msg-stg-guard-02",
            status="staged",
            subject="Application Update: ML Engineer",
        )
    )
    await db_session.commit()
    await db_session.refresh(staged_item)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/staging/{staged_item.id}/resolve",
            json={
                "company_name": "Stripe",
                "position": "ML Engineer",
                "status": "TECHNICAL_INTERVIEW",
                "event_type": "INTERVIEW_REQUESTED",
                "summary": "Interview invite received.",
                "job_url": "https://stripe.com/careers/ml-engineer",
                "description_markdown": "Role details from the email.",
            },
        )
        assert res.status_code == 200

        event_id = res.json()["event_id"]
        processed = (
            await db_session.execute(
                select(ProcessedEmailModel).where(
                    ProcessedEmailModel.message_id == "msg-stg-guard-02"
                )
            )
        ).scalar_one()
        assert processed is not None
        assert processed.status == "ingested"

        reopened = await ac.post(f"/api/v1/staging/{staged_item.id}/reopen")
        assert reopened.status_code == 200
        assert processed.status == "staged"

        corrected = await ac.post(
            f"/api/v1/staging/{staged_item.id}/resolve",
            json={
                "company_name": "Stripe",
                "position": "ML Engineer",
                "status": "REJECTED",
                "event_type": "REJECTION",
                "summary": "Application rejected.",
            },
        )
        assert corrected.status_code == 200
        assert corrected.json()["event_id"] == event_id

    events = (await db_session.execute(select(ApplicationEventModel))).scalars().all()
    assert len(events) == 1
    assert events[0].email_event_type == "REJECTION"
    assert events[0].email_status_after_event == "REJECTED"

    tasks = (
        (await db_session.execute(select(IntakeEvaluationTaskModel))).scalars().all()
    )
    assert tasks == []


@pytest.mark.asyncio
async def test_agent_tools_transition_respects_embedding_setting(
    db_session: AsyncSession,
):
    """Verify agent_tools execute_update_application_pipeline skips embedding when disabled."""
    from app.services.agent_tools import execute_update_application_pipeline

    await set_setting("ENABLE_EMBEDDINGS", False, db=db_session)

    company = CompanyModel(name="Agent Test Co", name_normalized="agent test co")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="DevOps Engineer",
        position_normalized="devops engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.commit()

    with patch(
        "app.services.agent_tools.generate_and_save_application_embedding",
        new_callable=AsyncMock,
    ) as mock_tool_emb:
        result = await execute_update_application_pipeline(
            db=db_session,
            company_or_id=str(application.id),
            new_status="REJECTED",
            notes="Rejected via agent tool",
        )
        assert result["success"] is True
        mock_tool_emb.assert_not_called()


@pytest.mark.asyncio
async def test_worker_does_not_process_legacy_embedding_tasks(db_session: AsyncSession):
    task = IntakeEvaluationTaskModel(
        task_type="EMBEDDING",
        status="QUEUED",
        stage="QUEUED",
        result_json={"application_id": 9001},
    )
    db_session.add(task)
    await db_session.commit()

    await process_evaluation_task(task.id, db=db_session)

    await db_session.refresh(task)
    assert task.status == "QUEUED"
