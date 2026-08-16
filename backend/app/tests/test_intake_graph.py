from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import ApplicationModel, CompanyModel, OtherEventModel
from app.models.staging import StagingItemModel
from app.schemas.graph_state import JobTrackerState
from app.schemas.intake import ExtractedEmailInfo
from app.services.intake_graph import intake_graph


@pytest.mark.asyncio
async def test_graph_duplicate_flow(db_session: AsyncSession):
    # Seed an existing event to trigger duplicate detection
    other_event = OtherEventModel(
        email_message_id="msg-dup-101",
        email_subject="Duplicate Subject",
        email_type="NEWSLETTER",
        summary="Newsletter content",
    )
    db_session.add(other_event)
    await db_session.commit()

    state_input: JobTrackerState = {
        "message_id": "msg-dup-101",
        "subject": "Duplicate Subject",
        "body": "Duplicate Body",
    }

    result = await intake_graph.ainvoke(
        state_input,
        config={"configurable": {"db": db_session}},
    )

    assert result.get("is_duplicate") is True
    assert result.get("route") == "skip"


@pytest.mark.asyncio
async def test_graph_non_application_flow(db_session: AsyncSession):
    state_input: JobTrackerState = {
        "message_id": "msg-news-102",
        "conversation_id": "conv-news-102",
        "subject": "Weekly Newsletter",
        "body": "Here is the news.",
    }

    non_job_extracted = ExtractedEmailInfo(
        company=None,
        position=None,
        email_type="NEWSLETTER",
        summary="Tech news.",
        action_required=False,
        action=None,
    )

    with patch(
        "app.services.intake.extract_email_info", new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = non_job_extracted

        result = await intake_graph.ainvoke(
            state_input,
            config={"configurable": {"db": db_session}},
        )

        assert result.get("is_application") is False
        assert result.get("event_id") is not None

    other_res = await db_session.execute(
        select(OtherEventModel).where(
            OtherEventModel.email_message_id == "msg-news-102"
        )
    )
    assert other_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_graph_high_confidence_application_flow(db_session: AsyncSession):
    state_input: JobTrackerState = {
        "message_id": "msg-job-103",
        "conversation_id": "conv-job-103",
        "subject": "Application Received: Backend Developer",
        "body": "Thank you for applying to Google as Backend Developer.",
    }

    extracted = ExtractedEmailInfo(
        company="Google",
        position="Backend Developer",
        email_type="APPLICATION_CONFIRMATION",
        event_type="APPLICATION_SUBMITTED",
        status="APPLIED",
        summary="Applied to Google.",
        action_required=False,
        action=None,
    )

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ) as mock_emb,
    ):
        mock_extract.return_value = extracted

        result = await intake_graph.ainvoke(
            state_input,
            config={"configurable": {"db": db_session}},
        )

        assert result.get("is_application") is True
        assert result.get("company_id") is not None
        assert result.get("application_id") is not None
        assert result.get("event_id") is not None

    app_res = await db_session.execute(
        select(ApplicationModel).where(ApplicationModel.id == result["application_id"])
    )
    app = app_res.scalar_one_or_none()
    assert app is not None
    assert app.position == "Backend Developer"
    assert app.status == "APPLIED"


@pytest.mark.asyncio
async def test_graph_low_confidence_staging_flow(db_session: AsyncSession):
    # Seed a company to cause a low match score against "Unknown Venture"
    comp = CompanyModel(name="Apple", name_normalized="apple")
    db_session.add(comp)
    await db_session.commit()

    state_input: JobTrackerState = {
        "message_id": "msg-stage-104",
        "conversation_id": "conv-stage-104",
        "subject": "Hello from Mystery Venture",
        "body": "Interested in interviewing.",
    }

    extracted = ExtractedEmailInfo(
        company="Mystery Venture",
        position="Data Scientist",
        email_type="INTERVIEW_INVITE",
        event_type="INTERVIEW_INVITE",
        status="INTERVIEW",
        summary="Interview invitation.",
        action_required=True,
        action="Reply with dates.",
    )

    with patch(
        "app.services.intake.extract_email_info", new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = extracted

        result = await intake_graph.ainvoke(
            state_input,
            config={"configurable": {"db": db_session}},
        )

        assert result.get("staging_item_id") is not None

    staging_res = await db_session.execute(
        select(StagingItemModel).where(StagingItemModel.id == result["staging_item_id"])
    )
    staged = staging_res.scalar_one_or_none()
    assert staged is not None
    assert staged.status == "PENDING"


@pytest.mark.asyncio
async def test_graph_single_company_auto_link(db_session: AsyncSession):
    """When exactly 1 application exists for a matched company, auto-link to it even if position is vague."""
    comp = CompanyModel(name="Stripe", name_normalized="stripe")
    db_session.add(comp)
    await db_session.flush()

    app = ApplicationModel(
        company_id=comp.id,
        position="Senior Backend Engineer",
        position_normalized="senior backend engineer",
        status="APPLIED",
    )
    db_session.add(app)
    await db_session.commit()

    state_input: JobTrackerState = {
        "message_id": "msg-stripe-201",
        "conversation_id": "conv-stripe-201",
        "subject": "Interview Invitation at Stripe",
        "body": "We would like to invite you to an interview.",
    }

    extracted = ExtractedEmailInfo(
        company="Stripe",
        position="Backend Engineering Role",
        email_type="INTERVIEW_INVITE",
        event_type="INTERVIEW_INVITE",
        status="INTERVIEW",
        summary="Invitation to interview.",
        action_required=True,
        action="Schedule interview.",
    )

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = extracted

        result = await intake_graph.ainvoke(
            state_input,
            config={"configurable": {"db": db_session}},
        )

        assert result.get("is_application") is True
        assert result.get("application_id") == app.id
        assert result.get("company_id") == comp.id


@pytest.mark.asyncio
async def test_graph_multiple_company_disambiguation(db_session: AsyncSession):
    """When multiple applications exist for a company, disambiguate by position or route to staging."""
    comp = CompanyModel(name="Uber", name_normalized="uber")
    db_session.add(comp)
    await db_session.flush()

    app1 = ApplicationModel(
        company_id=comp.id,
        position="Frontend Developer",
        position_normalized="frontend developer",
        status="APPLIED",
    )
    app2 = ApplicationModel(
        company_id=comp.id,
        position="Site Reliability Engineer",
        position_normalized="site reliability engineer",
        status="APPLIED",
    )
    db_session.add_all([app1, app2])
    await db_session.commit()

    # 1. Matching position -> links to app2
    state_sre: JobTrackerState = {
        "message_id": "msg-uber-sre",
        "conversation_id": "conv-uber-sre",
        "subject": "Update on your SRE Application at Uber",
        "body": "Next steps for Site Reliability Engineer.",
    }
    extracted_sre = ExtractedEmailInfo(
        company="Uber",
        position="Site Reliability Engineer",
        email_type="STATUS_UPDATE",
        event_type="STATUS_UPDATE",
        status="TECHNICAL_INTERVIEW",
        summary="SRE update.",
        action_required=False,
        action=None,
    )

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = extracted_sre

        result = await intake_graph.ainvoke(
            state_sre,
            config={"configurable": {"db": db_session}},
        )

        assert result.get("application_id") == app2.id

    # 2. Ambiguous/missing position -> routes to staging
    state_ambiguous: JobTrackerState = {
        "message_id": "msg-uber-ambig",
        "conversation_id": "conv-uber-ambig",
        "subject": "Important update regarding your application",
        "body": "Please contact HR.",
    }
    extracted_ambig = ExtractedEmailInfo(
        company="Uber",
        position="General Applicant",
        email_type="STATUS_UPDATE",
        event_type="STATUS_UPDATE",
        status="APPLIED",
        summary="General update.",
        action_required=False,
        action=None,
    )

    with patch(
        "app.services.intake.extract_email_info", new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = extracted_ambig

        result = await intake_graph.ainvoke(
            state_ambiguous,
            config={"configurable": {"db": db_session}},
        )

        assert result.get("staging_item_id") is not None
