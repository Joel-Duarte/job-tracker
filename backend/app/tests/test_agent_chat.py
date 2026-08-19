import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from app.main import app
from app.models.applications import ApplicationModel, CompanyModel
from app.routers.agent_chat import prune_and_sanitize_tool_output
from app.services.agent_tools import create_agent_tools


def test_prune_and_sanitize_tool_output():
    """Test sanitization and pruning of tool execution outputs."""
    # 1. Test removing 'metadata' key and bounding array length
    raw_output = [
        {
            "application_id": i,
            "company": f"Company {i}",
            "metadata": {"embedding": [0.1, 0.2, 0.3], "raw": "secret"},
        }
        for i in range(10)
    ]

    sanitized = prune_and_sanitize_tool_output(raw_output, max_array_len=3)
    parsed = json.loads(sanitized)

    # Verify array length is bounded to 3
    assert len(parsed) == 3

    # Verify 'metadata' key is completely stripped
    for item in parsed:
        assert "metadata" not in item
        assert "company" in item

    # Verify compact serialization without newlines
    assert "\n" not in sanitized
    assert " " not in sanitized or ":" in sanitized


@pytest.mark.asyncio
async def test_compact_tool_output_serialization(db_session):
    """Test that create_agent_tools returns compact JSON without indents."""
    company = CompanyModel(name="TestCo", name_normalized="testco")
    db_session.add(company)
    await db_session.flush()

    app_model = ApplicationModel(
        company_id=company.id,
        position="Software Engineer",
        position_normalized="software engineer",
        status="APPLIED",
    )
    db_session.add(app_model)
    await db_session.commit()

    tools = create_agent_tools(db_session)
    list_tool = next(t for t in tools if t.name == "list_applications")

    res = await list_tool.ainvoke({"status": "APPLIED"})
    assert isinstance(res, str)
    assert "\n" not in res
    assert " " not in res or '{"' in res


@pytest.mark.asyncio
async def test_agent_chat_endpoint(db_session):
    """Test non-streaming /agent/chat endpoint."""
    mock_ai_response = AIMessage(
        content="I checked your applications. You have 1 active application."
    )

    with patch("app.routers.agent_chat.get_task_chat_model") as mock_get_model:
        mock_model = AsyncMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.ainvoke.return_value = mock_ai_response
        mock_get_model.return_value = mock_model

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.post(
                "/api/agent/chat",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": "How many active applications do I have?",
                        }
                    ]
                },
            )

        assert res.status_code == 200
        data = res.json()
        assert "chat_id" in data
        assert "I checked your applications" in data["reply"]


@pytest.mark.asyncio
async def test_agent_chat_stream_endpoint(db_session):
    """Test streaming /agent/chat/stream endpoint with SSE events."""
    mock_chunk1 = AIMessage(content="Hello! ")
    mock_chunk2 = AIMessage(content="I am processing your request.")

    async def mock_astream(*args, **kwargs):
        yield mock_chunk1
        yield mock_chunk2

    with patch("app.routers.agent_chat.get_task_chat_model") as mock_get_model:
        mock_model = AsyncMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.astream = mock_astream
        mock_get_model.return_value = mock_model

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            res = await ac.post(
                "/api/agent/chat/stream",
                json={"messages": [{"role": "user", "content": "Hello agent!"}]},
            )

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = res.text
        assert "data: " in body
        assert "token" in body
        assert "done" in body
