import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from datetime import datetime, timezone
from app.models.applications import CompanyModel, ApplicationModel, ApplicationEventModel, OtherEventModel
from app.services.intake import process_email_batch_sequential
from app.services.task_tracker import task_tracker
from app.services.email_fetcher import fetch_emails_from_account
from app.schemas.intake import EmailPayload, ExtractedEmailInfo


@pytest.mark.asyncio
async def test_process_new_job_application(db_session, mock_job_email_payload, mock_extracted_job_info):
    """Test that a new job email correctly creates a Company, Application, and Event record."""
    task_id = task_tracker.create_task(total_emails=1)

    with patch("app.services.intake.extract_email_info", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_extracted_job_info

        await process_email_batch_sequential(db_session, [mock_job_email_payload], task_id)

    # 1. Verify Company Creation
    company_res = await db_session.execute(select(CompanyModel).where(CompanyModel.name_normalized == "stripe"))
    company = company_res.scalar_one_or_none()
    assert company is not None
    assert company.name == "Stripe"

    # 2. Verify Application Creation
    app_res = await db_session.execute(select(ApplicationModel).where(ApplicationModel.company_id == company.id))
    application = app_res.scalar_one_or_none()
    assert application is not None
    assert application.position == "Senior Backend Engineer"
    assert application.status == "INTERVIEW"

    # 3. Verify Timeline Event
    event_res = await db_session.execute(
        select(ApplicationEventModel).where(ApplicationEventModel.email_application_id == application.id)
    )
    event = event_res.scalar_one_or_none()
    assert event is not None
    assert event.email_conversation_id == "msg-stripe-1001"

    # 4. Verify Task Tracker Status
    task_status = task_tracker.get_task(task_id)
    assert task_status is not None
    assert task_status["status"] == "completed"
    assert task_status["applications_updated"] == 1


@pytest.mark.asyncio
async def test_deduplication_and_update_existing_application(db_session, mock_job_email_payload, mock_extracted_job_info):
    """Test that multiple emails for the same company/position update existing records without creating duplicates."""
    task_id_1 = task_tracker.create_task(total_emails=1)
    
    # --- Step 1: Initial Email (Status: INTERVIEW) ---
    with patch("app.services.intake.extract_email_info", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_extracted_job_info
        await process_email_batch_sequential(db_session, [mock_job_email_payload], task_id_1)

    # --- Step 2: Second Email for Same Role (Status: REJECTED) ---
    second_email = EmailPayload(
        conversation_id="msg-stripe-1002",
        received_at=datetime.now(timezone.utc),
        subject="Application Status Update - Stripe",
        body="Unfortunately, we decided to proceed with another candidate.",
    )
    second_extracted = ExtractedEmailInfo(
        company="Stripe",  # Same company
        position="Senior Backend Engineer",  # Same position
        status="REJECTED",  # Updated status
        event_type="REJECTION",
        summary="Application rejected.",
        action_required=False,
        action=None,
    )

    task_id_2 = task_tracker.create_task(total_emails=1)
    with patch("app.services.intake.extract_email_info", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = second_extracted
        await process_email_batch_sequential(db_session, [second_email], task_id_2)

    # --- Verification ---
    # Total companies must still be 1
    companies = (await db_session.execute(select(CompanyModel))).scalars().all()
    assert len(companies) == 1

    # Total applications must still be 1, but status updated to REJECTED
    applications = (await db_session.execute(select(ApplicationModel))).scalars().all()
    assert len(applications) == 1
    assert applications[0].status == "REJECTED"

    # Total timeline events must be 2
    events = (await db_session.execute(select(ApplicationEventModel))).scalars().all()
    assert len(events) == 2


@pytest.mark.asyncio
async def test_process_non_job_email(db_session):
    """Test that emails without structured job/company info log to OtherEventModel."""
    newsletter_email = EmailPayload(
        conversation_id="news-123",
        received_at=datetime.now(timezone.utc),
        subject="Weekly Tech Newsletter",
        body="Here are the top stories in tech this week...",
    )
    non_job_extracted = ExtractedEmailInfo(
        company=None,
        position=None,
        email_type="NEWSLETTER",
        summary="Weekly industry updates.",
        action_required=False,
        action=None,
    )

    task_id = task_tracker.create_task(total_emails=1)
    with patch("app.services.intake.extract_email_info", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = non_job_extracted
        await process_email_batch_sequential(db_session, [newsletter_email], task_id)

    # Verify log written to OtherEventModel
    other_res = await db_session.execute(select(OtherEventModel))
    other_event = other_res.scalar_one_or_none()
    assert other_event is not None
    assert other_event.email_type == "NEWSLETTER"

    # Verify task tracker metrics
    task_status = task_tracker.get_task(task_id)
    assert task_status["other_events_logged"] == 1
    assert task_status["applications_updated"] == 0


@pytest.mark.asyncio
async def test_mock_imap_email_fetching(sample_email_account):
    """Test IMAP fetcher wrapper with mocked imaplib sync calls."""
    with patch("app.services.email_fetcher._fetch_imap_emails_sync") as mock_sync_fetch:
        mock_sync_fetch.return_value = [
            EmailPayload(
                conversation_id="mock-1",
                received_at=datetime.now(timezone.utc),
                subject="Test Subject",
                body="Test Body",
            )
        ]

        emails = await fetch_emails_from_account(sample_email_account)
        assert len(emails) == 1
        assert emails[0].subject == "Test Subject"
        mock_sync_fetch.assert_called_once()

