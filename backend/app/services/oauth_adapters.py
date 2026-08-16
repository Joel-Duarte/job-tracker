import base64
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from app.schemas.intake import EmailPayload
from app.services.file_parser import parse_eml

logger = logging.getLogger(__name__)


class GmailOAuthAdapter:
    """Adapter for Google Gmail REST API with incremental history IDs."""

    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    @classmethod
    async def exchange_code_for_tokens(
        cls, client_id: str, client_secret: str, code: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Exchanges OAuth2 authorization code for access and refresh tokens."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                cls.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            return resp.json()

    @classmethod
    async def refresh_access_token(
        cls, client_id: str, client_secret: str, refresh_token: str
    ) -> str:
        """Refreshes expired OAuth2 access token with Google token endpoint."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                cls.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]

    @classmethod
    async def fetch_messages_delta(
        cls,
        access_token: str,
        history_id: str | None = None,
        max_results: int = 50,
        query: str = "label:INBOX",
    ) -> tuple[list[EmailPayload], str | None]:
        """
        Fetches new or changed messages incrementally using Gmail history ID or message list.
        Returns a tuple of (emails_list, new_history_id).
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            message_ids: list[str] = []
            new_history_id = history_id

            # 1. If history_id is provided, attempt incremental history sync
            if history_id:
                try:
                    hist_url = f"{cls.GMAIL_API_BASE}/history"
                    params = {
                        "startHistoryId": history_id,
                        "maxResults": max_results,
                        "historyTypes": "messageAdded",
                    }
                    hist_resp = await client.get(
                        hist_url, headers=headers, params=params
                    )
                    if hist_resp.status_code == 200:
                        hist_data = hist_resp.json()
                        new_history_id = hist_data.get("historyId", history_id)
                        for record in hist_data.get("history", []):
                            for msg_added in record.get("messagesAdded", []):
                                msg_id = msg_added.get("message", {}).get("id")
                                if msg_id and msg_id not in message_ids:
                                    message_ids.append(msg_id)
                    else:
                        logger.warning(
                            "History ID expired or invalid (%s), falling back to query.",
                            hist_resp.status_code,
                        )
                        history_id = None
                except Exception as err:
                    logger.warning("Gmail history query error: %s", err)
                    history_id = None

            # 2. Initial sync or fallback: list messages matching query
            if not history_id:
                list_url = f"{cls.GMAIL_API_BASE}/messages"
                params = {"q": query, "maxResults": max_results}
                resp = await client.get(list_url, headers=headers, params=params)
                resp.raise_for_status()
                list_data = resp.json()
                for msg_item in list_data.get("messages", []):
                    message_ids.append(msg_item["id"])

                # Get latest user profile historyId
                profile_resp = await client.get(
                    f"{cls.GMAIL_API_BASE}/profile", headers=headers
                )
                if profile_resp.status_code == 200:
                    new_history_id = profile_resp.json().get("historyId")

            # 3. Retrieve raw message RFC 822 contents in parallel
            emails: list[EmailPayload] = []
            for mid in message_ids:
                try:
                    msg_url = f"{cls.GMAIL_API_BASE}/messages/{mid}?format=raw"
                    raw_resp = await client.get(msg_url, headers=headers)
                    if raw_resp.status_code == 200:
                        raw_data = raw_resp.json()
                        raw_base64 = raw_data.get("raw", "")
                        raw_bytes = base64.urlsafe_b64decode(raw_base64.encode("utf-8"))
                        parsed = parse_eml(raw_bytes)
                        # Ensure conversation ID uses Google threadId if present
                        thread_id = raw_data.get("threadId")
                        if thread_id:
                            parsed.conversation_id = f"gmail-thread-{thread_id}"
                        parsed.message_id = f"gmail-{mid}"
                        emails.append(parsed)
                except Exception as err:
                    logger.error("Failed downloading Gmail message %s: %s", mid, err)

            return emails, str(new_history_id) if new_history_id else None


class MicrosoftGraphAdapter:
    """Adapter for Microsoft Graph delta sync API for Outlook / Office 365."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    @classmethod
    async def exchange_code_for_tokens(
        cls,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        tenant_id: str = "common",
    ) -> dict[str, Any]:
        """Exchanges OAuth2 authorization code for access and refresh tokens with Microsoft."""
        token_endpoint = cls.TOKEN_URL.format(tenant_id=tenant_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                token_endpoint,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "https://graph.microsoft.com/Mail.Read offline_access User.Read",
                },
            )
            resp.raise_for_status()
            return resp.json()

    @classmethod
    async def refresh_access_token(
        cls,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        tenant_id: str = "common",
    ) -> str:
        """Refreshes expired OAuth2 access token with Microsoft identity platform."""
        token_endpoint = cls.TOKEN_URL.format(tenant_id=tenant_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                token_endpoint,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": "https://graph.microsoft.com/Mail.Read offline_access",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]

    @classmethod
    async def fetch_messages_delta(
        cls,
        access_token: str,
        delta_link: str | None = None,
        max_results: int = 50,
    ) -> tuple[list[EmailPayload], str | None]:
        """
        Fetches new or changed messages incrementally using Microsoft Graph delta sync.
        Returns a tuple of (emails_list, next_delta_link).
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Prefer": f"odata.maxpagesize={max_results}",
        }

        request_url = (
            delta_link or f"{cls.GRAPH_BASE}/me/mailFolders('Inbox')/messages/delta"
        )

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(request_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            emails: list[EmailPayload] = []
            for item in data.get("value", []):
                # Skip deletion markers in delta response
                if "@removed" in item:
                    continue

                subject = item.get("subject") or "No Subject"
                body_obj = item.get("body", {})
                body_content = body_obj.get("content", "")

                received_str = item.get("receivedDateTime")
                received_at = datetime.now(UTC)
                if received_str:
                    try:
                        received_at = datetime.fromisoformat(
                            received_str.replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                msg_id = item.get("id", "")
                conv_id = item.get("conversationId") or f"ms-conv-{msg_id[:16]}"

                emails.append(
                    EmailPayload(
                        conversation_id=conv_id,
                        message_id=f"msg-graph-{msg_id[:24]}",
                        received_at=received_at,
                        subject=subject,
                        body=body_content,
                    )
                )

            next_delta = data.get("@odata.deltaLink") or data.get("@odata.nextLink")
            return emails, next_delta
