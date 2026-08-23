from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processed_email import ProcessedEmailModel
from app.routers.intake import SyncFolderRequest, sync_email_account
from app.schemas.intake import EmailPayload


@pytest.fixture(autouse=True)
def enable_email_intake_mock():
    with (
        patch(
            "app.core.config_manager.load_settings",
            new_callable=AsyncMock,
            return_value={"enable_email_intake": True},
        ),
        patch(
            "app.services.email_fetcher.load_settings",
            new_callable=AsyncMock,
            return_value={"enable_email_intake": True},
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_sync_email_account_processes_all_by_default(
    db_session: AsyncSession, sample_email_account
):
    """Test that sync_email_account processes all new non-duplicate emails by default without keyword filtering."""
    job_email = EmailPayload(
        message_id="msg-job-001",
        conversation_id="conv-job-001",
        received_at=datetime.now(UTC),
        subject="Your Application for Software Engineer",
        body="Thank you for applying. We are reviewing your application.",
    )
    other_email = EmailPayload(
        message_id="msg-other-002",
        conversation_id="conv-other-002",
        received_at=datetime.now(UTC),
        subject="Update from our community",
        body="Here are recent updates.",
    )

    bg_tasks = BackgroundTasks()

    with patch(
        "app.routers.intake.fetch_emails_from_account", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ([job_email, other_email], None)

        req = SyncFolderRequest(account_id=sample_email_account.id)
        res = await sync_email_account(req, bg_tasks, db_session)

        # By default, all 2 emails should be matched and queued without filtering
        assert res.scanned_count == 2
        assert res.matched_count == 2
        assert res.filtered_out_count == 0
        assert res.skipped_duplicates == 0


@pytest.mark.asyncio
async def test_sync_email_account_custom_keywords_filter(
    db_session: AsyncSession, sample_email_account
):
    """Test that when keyword_filter is provided by user, only matching emails are processed."""
    custom_email = EmailPayload(
        message_id="msg-custom-003",
        conversation_id="conv-custom-003",
        received_at=datetime.now(UTC),
        subject="Take-home coding challenge instructions",
        body="Please complete the take-home project within 48 hours.",
    )
    non_matching_email = EmailPayload(
        message_id="msg-nonmatch-004",
        conversation_id="conv-nonmatch-004",
        received_at=datetime.now(UTC),
        subject="Casual Friday reminder",
        body="Don't forget casual friday.",
    )

    bg_tasks = BackgroundTasks()

    with patch(
        "app.routers.intake.fetch_emails_from_account", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ([custom_email, non_matching_email], None)

        req = SyncFolderRequest(
            account_id=sample_email_account.id,
            keyword_filter=["take-home", "coding challenge"],
        )
        res = await sync_email_account(req, bg_tasks, db_session)

        assert res.scanned_count == 2
        assert res.matched_count == 1
        assert res.filtered_out_count == 1

    # Verify non_matching_email has been persisted as filtered_out
    stmt = select(ProcessedEmailModel).where(
        ProcessedEmailModel.message_id == "msg-nonmatch-004"
    )
    filtered_rec = (await db_session.execute(stmt)).scalar_one_or_none()
    assert filtered_rec is not None
    assert filtered_rec.status == "filtered_out"


@pytest.mark.asyncio
async def test_sync_email_account_deduplication(
    db_session: AsyncSession, sample_email_account
):
    """Test that already processed emails in ProcessedEmailModel are skipped without re-evaluating."""
    # Pre-seed a processed email
    db_session.add(
        ProcessedEmailModel(
            message_id="msg-already-seen-004",
            account_id=sample_email_account.id,
            status="ingested",
            subject="Previous interview",
        )
    )
    await db_session.commit()

    seen_email = EmailPayload(
        message_id="msg-already-seen-004",
        conversation_id="conv-seen-004",
        received_at=datetime.now(UTC),
        subject="Previous interview confirmation",
        body="Interview details.",
    )

    bg_tasks = BackgroundTasks()

    with patch(
        "app.routers.intake.fetch_emails_from_account", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ([seen_email], None)

        req = SyncFolderRequest(account_id=sample_email_account.id)
        res = await sync_email_account(req, bg_tasks, db_session)

        assert res.scanned_count == 1
        assert res.matched_count == 0
        assert res.skipped_duplicates == 1
        assert res.filtered_out_count == 0


@pytest.mark.asyncio
async def test_sync_email_account_creates_queue_task(
    db_session: AsyncSession, sample_email_account
):
    """Test that sync_email_account creates a persistent IntakeEvaluationTaskModel for AI extraction."""
    from app.models.intake_tasks import IntakeEvaluationTaskModel

    job_email = EmailPayload(
        message_id="msg-queue-005",
        conversation_id="conv-queue-005",
        received_at=datetime.now(UTC),
        subject="Interview Invitation from Figma",
        body="We would love to schedule a technical interview.",
    )

    bg_tasks = BackgroundTasks()

    with (
        patch(
            "app.routers.intake.fetch_emails_from_account", new_callable=AsyncMock
        ) as mock_fetch,
        patch("app.routers.intake.process_evaluation_task"),
    ):
        mock_fetch.return_value = ([job_email], None)

        req = SyncFolderRequest(account_id=sample_email_account.id)
        res = await sync_email_account(req, bg_tasks, db_session)

        assert res.scanned_count == 1
        assert res.matched_count == 1
        task_id = int(res.task_id)

        task = await db_session.get(IntakeEvaluationTaskModel, task_id)
        assert task is not None
        assert task.task_type == "EMAIL_SYNC"
        assert task.status == "QUEUED"
        assert task.result_json is not None
        assert task.result_json["total_emails"] == 1
        assert (
            task.result_json["emails"][0]["subject"]
            == "Interview Invitation from Figma"
        )


@pytest.mark.asyncio
async def test_execute_email_sync_steps(db_session: AsyncSession, sample_email_account):
    """Test that _execute_email_sync_steps processes emails and updates progress."""
    from app.models.intake_tasks import IntakeEvaluationTaskModel
    from app.services.evaluation_worker import _execute_email_sync_steps

    task = IntakeEvaluationTaskModel(
        task_type="EMAIL_SYNC",
        title_hint="Email Sync Test (1 email)",
        status="QUEUED",
        stage="QUEUED",
        result_json={
            "total_emails": 1,
            "processed_count": 0,
            "emails": [
                {
                    "message_id": "msg-worker-006",
                    "conversation_id": "conv-worker-006",
                    "subject": "Offer from Stripe",
                    "body": "Congratulations, we are pleased to offer you the role of Senior Engineer.",
                    "received_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    with patch(
        "app.services.intake.process_single_email_graph", new_callable=AsyncMock
    ) as mock_graph:
        mock_graph.return_value = {
            "is_application": True,
            "company_name": "Stripe",
            "position_name": "Senior Engineer",
            "application_id": 1,
            "event_id": 1,
        }

        await _execute_email_sync_steps(task, db_session)

        assert task.status == "COMPLETED"
        assert task.stage == "COMPLETE"
        assert task.result_json["processed_count"] == 1
        assert task.result_json["applications_count"] == 1
        assert task.result_json["progress_pct"] == 100
