import base64
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.models.email_accounts import EmailAccountModel
from app.services.email_fetcher import fetch_emails_from_account
from app.services.oauth_adapters import GmailOAuthAdapter, MicrosoftGraphAdapter


@pytest.mark.asyncio
async def test_gmail_oauth_adapter_incremental_sync():
    raw_email_str = (
        "From: recruiter@uber.com\n"
        "To: me@example.com\n"
        "Subject: Interview with Uber\n"
        "Date: Mon, 20 Jul 2026 10:00:00 +0000\n"
        "Message-ID: <uber-123@uber.com>\n"
        "Content-Type: text/plain\n\n"
        "Hi Joel, we would like to invite you for an interview."
    )
    raw_b64 = base64.urlsafe_b64encode(raw_email_str.encode("utf-8")).decode("utf-8")

    async def mock_handler(request: httpx.Request):
        url = str(request.url)
        if "/history" in url:
            return httpx.Response(
                200,
                json={
                    "historyId": "999888",
                    "history": [{"messagesAdded": [{"message": {"id": "msg_001"}}]}],
                },
            )
        elif "/messages/msg_001?format=raw" in url:
            return httpx.Response(
                200,
                json={"id": "msg_001", "threadId": "th_123", "raw": raw_b64},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    with patch(
        "httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)
    ):
        emails, next_history_id = await GmailOAuthAdapter.fetch_messages_delta(
            access_token="fake-gmail-token",
            history_id="111222",
        )

        assert len(emails) == 1
        assert emails[0].subject == "Interview with Uber"
        assert "invite you for an interview" in emails[0].body
        assert emails[0].conversation_id == "gmail-thread-th_123"
        assert next_history_id == "999888"


@pytest.mark.asyncio
async def test_ms_graph_adapter_delta_sync():
    async def mock_handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/delta?cursor=xyz987",
                "value": [
                    {
                        "id": "ms_msg_1001",
                        "conversationId": "ms_conv_abc",
                        "subject": "Microsoft Offer Letter",
                        "receivedDateTime": "2026-08-01T15:30:00Z",
                        "body": {
                            "contentType": "text",
                            "content": "Congratulations on your offer!",
                        },
                    },
                    {
                        "id": "ms_msg_deleted",
                        "@removed": {"reason": "deleted"},
                    },
                ],
            },
        )

    transport = httpx.MockTransport(mock_handler)
    with patch(
        "httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)
    ):
        emails, next_delta = await MicrosoftGraphAdapter.fetch_messages_delta(
            access_token="fake-ms-token",
            delta_link=None,
        )

        assert len(emails) == 1
        assert emails[0].subject == "Microsoft Offer Letter"
        assert emails[0].conversation_id == "ms_conv_abc"
        assert "Congratulations" in emails[0].body
        assert next_delta == "https://graph.microsoft.com/v1.0/delta?cursor=xyz987"


@pytest.mark.asyncio
async def test_fetch_emails_from_account_oauth_dispatch():
    gmail_account = EmailAccountModel(
        id=1,
        name="Gmail Sync",
        auth_type="GMAIL_OAUTH",
        username="user@gmail.com",
        access_token="valid-token",
        sync_cursor="12345",
    )

    with patch.object(
        GmailOAuthAdapter, "fetch_messages_delta", new_callable=AsyncMock
    ) as mock_gmail:
        mock_gmail.return_value = ([], "67890")
        emails, cursor = await fetch_emails_from_account(gmail_account)
        assert cursor == "67890"
        mock_gmail.assert_called_once()
