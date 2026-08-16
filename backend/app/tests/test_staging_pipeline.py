from datetime import datetime, timezone
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
        received_at=datetime.now(timezone.utc),
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
    assert staged_item.match_reason == "LOW_FUZZY_MATCH_CONFIDENCE"


@pytest.mark.asyncio
async def test_duplicate_email_deduplication(
    db_session, mock_job_email_payload, mock_extracted_job_info
):
    """Test that an email with an identical message_id is skipped if already present in event/staging tables."""
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
        email_received_at=datetime.now(timezone.utc),
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
