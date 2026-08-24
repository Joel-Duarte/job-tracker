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
from app.routers.ai_config import check_ai_provider_health, invalidate_ai_health_cache


@pytest.fixture(autouse=True)
def reset_health_cache():
    invalidate_ai_health_cache()
    yield
    invalidate_ai_health_cache()


@pytest.mark.asyncio
async def test_check_ai_provider_health_caching_unit():
    mock_db = AsyncMock(spec=AsyncSession)

    primary = AIProviderModel(
        id=1,
        name="Unit Test LM Studio",
        provider_type="openai",
        base_url="http://127.0.0.1:1234/v1",
        is_active=True,
    )
    binding = AITaskBindingModel(
        id=1,
        task_type="GLOBAL_DEFAULT",
        provider_id=1,
        model_name="qwen2.5",
        is_active=True,
        provider=primary,
    )

    from unittest.mock import MagicMock

    mock_execute_global = MagicMock()
    mock_execute_global.scalar_one_or_none.return_value = binding

    mock_execute_fallback = MagicMock()
    mock_execute_fallback.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(
        side_effect=[mock_execute_global, mock_execute_fallback]
    )

    mock_resp = httpx.Response(200, json={"data": []})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client

    with patch("app.routers.ai_config.httpx.AsyncClient", return_value=mock_client):
        # 1. First execution: queries db & performs HTTP probe
        res1 = await check_ai_provider_health(mock_db)
        assert res1.status == "healthy"
        assert res1.provider_name == "Unit Test LM Studio"
        assert mock_db.execute.call_count == 2
        assert mock_client.get.call_count == 1

        # 2. Immediate second execution: returns cached result without db query or HTTP probe
        res2 = await check_ai_provider_health(mock_db)
        assert res2.status == "healthy"
        assert mock_db.execute.call_count == 2
        assert mock_client.get.call_count == 1

        # 3. Explicit cache invalidation
        invalidate_ai_health_cache()

        mock_execute_global_2 = MagicMock()
        mock_execute_global_2.scalar_one_or_none.return_value = binding
        mock_execute_fallback_2 = MagicMock()
        mock_execute_fallback_2.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(
            side_effect=[mock_execute_global_2, mock_execute_fallback_2]
        )

        res3 = await check_ai_provider_health(mock_db)
        assert res3.status == "healthy"
        assert mock_db.execute.call_count == 2
        assert mock_client.get.call_count == 2


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


@pytest.mark.asyncio
async def test_ai_health_cache_ttl_and_invalidation(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    primary = AIProviderModel(
        name="LM Studio Local",
        provider_type="openai",
        base_url="http://localhost:1234/v1",
        is_active=True,
    )
    db_session.add(primary)
    await db_session.commit()
    await db_session.refresh(primary)

    binding = AITaskBindingModel(
        task_type="GLOBAL_DEFAULT",
        provider_id=primary.id,
        model_name="qwen2.5",
        is_active=True,
    )
    db_session.add(binding)
    await db_session.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        mock_resp = httpx.Response(200, json={"data": []})
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__.return_value = mock_client

        with patch("app.routers.ai_config.httpx.AsyncClient", return_value=mock_client):
            # First check: triggers HTTP call
            res1 = await ac.get("/api/v1/config/ai/health")
            assert res1.status_code == 200
            assert res1.json()["status"] == "healthy"
            assert mock_client.get.call_count == 1

            # Second check immediately after: uses cache, call_count remains 1
            res2 = await ac.get("/api/v1/config/ai/health")
            assert res2.status_code == 200
            assert res2.json()["status"] == "healthy"
            assert mock_client.get.call_count == 1

        # Simulate TTL expiration by mocking time.monotonic
        with patch("app.routers.ai_config.httpx.AsyncClient", return_value=mock_client):
            with patch("time.monotonic", return_value=100000.0):
                res3 = await ac.get("/api/v1/config/ai/health")
                assert res3.status_code == 200
                assert mock_client.get.call_count == 2

        # Invalidation via provider update
        invalidate_ai_health_cache()
        with patch("app.routers.ai_config.httpx.AsyncClient", return_value=mock_client):
            res4 = await ac.get("/api/v1/config/ai/health")
            assert res4.status_code == 200
            assert mock_client.get.call_count == 3

    app.dependency_overrides.clear()
