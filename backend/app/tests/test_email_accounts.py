from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.email_accounts import EmailAccountModel
from app.routers.email_accounts import generate_oauth_state, validate_oauth_state


def test_oauth_state_generation_and_validation():
    state = generate_oauth_state()
    assert state is not None
    assert len(state.split(".")) == 3

    # Valid state check
    assert validate_oauth_state(state) is True

    # Replay attack check
    assert validate_oauth_state(state) is False

    # Tampered state check
    tampered = state + "bad"
    assert validate_oauth_state(tampered) is False

    # None or empty
    assert validate_oauth_state(None) is False
    assert validate_oauth_state("") is False


@pytest.mark.asyncio
async def test_get_oauth_authorize_url_includes_state():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/email_accounts/oauth/authorize-url?provider=google"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "google"
        assert data["auth_url"] is None  # No env CLIENT_ID in test environment
        assert data["client_id_configured"] is False

        # With client_id provided
        res_with_id = await client.get(
            "/api/v1/email_accounts/oauth/authorize-url?provider=google&client_id=test-client-id"
        )
        assert res_with_id.status_code == 200
        data_id = res_with_id.json()
        assert data_id["client_id_configured"] is True
        assert "state=" in data_id["auth_url"]


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/email_accounts/oauth/callback/google?code=fake-code&state=invalid-state"
        )
        assert response.status_code == 400
        assert "Invalid or expired CSRF state" in response.text


@pytest.mark.asyncio
async def test_oauth_callback_postmessage_origin(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        state = generate_oauth_state()
        mock_tokens = {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
        }

        mock_profile_resp = httpx.Response(
            200, json={"emailAddress": "testuser@gmail.com"}
        )

        with (
            patch(
                "app.services.oauth_adapters.GmailOAuthAdapter.exchange_code_for_tokens",
                return_value=mock_tokens,
            ),
            patch(
                "app.routers.email_accounts.httpx.AsyncClient.get",
                return_value=mock_profile_resp,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                headers = {"origin": "http://localhost:5173"}
                response = await client.get(
                    f"/api/v1/email_accounts/oauth/callback/google?code=fake-code&state={state}",
                    headers=headers,
                )
                assert response.status_code == 200
                assert "http://localhost:5173" in response.text
                assert "'*'" not in response.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_email_account_credential_masking(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        # Create an account with raw credentials directly in DB
        account = EmailAccountModel(
            name="Secret Account",
            auth_type="IMAP",
            username="secret@example.com",
            app_password="super-secret-password",
            access_token="secret-access-token",
            refresh_token="secret-refresh-token",
            client_id="my-client-id",
            client_secret="secret-client-secret",
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Fetch account details via API
            response = await client.get(f"/api/v1/email_accounts/{account.id}")
            assert response.status_code == 200
            data = response.json()

            assert data["app_password"] == "********"
            assert data["access_token"] == "********"
            assert data["refresh_token"] == "********"
            assert data["client_secret"] == "********"
            assert data["client_id"] == "my-client-id"

            # 2. Update account sending back "********"
            patch_resp = await client.patch(
                f"/api/v1/email_accounts/{account.id}",
                json={"name": "Updated Secret Account", "app_password": "********"},
            )
            assert patch_resp.status_code == 200

            # Verify underlying DB model retains original password
            await db_session.refresh(account)
            assert account.app_password == "super-secret-password"
            assert account.name == "Updated Secret Account"
    finally:
        app.dependency_overrides.clear()
