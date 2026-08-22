import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.email_accounts import EmailAccountModel
from app.services.email_fetcher import fetch_emails_from_account


@pytest.mark.asyncio
async def test_system_settings_get_and_patch(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. GET /api/v1/config/system
        get_res = await ac.get("/api/v1/config/system")
        assert get_res.status_code == 200
        data = get_res.json()
        assert "has_completed_onboarding" in data
        assert "enable_email_intake" in data
        assert "enable_embeddings" in data
        assert "enable_auto_cover_letter" in data

        # 2. PATCH /api/v1/config/system
        patch_res = await ac.patch(
            "/api/v1/config/system",
            json={
                "has_completed_onboarding": True,
                "enable_email_intake": True,
                "enable_embeddings": False,
            },
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["has_completed_onboarding"] is True
        assert patch_data["enable_email_intake"] is True
        assert patch_data["enable_embeddings"] is False

        # 3. Verify GET reflects updated values
        get_res_2 = await ac.get("/api/v1/config/system")
        assert get_res_2.status_code == 200
        data_2 = get_res_2.json()
        assert data_2["has_completed_onboarding"] is True
        assert data_2["enable_email_intake"] is True
        assert data_2["enable_embeddings"] is False


@pytest.mark.asyncio
async def test_global_settings_backward_compatibility(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Check GET /api/v1/ai/global-settings contains uppercase keys
        get_res = await ac.get("/api/v1/ai/global-settings")
        assert get_res.status_code == 200
        data = get_res.json()
        assert "ENABLE_EMAIL_INTAKE" in data
        assert "HAS_COMPLETED_ONBOARDING" in data
        assert "ENABLE_EMBEDDINGS" in data

        # Update via /api/v1/ai/global-settings
        patch_res = await ac.patch(
            "/api/v1/ai/global-settings",
            json={
                "ENABLE_EMAIL_INTAKE": False,
                "HAS_COMPLETED_ONBOARDING": True,
            },
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["ENABLE_EMAIL_INTAKE"] is False
        assert patch_data["HAS_COMPLETED_ONBOARDING"] is True


@pytest.mark.asyncio
async def test_email_intake_disabled_guard(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Disable email intake
        await ac.patch(
            "/api/v1/config/system",
            json={"enable_email_intake": False},
        )

        # 1. Create a dummy email account
        account = EmailAccountModel(
            name="Test Mailbox",
            username="test@example.com",
            auth_type="IMAP",
            imap_host="imap.example.com",
            app_password="password",
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        # 2. Call sync-account endpoint
        sync_res = await ac.post(
            "/api/v1/intake/sync-account",
            json={"account_id": account.id},
        )
        assert sync_res.status_code == 200
        res_data = sync_res.json()
        assert res_data.get("status") == "disabled"
        assert "turned off" in res_data.get("message", "")

        # 3. Direct fetch_emails_from_account call returns empty list without fetching
        emails, cursor = await fetch_emails_from_account(account)
        assert emails == []
        assert cursor is None
