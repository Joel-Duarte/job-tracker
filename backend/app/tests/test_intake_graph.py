from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import ApplicationModel, CompanyModel, OtherEventModel
from app.models.processed_email import ProcessedEmailModel
from app.models.staging import StagingItemModel
from app.schemas.graph_state import JobTrackerState
from app.schemas.intake import ExtractedEmailInfo
from app.services.intake_graph import intake_graph, prune_terminal_state_node


def test_prune_terminal_state_node():
    state: JobTrackerState = {
        "scraped_spec": "Large scraped webpage content...",
        "body": "Large raw email body text...",
        "subject": "Test Email",
    }
    result = prune_terminal_state_node(state)
    assert result["scraped_spec"] is None
    assert result["body"] == ""


@pytest.mark.asyncio
async def test_graph_duplicate_flow(db_session: AsyncSession):
    # Seed an existing ProcessedEmailModel record to trigger duplicate detection
    processed = ProcessedEmailModel(
        message_id="msg-dup-101",
        subject="Duplicate Subject",
        status="ingested",
    )
    db_session.add(processed)
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
        ),
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


@pytest.mark.asyncio
async def test_graph_recruiter_outreach_staging_flow(db_session: AsyncSession):
    """Recruiter outreach for a new company should route to Staging Queue for review."""
    # Seed an unrelated company
    comp = CompanyModel(name="Google", name_normalized="google")
    db_session.add(comp)
    await db_session.commit()

    state_input: JobTrackerState = {
        "message_id": "msg-recruiter-anthropic-1",
        "conversation_id": "conv-recruiter-anthropic-1",
        "subject": "Exciting Infrastructure Role at Anthropic",
        "body": "Hi, I came across your profile and thought you'd be a great fit for our Systems team at Anthropic.",
    }

    extracted = ExtractedEmailInfo(
        company="Anthropic",
        position="Senior Systems Engineer",
        email_type="RECRUITER_OUTREACH",
        event_type="RECRUITER_CONTACTED",
        status="RECRUITER_CONTACT",
        summary="Recruiter reached out regarding Systems role.",
        action_required=True,
        action="Reply to recruiter with CV.",
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
    assert staged.extracted_data.get("company") == "Anthropic"
    assert staged.extracted_data.get("position") == "Senior Systems Engineer"


@pytest.mark.asyncio
async def test_graph_action_item_generation(db_session: AsyncSession):
    """When an email requires action on a matched application, ActionItemModel is automatically created."""
    comp = CompanyModel(name="Figma", name_normalized="figma")
    db_session.add(comp)
    await db_session.flush()

    app = ApplicationModel(
        company_id=comp.id,
        position="Full Stack Engineer",
        position_normalized="full stack engineer",
        status="APPLIED",
    )
    db_session.add(app)
    await db_session.commit()

    state_input: JobTrackerState = {
        "message_id": "msg-figma-oa-1",
        "conversation_id": "conv-figma-oa-1",
        "subject": "Figma: Coding Assessment Invitation",
        "body": "Please complete the CodeSignal assessment by Friday.",
    }

    extracted = ExtractedEmailInfo(
        company="Figma",
        position="Full Stack Engineer",
        email_type="JOB_APPLICATION",
        event_type="ASSESSMENT_REQUESTED",
        status="ONLINE_ASSESSMENT",
        summary="CodeSignal assessment invitation.",
        action_required=True,
        action="Complete CodeSignal assessment by Friday 5 PM",
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

        assert result.get("application_id") == app.id

    from app.models.applications import ActionItemModel

    action_res = await db_session.execute(
        select(ActionItemModel).where(ActionItemModel.application_id == app.id)
    )
    action_items = action_res.scalars().all()
    assert len(action_items) == 1
    assert "Complete CodeSignal" in action_items[0].title
    assert action_items[0].status == "PENDING"
    assert action_items[0].urgency == "HIGH"
