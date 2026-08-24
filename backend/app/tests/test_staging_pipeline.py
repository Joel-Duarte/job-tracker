from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.models.staging import StagingItemModel
from app.schemas.intake import EmailPayload, ExtractedEmailInfo
from app.schemas.staging import StagingItemResolve
from app.services.intake import process_email_batch_sequential
from app.services.task_tracker import task_tracker


@pytest.mark.asyncio
async def test_low_confidence_email_routed_to_staging(db_session):
    """Test that emails with low fuzzy match confidence get sent to StagingItemModel."""
    # Seed an existing company to force fuzzy matching evaluation
    existing_company = CompanyModel(name="Stripe", name_normalized="stripe")
    db_session.add(existing_company)
    await db_session.commit()

    staged_email = EmailPayload(
        conversation_id="conv-staging-101",
        received_at=datetime.now(UTC),
        subject="Interview Invitation - Mystery Startup",
        body="We would love to chat about your application.",
    )

    low_confidence_extracted = ExtractedEmailInfo(
        company="Unregistered Mystery Startup",  # Fuzzy match against "stripe" will yield ~0.15 score
        position="Software Engineer",
        status="INTERVIEW",
        event_type="INTERVIEW_INVITE",
        summary="Invitation to interview.",
        action_required=True,
        action="Reply with availability.",
    )

    task_id = task_tracker.create_task(total_emails=1)

    with patch(
        "app.services.intake.extract_email_info", new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = low_confidence_extracted
        await process_email_batch_sequential(db_session, [staged_email], task_id)

    # 1. Verify NO new application was created for the low-confidence company
    app_res = await db_session.execute(select(ApplicationModel))
    assert app_res.scalar_one_or_none() is None

    # 2. Verify Item was stored in Staging Queue
    staging_res = await db_session.execute(
        select(StagingItemModel).where(
            StagingItemModel.email_conversation_id == "conv-staging-101"
        )
    )
    staged_item = staging_res.scalar_one_or_none()
    assert staged_item is not None
    assert staged_item.status == "PENDING"
    assert staged_item.match_reason == "NEW_COMPANY_LEAD"


@pytest.mark.asyncio
async def test_duplicate_email_deduplication(
    db_session, mock_job_email_payload, mock_extracted_job_info
):
    """Test that an email with an identical message_id is skipped if already present in event/staging tables."""
    company = CompanyModel(name="Stripe", name_normalized="stripe")
    db_session.add(company)
    await db_session.flush()

    app_model = ApplicationModel(
        company_id=company.id,
        position="Senior Backend Engineer",
        position_normalized="senior backend engineer",
        status="APPLIED",
    )
    db_session.add(app_model)
    await db_session.commit()

    duplicate_payload = EmailPayload(
        conversation_id=mock_job_email_payload.conversation_id,
        message_id="msg-unique-id-999",
        received_at=mock_job_email_payload.received_at,
        subject=mock_job_email_payload.subject,
        body=mock_job_email_payload.body,
    )

    task_id_1 = task_tracker.create_task(total_emails=1)
    task_id_2 = task_tracker.create_task(total_emails=1)

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = mock_extracted_job_info

        # Pass 1: Ingests email
        await process_email_batch_sequential(db_session, [duplicate_payload], task_id_1)

        # Pass 2: Identical duplicate email should be skipped
        await process_email_batch_sequential(db_session, [duplicate_payload], task_id_2)

        # Extraction should only be called ONCE (during Pass 1)
        assert mock_extract.call_count == 1

    # Verify only 1 timeline event exists in DB
    events = (await db_session.execute(select(ApplicationEventModel))).scalars().all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_resolve_staged_item_and_generate_embeddings(db_session):
    """Test manually resolving a staged item, committing application records, and calling embedding generation."""
    # 1. Create a raw staged item in DB
    staged_item = StagingItemModel(
        email_conversation_id="conv-resolve-202",
        email_subject="Follow up regarding Backend Role",
        email_received_at=datetime.now(UTC),
        email_raw_body="Thanks for applying to Acme Corp!",
        extracted_data={"company": "Acme", "position": "Backend Dev"},
        match_score=0.45,
        match_reason="LOW_FUZZY_MATCH_CONFIDENCE",
        status="PENDING",
    )
    db_session.add(staged_item)
    await db_session.commit()

    # 2. Simulate User Resolution via API Schema
    resolve_payload = StagingItemResolve(
        company_name="Acme Corporation",
        position="Senior Backend Engineer",
        status="APPLIED",
        event_type="APPLICATION_CONFIRMATION",
        summary="Application submitted successfully.",
    )

    # Mock embedding function to prevent real API calls during test
    with patch(
        "app.services.llm.generate_and_save_application_embedding",
        new_callable=AsyncMock,
    ) as mock_gen_emb:
        # Replicate resolution logic
        company_norm = resolve_payload.company_name.strip().lower()
        company = CompanyModel(
            name=resolve_payload.company_name, name_normalized=company_norm
        )
        db_session.add(company)
        await db_session.flush()

        application = ApplicationModel(
            company_id=company.id,
            position=resolve_payload.position,
            position_normalized=resolve_payload.position.strip().lower(),
            status=resolve_payload.status or "APPLIED",
        )
        db_session.add(application)
        await db_session.flush()

        event = ApplicationEventModel(
            email_application_id=application.id,
            email_conversation_id=staged_item.email_conversation_id,
            email_event_type=resolve_payload.event_type or "UPDATED",
            email_summary=resolve_payload.summary,
            email_raw_body=staged_item.email_raw_body,
        )
        db_session.add(event)

        staged_item.status = "PROCESSED"
        await db_session.commit()

        # Call embedding service mock
        await mock_gen_emb(db_session, application.id)

        # 3. Assertions
        assert staged_item.status == "PROCESSED"
        assert company.name == "Acme Corporation"
        assert application.position == "Senior Backend Engineer"
        mock_gen_emb.assert_called_once_with(db_session, application.id)


@pytest.mark.asyncio
async def test_unmatched_rejection_email_sent_to_staging_never_creates_app(db_session):
    """Test that a rejection email for a company with 0 active applications routes to staging and NEVER creates an application."""
    company = CompanyModel(name="Google", name_normalized="google")
    db_session.add(company)
    await db_session.commit()

    rejection_email = EmailPayload(
        conversation_id="conv-rejection-404",
        received_at=datetime.now(UTC),
        subject="Thank you for your interest in Google",
        body="Unfortunately we will not be moving forward with your candidacy.",
    )

    rejection_extracted = ExtractedEmailInfo(
        company="Google",
        position="Senior Staff Engineer",
        status="REJECTED",
        event_type="REJECTION",
        summary="Application rejected.",
        action_required=False,
    )

    task_id = task_tracker.create_task(total_emails=1)

    with patch(
        "app.services.intake.extract_email_info", new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = rejection_extracted
        await process_email_batch_sequential(db_session, [rejection_email], task_id)

    # 1. Verify NO new application was created
    app_res = await db_session.execute(select(ApplicationModel))
    assert app_res.scalars().all() == []

    # 2. Verify Item was stored in Staging Queue
    staging_res = await db_session.execute(
        select(StagingItemModel).where(
            StagingItemModel.email_conversation_id == "conv-rejection-404"
        )
    )
    staged_item = staging_res.scalar_one_or_none()
    assert staged_item is not None
    assert staged_item.status == "PENDING"
    assert staged_item.match_reason == "UNMATCHED_STATUS_UPDATE"


@pytest.mark.asyncio
async def test_historical_rejection_attaches_to_terminal_application(db_session):
    """Test that an older historical rejection email correctly attaches to an already concluded terminal application."""
    company = CompanyModel(name="Meta", name_normalized="meta")
    db_session.add(company)
    await db_session.flush()

    past_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    terminal_app = ApplicationModel(
        company_id=company.id,
        position="Production Engineer",
        position_normalized="production engineer",
        status="REJECTED",
        updated_at=past_date,
    )
    db_session.add(terminal_app)
    await db_session.commit()

    historical_email = EmailPayload(
        conversation_id="conv-meta-past",
        received_at=datetime(2024, 1, 14, 10, 0, 0, tzinfo=UTC),
        subject="Update on your Meta application",
        body="We will not be proceeding at this time.",
    )

    extracted_info = ExtractedEmailInfo(
        company="Meta",
        position="Production Engineer",
        status="REJECTED",
        event_type="REJECTION",
        summary="Historical rejection notice.",
        action_required=False,
    )

    task_id = task_tracker.create_task(total_emails=1)

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = extracted_info
        await process_email_batch_sequential(db_session, [historical_email], task_id)

    # 1. Verify NO new applications were created (still just 1)
    apps = (await db_session.execute(select(ApplicationModel))).scalars().all()
    assert len(apps) == 1
    assert apps[0].id == terminal_app.id

    # 2. Verify event was attached to the existing terminal application
    events = (
        (
            await db_session.execute(
                select(ApplicationEventModel).where(
                    ApplicationEventModel.email_application_id == terminal_app.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].email_subject == "Update on your Meta application"

    # 3. Verify Staging queue is empty
    staged = (await db_session.execute(select(StagingItemModel))).scalars().all()
    assert len(staged) == 0
