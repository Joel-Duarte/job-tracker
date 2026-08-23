from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.llm_factory import FailoverChatModel, get_task_chat_model
from app.main import app
from app.models.ai_providers import AIProviderModel, AITaskBindingModel


@pytest.mark.asyncio
async def test_ai_health_unconfigured(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Primary endpoint
        res1 = await ac.get("/api/v1/config/ai/health")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "unconfigured"
        assert data1["provider_name"] is None

        # 2. Alias endpoint
        res2 = await ac.get("/api/v1/ai/health")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "unconfigured"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_health_healthy_and_degraded(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    # Add primary provider and GLOBAL_DEFAULT binding
    primary = AIProviderModel(
        name="Local LM Studio",
        provider_type="openai",
        base_url="http://192.168.1.187:1234/v1",
        api_key="lm-studio-key",
        is_active=True,
    )
    db_session.add(primary)
    await db_session.commit()
    await db_session.refresh(primary)

    binding = AITaskBindingModel(
        task_type="GLOBAL_DEFAULT",
        provider_id=primary.id,
        model_name="qwen3.5-9b",
        is_active=True,
    )
    db_session.add(binding)
    await db_session.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Mock httpx AsyncClient inside ai_config for fast <800ms healthy response
        mock_response = httpx.Response(200, json={"data": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__.return_value = mock_client

        with patch("app.routers.ai_config.httpx.AsyncClient", return_value=mock_client):
            res = await ac.get("/api/v1/config/ai/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert data["provider_id"] == primary.id
            assert data["provider_name"] == "Local LM Studio"
            assert data["model_name"] == "qwen3.5-9b"
            assert data["fallback_provider_id"] is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_health_offline_and_fallback_resolution(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    # 1. Primary provider
    primary = AIProviderModel(
        name="Local LM Studio",
        provider_type="openai",
        base_url="http://192.168.1.187:1234/v1",
        is_active=True,
    )
    # 2. Designated fallback provider
    fallback = AIProviderModel(
        name="OpenAI Cloud",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test-key",
        is_active=True,
        is_fallback=True,
    )
    db_session.add_all([primary, fallback])
    await db_session.commit()
    await db_session.refresh(primary)
    await db_session.refresh(fallback)

    binding = AITaskBindingModel(
        task_type="GLOBAL_DEFAULT",
        provider_id=primary.id,
        model_name="qwen3.5-9b",
        is_active=True,
    )
    db_session.add(binding)
    await db_session.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Mock httpx AsyncClient raising ConnectError
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client.__aenter__.return_value = mock_client

        with patch("app.routers.ai_config.httpx.AsyncClient", return_value=mock_client):
            res = await ac.get("/api/v1/config/ai/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "offline"
            assert data["provider_name"] == "Local LM Studio"
            assert data["fallback_provider_id"] == fallback.id
            assert data["fallback_provider_name"] == "OpenAI Cloud"
            assert "Connection refused" in data["error_message"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_automatic_failover_execution(db_session: AsyncSession):
    # Primary provider
    primary = AIProviderModel(
        name="Local LM Studio",
        provider_type="openai",
        base_url="http://192.168.1.187:1234/v1",
        is_active=True,
    )
    # Fallback provider
    fallback = AIProviderModel(
        name="OpenAI Cloud",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        is_active=True,
        is_fallback=True,
    )
    db_session.add_all([primary, fallback])
    await db_session.commit()
    await db_session.refresh(primary)
    await db_session.refresh(fallback)

    binding = AITaskBindingModel(
        task_type="GLOBAL_DEFAULT",
        provider_id=primary.id,
        model_name="qwen3.5-9b",
        is_active=True,
    )
    db_session.add(binding)
    await db_session.commit()

    # Get model wrapper
    model_wrapper = await get_task_chat_model(db_session, task_type="EXTRACTION")
    assert isinstance(model_wrapper, FailoverChatModel)
    assert model_wrapper.fallback_model is not None
    assert model_wrapper.fallback_name == "OpenAI Cloud"

    # Mock primary to fail with ConnectError and fallback to succeed
    mock_primary_model = AsyncMock()
    mock_primary_model.ainvoke.side_effect = httpx.ConnectError(
        "Connection refused on 192.168.1.187:1234"
    )

    mock_fallback_model = AsyncMock()
    mock_fallback_model.ainvoke.return_value = AIMessage(
        content="Failover success output"
    )

    model_wrapper.primary_model = mock_primary_model
    model_wrapper.fallback_model = mock_fallback_model

    result = await model_wrapper.ainvoke("Test input")
    assert result.content == "Failover success output"
    assert mock_primary_model.ainvoke.called
    assert mock_fallback_model.ainvoke.called
