from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
        assert "oauth_state=" in res_with_id.headers["set-cookie"]


@pytest.mark.asyncio
async def test_oauth_callback_requires_matching_state_cookie():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        state = generate_oauth_state()
        client.cookies.set("oauth_state", "different-token")
        response = await client.get(
            f"/api/v1/email_accounts/oauth/callback/google?code=fake-code&state={state}",
        )
        assert response.status_code == 400
        assert "Invalid or expired CSRF state" in response.text


@pytest.mark.asyncio
async def test_oauth_callback_escapes_provider_error():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        state = generate_oauth_state()
        client.cookies.set("oauth_state", state.split(".", 1)[0])
        response = await client.get(
            "/api/v1/email_accounts/oauth/callback/google"
            f"?state={state}&error=%3Cscript%3Ealert(1)%3C%2Fscript%3E",
        )
        assert response.status_code == 400
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
        assert "<script>alert(1)</script>" not in response.text


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
async def test_oauth_callback_postmessage_origin(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        monkeypatch.setattr(settings, "PUBLIC_FRONTEND_URL", "http://localhost:5173")
        state = generate_oauth_state()
        mock_tokens = {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
        }

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            return_value=httpx.Response(
                200, json={"emailAddress": "testuser@gmail.com"}
            )
        )

        with (
            patch(
                "app.services.oauth_adapters.GmailOAuthAdapter.exchange_code_for_tokens",
                return_value=mock_tokens,
            ),
            patch(
                "app.routers.email_accounts.httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                headers = {"origin": "http://localhost:5173"}
                client.cookies.set("oauth_state", state.split(".", 1)[0])
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
            assert account._app_password != "super-secret-password"
            assert account._access_token != "secret-access-token"
            assert account._refresh_token != "secret-refresh-token"
            assert account._client_secret != "secret-client-secret"

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


@pytest.mark.asyncio
async def test_clear_account_processed_emails(db_session: AsyncSession):
    """Test clearing email deduplication history and resetting sync cursor for a single account."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        from datetime import UTC, datetime

        from sqlalchemy import select

        from app.models.processed_email import ProcessedEmailModel

        acc1 = EmailAccountModel(
            name="Work Mailbox",
            username="work@example.com",
            auth_type="IMAP",
            sync_cursor="cursor-123",
            last_synced_at=datetime.now(UTC),
            is_active=True,
        )
        acc2 = EmailAccountModel(
            name="Personal Mailbox",
            username="personal@example.com",
            auth_type="IMAP",
            sync_cursor="cursor-456",
            last_synced_at=datetime.now(UTC),
            is_active=True,
        )
        db_session.add_all([acc1, acc2])
        await db_session.commit()
        await db_session.refresh(acc1)
        await db_session.refresh(acc2)

        # Seed processed emails
        pe1 = ProcessedEmailModel(
            message_id="msg-acc1-01",
            account_id=acc1.id,
            status="ingested",
            subject="Job offer",
        )
        pe2 = ProcessedEmailModel(
            message_id="msg-acc1-02",
            account_id=acc1.id,
            status="filtered_out",
            subject="Newsletter",
        )
        pe3 = ProcessedEmailModel(
            message_id="msg-acc2-01",
            account_id=acc2.id,
            status="ingested",
            subject="Interview invite",
        )
        db_session.add_all([pe1, pe2, pe3])
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            resp = await client.delete(
                f"/api/v1/email_accounts/{acc1.id}/processed-emails"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["deleted_count"] == 2

        # Check acc1 sync_cursor and last_synced_at reset
        await db_session.refresh(acc1)
        assert acc1.sync_cursor is None
        assert acc1.last_synced_at is None

        # Check acc2 remained untouched
        await db_session.refresh(acc2)
        assert acc2.sync_cursor == "cursor-456"
        assert acc2.last_synced_at is not None

        # Check ProcessedEmailModel records
        remaining = (
            (await db_session.execute(select(ProcessedEmailModel))).scalars().all()
        )
        assert len(remaining) == 1
        assert remaining[0].message_id == "msg-acc2-01"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_clear_all_processed_emails(db_session: AsyncSession):
    """Test clearing all email deduplication history and resetting sync cursors across all accounts."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        from datetime import UTC, datetime

        from sqlalchemy import select

        from app.models.processed_email import ProcessedEmailModel

        acc1 = EmailAccountModel(
            name="Mailbox A",
            username="a@example.com",
            auth_type="IMAP",
            sync_cursor="cursor-a",
            last_synced_at=datetime.now(UTC),
            is_active=True,
        )
        acc2 = EmailAccountModel(
            name="Mailbox B",
            username="b@example.com",
            auth_type="IMAP",
            sync_cursor="cursor-b",
            last_synced_at=datetime.now(UTC),
            is_active=True,
        )
        db_session.add_all([acc1, acc2])
        await db_session.commit()
        await db_session.refresh(acc1)
        await db_session.refresh(acc2)

        # Seed processed emails
        pe1 = ProcessedEmailModel(
            message_id="msg-a-01",
            account_id=acc1.id,
            status="ingested",
            subject="Job A",
        )
        pe2 = ProcessedEmailModel(
            message_id="msg-b-01",
            account_id=acc2.id,
            status="ingested",
            subject="Job B",
        )
        pe3 = ProcessedEmailModel(
            message_id="msg-unlinked-01",
            account_id=None,
            status="ingested",
            subject="Pasted text",
        )
        db_session.add_all([pe1, pe2, pe3])
        await db_session.commit()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            resp = await client.delete("/api/v1/email_accounts/processed-emails/all")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["deleted_count"] == 3

        # Check all accounts have reset cursors
        await db_session.refresh(acc1)
        assert acc1.sync_cursor is None
        assert acc1.last_synced_at is None

        await db_session.refresh(acc2)
        assert acc2.sync_cursor is None
        assert acc2.last_synced_at is None

        # Check no ProcessedEmailModel records remain
        remaining = (
            (await db_session.execute(select(ProcessedEmailModel))).scalars().all()
        )
        assert len(remaining) == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_oauth_callback_multi_channel_broadcast(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """Test that OAuth callback response broadcasts across BroadcastChannel and localStorage."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        monkeypatch.setattr(settings, "PUBLIC_FRONTEND_URL", "http://localhost:5173")
        state = generate_oauth_state()
        mock_tokens = {
            "access_token": "mock-token-xyz",
            "refresh_token": "mock-refresh-xyz",
        }

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = AsyncMock(
            return_value=httpx.Response(
                200, json={"emailAddress": "multichannel@gmail.com"}
            )
        )

        with (
            patch(
                "app.services.oauth_adapters.GmailOAuthAdapter.exchange_code_for_tokens",
                return_value=mock_tokens,
            ),
            patch(
                "app.routers.email_accounts.httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                headers = {"origin": "http://localhost:5173"}
                client.cookies.set("oauth_state", state.split(".", 1)[0])
                response = await client.get(
                    f"/api/v1/email_accounts/oauth/callback/google?code=code123&state={state}",
                    headers=headers,
                )
                assert response.status_code == 200
                html_text = response.text
                assert "BroadcastChannel('jobtracker_oauth_channel')" in html_text
                assert "jobtracker_oauth_success" in html_text
                assert "window.opener.postMessage" in html_text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_email_account_patch_preserves_unpassed_credentials(
    db_session: AsyncSession,
):
    """Test that PATCHing an account with None for secret credentials does not wipe them."""
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        acc = EmailAccountModel(
            name="OAuth Inbox",
            auth_type="GMAIL_OAUTH",
            username="oauth@example.com",
            access_token="tok_123",
            refresh_token="ref_456",
            client_id="cid_789",
            client_secret="sec_abc",
        )
        db_session.add(acc)
        await db_session.commit()
        await db_session.refresh(acc)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/email_accounts/{acc.id}",
                json={
                    "name": "Renamed OAuth Inbox",
                    "folder": "Recruitment",
                    "sync_interval": "30m",
                },
            )
            assert resp.status_code == 200

        await db_session.refresh(acc)
        assert acc.name == "Renamed OAuth Inbox"
        assert acc.folder == "Recruitment"
        assert acc.sync_interval == "30m"
        assert acc.access_token == "tok_123"
        assert acc.refresh_token == "ref_456"
        assert acc.client_secret == "sec_abc"
    finally:
        app.dependency_overrides.clear()
