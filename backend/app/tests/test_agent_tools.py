from unittest.mock import AsyncMock, patch

import pytest

from app.models.applications import (
    ActionItemModel,
    ApplicationModel,
    CompanyModel,
)
from app.services.agent_tools import (
    create_agent_tools,
    execute_get_action_items,
    execute_get_application_details,
    execute_list_applications,
    execute_update_application_status,
)


@pytest.mark.asyncio
async def test_agent_tools_execution(db_session):
    """Test individual agent tool execution for listing, details, status update, and action items."""
    # 1. Seed Company & Application
    company = CompanyModel(name="Stripe", name_normalized="Stripe")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Python Developer",
        position_normalized="senior python developer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.flush()

    action_item = ActionItemModel(
        application_id=application.id,
        title="Schedule Recruiter Chat",
        urgency="HIGH",
        status="PENDING",
    )
    db_session.add(action_item)
    await db_session.commit()

    # 2. Test List Applications Tool
    list_res = await execute_list_applications(db_session, status="APPLIED")
    assert len(list_res) >= 1
    assert any(a["company"] == "Stripe" for a in list_res)

    # 3. Test Application Details Tool
    details_res = await execute_get_application_details(db_session, "Stripe")
    assert details_res["company"] == "Stripe"
    assert details_res["position"] == "Senior Python Developer"
    assert len(details_res["action_items"]) == 1

    # 4. Test Action Items Tool
    actions_res = await execute_get_action_items(db_session, urgency="HIGH")
    assert len(actions_res) >= 1
    assert any(a["title"] == "Schedule Recruiter Chat" for a in actions_res)

    # 5. Test Update Status Tool
    with patch(
        "app.services.agent_tools.generate_and_save_application_embedding",
        new_callable=AsyncMock,
    ):
        update_res = await execute_update_application_status(
            db_session,
            company_name="Stripe",
            new_status="TECHNICAL_INTERVIEW",
            notes="Recruiter confirmed technical assessment.",
        )
        assert update_res["success"] is True
        assert update_res["new_status"] == "TECHNICAL_INTERVIEW"

        # Verify DB state
        await db_session.refresh(application)
        assert application.status == "TECHNICAL_INTERVIEW"

    # 6. Test LangChain Tool Creation
    tools = create_agent_tools(db_session)
    tool_names = [t.name for t in tools]
    assert "semantic_vector_search" in tool_names
    assert "list_applications" in tool_names
    assert "get_application_details" in tool_names
    assert "update_application_status" in tool_names
    assert "get_action_items" in tool_names
