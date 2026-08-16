from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processed_email import ProcessedEmailModel
from app.routers.intake import SyncFolderRequest, sync_email_account
from app.schemas.intake import EmailPayload


@pytest.mark.asyncio
async def test_sync_email_account_keyword_prefilter(
    db_session: AsyncSession, sample_email_account
):
    """Test that sync_email_account skips non-job emails and writes filtered_out records."""
    job_email = EmailPayload(
        message_id="msg-job-001",
        conversation_id="conv-job-001",
        received_at=datetime.now(timezone.utc),
        subject="Your Application for Software Engineer",
        body="Thank you for applying. We are reviewing your application.",
    )
    spam_email = EmailPayload(
        message_id="msg-spam-002",
        conversation_id="conv-spam-002",
        received_at=datetime.now(timezone.utc),
        subject="50% off shoes today only!",
        body="Check out our summer sale on running shoes.",
    )

    bg_tasks = BackgroundTasks()

    with patch(
        "app.routers.intake.fetch_emails_from_account", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ([job_email, spam_email], None)

        req = SyncFolderRequest(account_id=sample_email_account.id)
        res = await sync_email_account(req, bg_tasks, db_session)

        assert res.scanned_count == 2
        assert res.matched_count == 1
        assert res.filtered_out_count == 1
        assert res.skipped_duplicates == 0

    # Verify spam_email has been persisted as filtered_out
    stmt = select(ProcessedEmailModel).where(
        ProcessedEmailModel.message_id == "msg-spam-002"
    )
    filtered_rec = (await db_session.execute(stmt)).scalar_one_or_none()
    assert filtered_rec is not None
    assert filtered_rec.status == "filtered_out"
    assert "50% off shoes" in (filtered_rec.subject or "")


@pytest.mark.asyncio
async def test_sync_email_account_custom_keywords(
    db_session: AsyncSession, sample_email_account
):
    """Test that custom keyword filter in SyncFolderRequest matches non-standard job terms."""
    custom_email = EmailPayload(
        message_id="msg-custom-003",
        conversation_id="conv-custom-003",
        received_at=datetime.now(timezone.utc),
        subject="Take-home coding challenge instructions",
        body="Please complete the take-home project within 48 hours.",
    )

    bg_tasks = BackgroundTasks()

    with patch(
        "app.routers.intake.fetch_emails_from_account", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ([custom_email], None)

        req = SyncFolderRequest(
            account_id=sample_email_account.id,
            keyword_filter=["take-home", "coding challenge"],
        )
        res = await sync_email_account(req, bg_tasks, db_session)

        assert res.scanned_count == 1
        assert res.matched_count == 1
        assert res.filtered_out_count == 0


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
        received_at=datetime.now(timezone.utc),
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
