from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config_manager import get_setting, load_settings, set_setting
from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model
from app.main import app
from app.models.ai_providers import AIProviderModel
from app.models.applications import (
    ActionItemModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.system_settings import SystemSettingsModel


@pytest.mark.asyncio
async def test_global_settings_db_backed(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Get initial global settings
        get_res = await ac.get("/api/v1/ai/global-settings")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["ENABLE_EMBEDDINGS"] is False
        assert data["AGENT_CHAT_RETENTION_DAYS"] == 7

        # 2. Patch global settings
        patch_res = await ac.patch(
            "/api/v1/ai/global-settings",
            json={"ENABLE_EMBEDDINGS": True, "AGENT_CHAT_RETENTION_DAYS": 14},
        )
        assert patch_res.status_code == 200
        patched_data = patch_res.json()
        assert patched_data["ENABLE_EMBEDDINGS"] is True
        assert patched_data["AGENT_CHAT_RETENTION_DAYS"] == 14

        # 3. Verify direct DB row update
        stmt = select(SystemSettingsModel).where(SystemSettingsModel.id == 1)
        res = await db_session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.enable_embeddings is True
        assert record.agent_chat_retention_days == 14

        # 4. Verify config_manager service methods with db_session
        loaded = await load_settings(db_session)
        assert loaded["ENABLE_EMBEDDINGS"] is True
        assert loaded["AGENT_CHAT_RETENTION_DAYS"] == 14

        val = await get_setting("ENABLE_EMBEDDINGS", default=False, db=db_session)
        assert val is True

        await set_setting("ENABLE_EMBEDDINGS", False, db=db_session)
        val_after = await get_setting("ENABLE_EMBEDDINGS", default=True, db=db_session)
        assert val_after is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_provider_crud_and_masking(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create Provider
        create_res = await ac.post(
            "/api/v1/ai/providers",
            json={
                "name": "Local LM Studio",
                "provider_type": "openai",
                "base_url": "http://192.168.1.187:1234/v1",
                "api_key": "secret-api-key-12345",
                "is_active": True,
            },
        )
        assert create_res.status_code == 201
        created = create_res.json()
        assert created["name"] == "Local LM Studio"
        assert created["api_key_masked"] == "sec...345"
        provider_id = created["id"]

        # 2. List Providers
        list_res = await ac.get("/api/v1/ai/providers")
        assert list_res.status_code == 200
        providers = list_res.json()
        assert len(providers) >= 1
        assert any(p["id"] == provider_id for p in providers)

        # 3. Patch Provider
        patch_res = await ac.patch(
            f"/api/v1/ai/providers/{provider_id}",
            json={"name": "Local LM Studio Updated"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["name"] == "Local LM Studio Updated"

        # 4. List Models for Provider (Hybrid Discovery / Curated Fallback)
        models_res = await ac.get(f"/api/v1/ai/providers/{provider_id}/models")
        assert models_res.status_code == 200
        models_data = models_res.json()
        assert models_data["provider_id"] == provider_id
        assert len(models_data["models"]) >= 1

        # 5. Direct Provider Test Probe (with mocked model)
        mock_chat = AsyncMock()
        mock_chat.ainvoke.return_value = AIMessage(content="OK")
        with patch("app.routers.ai_config.init_chat_model", return_value=mock_chat):
            probe_res = await ac.post(f"/api/v1/ai/providers/{provider_id}/test")
            assert probe_res.status_code == 200
            probe_data = probe_res.json()
            assert probe_data["status"] == "success"
            assert "OK" in probe_data["response"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_task_binding_and_execution(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    # 1. Create Provider in DB
    provider = AIProviderModel(
        name="LM Studio",
        provider_type="openai",
        base_url="http://192.168.1.187:1234/v1",
        api_key="lm-studio",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 2. Set Task Binding for EXTRACTION
        bind_res = await ac.put(
            "/api/v1/ai/bindings/EXTRACTION",
            json={
                "provider_id": provider.id,
                "model_name": "qwen3.5-4b",
                "temperature": 0.1,
                "max_tokens": 1000,
            },
        )
        assert bind_res.status_code == 200
        binding_data = bind_res.json()
        assert binding_data["task_type"] == "EXTRACTION"
        assert binding_data["model_name"] == "qwen3.5-4b"
        assert binding_data["provider_name"] == "LM Studio"

        # 3. List Task Bindings
        list_bindings = await ac.get("/api/v1/ai/bindings")
        assert list_bindings.status_code == 200
        all_bindings = list_bindings.json()
        assert len(all_bindings) >= 1

        # 4. Verify Task-Based Dynamic Model Loading
        chat_model = await get_task_chat_model(db_session, task_type="EXTRACTION")
        assert chat_model is not None

        # 5. Delete Provider Solo Guard (cannot delete only configured provider)
        del_prov = await ac.delete(f"/api/v1/ai/providers/{provider.id}")
        assert del_prov.status_code == 400

        # 6. Create fallback provider
        fb_provider = AIProviderModel(
            name="Fallback Provider",
            provider_type="openai",
            base_url="http://192.168.1.188:1234/v1",
            api_key="fb-key",
            is_active=True,
        )
        db_session.add(fb_provider)
        await db_session.commit()
        await db_session.refresh(fb_provider)

        # 7. Now delete primary provider succeeds and rebinds tasks to fallback
        del_prov_ok = await ac.delete(f"/api/v1/ai/providers/{provider.id}")
        assert del_prov_ok.status_code == 200
        assert "deleted" in del_prov_ok.json()["message"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_domain_entity_models(db_session: AsyncSession):
    # Test JobPostingModel and ActionItemModel creation & relationships
    company = CompanyModel(name="Figma", name_normalized="figma")
    db_session.add(company)
    await db_session.flush()

    app_record = ApplicationModel(
        company_id=company.id,
        position="Staff Product Designer",
        position_normalized="staff product designer",
        status="INTERVIEW",
    )
    db_session.add(app_record)
    await db_session.flush()

    job_posting = JobPostingModel(
        application_id=app_record.id,
        job_url="https://figma.com/careers/designer",
        description_markdown="# Staff Product Designer\nBuild collaborative tools.",
        salary_min=180000,
        salary_max=240000,
        location="San Francisco, CA",
        work_model="Hybrid",
        required_skills=["Figma", "Design Systems", "Prototyping"],
    )
    db_session.add(job_posting)

    action_item = ActionItemModel(
        application_id=app_record.id,
        title="Complete take-home portfolio walkthrough",
        status="PENDING",
        urgency="HIGH",
    )
    db_session.add(action_item)
    await db_session.commit()

    # Query back with selectinload
    stmt = (
        select(ApplicationModel)
        .options(
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.action_items),
        )
        .where(ApplicationModel.id == app_record.id)
    )
    res = await db_session.execute(stmt)
    loaded_app = res.scalar_one()

    assert loaded_app.job_posting is not None
    assert loaded_app.job_posting.salary_min == 180000
    assert len(loaded_app.action_items) == 1
    assert loaded_app.action_items[0].urgency == "HIGH"


@pytest.mark.asyncio
async def test_probe_model_capabilities(db_session: AsyncSession):
    from app.core.llm_factory import strip_reasoning_tags

    # Test tag stripping
    raw_with_think = "<think>Analyzing candidate experience...</think>Extracted Job Title: Senior Engineer"
    assert (
        strip_reasoning_tags(raw_with_think) == "Extracted Job Title: Senior Engineer"
    )

    # Setup test provider
    prov = AIProviderModel(
        name="Test Local Ollama",
        provider_type="ollama",
        base_url="http://localhost:11434",
        api_key=None,
        is_active=True,
    )
    db_session.add(prov)
    await db_session.commit()
    await db_session.refresh(prov)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Probe DeepSeek-R1 model
        probe_res = await ac.post(
            f"/api/v1/ai/providers/{prov.id}/probe-model",
            json={"model_name": "deepseek-r1:7b"},
        )
        assert probe_res.status_code == 200
        data = probe_res.json()
        assert data["is_reasoning_model"] is True
        assert "<think>" in data["detected_tags"]
        assert data["supports_chat_template_kwargs"] is True
        assert data["recommended_extra_body"] == {
            "chat_template_kwargs": {"thinking": False}
        }

        # Probe Standard model
        probe_std = await ac.post(
            f"/api/v1/ai/providers/{prov.id}/probe-model",
            json={"model_name": "llama3.2:3b"},
        )
        assert probe_std.status_code == 200
        std_data = probe_std.json()
        assert std_data["is_reasoning_model"] is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_task_binding_custom_extra_body(db_session: AsyncSession):
    prov = AIProviderModel(
        name="Local LM Studio",
        provider_type="openai",
        base_url="http://127.0.0.1:1234/v1",
        api_key=None,
        is_active=True,
    )
    db_session.add(prov)
    await db_session.commit()
    await db_session.refresh(prov)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create task binding with custom extra body
        bind_res = await ac.put(
            "/api/v1/ai/bindings/EMAIL_EXTRACTION",
            json={
                "provider_id": prov.id,
                "model_name": "deepseek-r1-distill-qwen-7b",
                "temperature": 0.1,
                "reasoning_effort": "custom",
                "custom_extra_body": {
                    "chat_template_kwargs": {"thinking": False},
                    "enable_thinking": False,
                },
            },
        )
        assert bind_res.status_code == 200
        bind_data = bind_res.json()
        assert bind_data["reasoning_effort"] == "custom"
        assert bind_data["custom_extra_body"] == {
            "chat_template_kwargs": {"thinking": False},
            "enable_thinking": False,
        }

        # List bindings and verify custom_extra_body is present
        list_res = await ac.get("/api/v1/ai/bindings")
        assert list_res.status_code == 200
        items = list_res.json()
        match = next((b for b in items if b["task_type"] == "EMAIL_EXTRACTION"), None)
        assert match is not None
        assert match["custom_extra_body"] == {
            "chat_template_kwargs": {"thinking": False},
            "enable_thinking": False,
        }

    app.dependency_overrides.clear()
