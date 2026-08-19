from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.main import app
from app.models.ai_providers import AIProviderModel


@pytest.mark.asyncio
async def test_reset_database_protections(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Missing confirm query param -> 400
        res1 = await ac.delete(
            "/api/v1/admin/reset-database",
            headers={"X-Confirm-Reset": "true"},
        )
        assert res1.status_code == 400

        # 2. Missing confirmation header -> 400
        res2 = await ac.delete(
            "/api/v1/admin/reset-database?confirm=true",
        )
        assert res2.status_code == 400

        # 3. Production environment restriction -> 403
        with patch.object(settings, "ENVIRONMENT", "production"):
            res3 = await ac.delete(
                "/api/v1/admin/reset-database?confirm=true",
                headers={"X-Confirm-Reset": "true"},
            )
            assert res3.status_code == 403
            assert "disabled in production" in res3.json()["detail"]

        # 4. Valid confirmation header and query param in dev mode -> 200
        with patch.object(settings, "ENVIRONMENT", "development"):
            res4 = await ac.delete(
                "/api/v1/admin/reset-database?confirm=true",
                headers={"X-Confirm-Reset": "true"},
            )
            assert res4.status_code == 200
            assert res4.json()["status"] == "success"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_authorization_header(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    with patch.object(settings, "ADMIN_SECRET", "super-secret-admin-key"):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Missing token -> 401
            res_unauth = await ac.get("/api/v1/admin/staleness-stats")
            assert res_unauth.status_code == 401

            # Wrong token -> 401
            res_bad = await ac.get(
                "/api/v1/admin/staleness-stats",
                headers={"X-Admin-Token": "wrong-key"},
            )
            assert res_bad.status_code == 401

            # Correct token -> 200
            res_ok = await ac.get(
                "/api/v1/admin/staleness-stats",
                headers={"X-Admin-Token": "super-secret-admin-key"},
            )
            assert res_ok.status_code == 200

    app.dependency_overrides.clear()


def test_secret_encryption_and_masking():
    raw_key = "sk-proj-123456789abcdef"
    encrypted = encrypt_secret(raw_key)
    assert encrypted != raw_key
    assert decrypt_secret(encrypted) == raw_key

    masked = mask_secret(raw_key)
    assert masked == "sk-...cdef"

    # Legacy unencrypted fallback
    assert decrypt_secret("legacy-plain-text") == "legacy-plain-text"
    assert mask_secret("secret-12345") == "sec...345"


@pytest.mark.asyncio
async def test_ai_provider_model_encryption(db_session: AsyncSession):
    provider = AIProviderModel(
        name="Encrypted Provider",
        provider_type="openai",
        base_url="http://localhost:1234/v1",
        api_key="sk-secret-provider-key-999",
        is_active=True,
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)

    # In Python attribute access, api_key property decrypts to plain text
    assert provider.api_key == "sk-secret-provider-key-999"
    # Raw underlying column _api_key is encrypted
    assert provider._api_key != "sk-secret-provider-key-999"
