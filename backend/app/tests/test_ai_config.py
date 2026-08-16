from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.main import app
from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model
from app.models.ai_providers import AIProviderModel
from app.models.applications import ActionItemModel, ApplicationModel, CompanyModel, JobPostingModel


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

        # 5. Delete Provider Conflict Guard
        del_prov = await ac.delete(f"/api/v1/ai/providers/{provider.id}")
        assert del_prov.status_code == 409  # Conflict because binding exists

        # 6. Delete Binding
        del_bind = await ac.delete("/api/v1/ai/bindings/EXTRACTION")
        assert del_bind.status_code == 200

        # 7. Now delete provider succeeds
        del_prov_ok = await ac.delete(f"/api/v1/ai/providers/{provider.id}")
        assert del_prov_ok.status_code == 200

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
