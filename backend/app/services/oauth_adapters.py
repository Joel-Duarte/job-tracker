import base64
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

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
        max_results: int = 500,
        query: str = "label:INBOX",
        since_date: datetime | None = None,
    ) -> tuple[list[EmailPayload], str | None]:
        """
        Fetches new or changed messages incrementally using Gmail history ID or message list.
        Paginates through messages up to max_results. Returns a tuple of (emails_list, new_history_id).
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            message_ids: list[str] = []
            new_history_id = history_id

            # 1. If history_id is provided AND no specific since_date window was selected, attempt history sync
            if history_id and not since_date:
                try:
                    hist_url = f"{cls.GMAIL_API_BASE}/history"
                    page_token = None
                    while len(message_ids) < max_results:
                        page_size = min(100, max_results - len(message_ids))
                        params = {
                            "startHistoryId": history_id,
                            "maxResults": page_size,
                            "historyTypes": "messageAdded",
                        }
                        if page_token:
                            params["pageToken"] = page_token
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
                            page_token = hist_data.get("nextPageToken")
                            if not page_token or not hist_data.get("history"):
                                break
                        else:
                            logger.warning(
                                "History ID expired or invalid (%s), falling back to query.",
                                hist_resp.status_code,
                            )
                            history_id = None
                            break
                except Exception as err:
                    logger.warning("Gmail history query error: %s", err)
                    history_id = None

            # 2. Window query or initial sync: list messages matching query with pagination
            if not history_id or since_date:
                list_url = f"{cls.GMAIL_API_BASE}/messages"
                page_token = None
                while len(message_ids) < max_results:
                    page_size = min(100, max_results - len(message_ids))
                    params = {"q": query, "maxResults": page_size}
                    if page_token:
                        params["pageToken"] = page_token
                    resp = await client.get(list_url, headers=headers, params=params)
                    resp.raise_for_status()
                    list_data = resp.json()
                    for msg_item in list_data.get("messages", []):
                        if msg_item["id"] not in message_ids:
                            message_ids.append(msg_item["id"])
                    page_token = list_data.get("nextPageToken")
                    if not page_token or not list_data.get("messages"):
                        break

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
    """OAuth2 adapter for Microsoft Graph (Outlook / Microsoft 365)."""

    TOKEN_ENDPOINT = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    SCOPES = ["Mail.Read", "offline_access", "User.Read"]

    @classmethod
    def get_authorization_url(
        cls, client_id: str, redirect_uri: str, state: str
    ) -> str:
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(cls.SCOPES),
            "state": state,
            "prompt": "select_account",
        }
        return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"

    @classmethod
    async def exchange_code_for_tokens(
        cls, client_id: str, client_secret: str, code: str, redirect_uri: str
    ) -> dict[str, Any]:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                cls.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                err_msg = resp.text
                logger.error("Microsoft code exchange failed: %s", err_msg)
                raise ValueError(f"Microsoft OAuth failed: {err_msg}")
            return resp.json()

    @classmethod
    async def refresh_access_token(
        cls, client_id: str, client_secret: str, refresh_token: str
    ) -> str:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(cls.SCOPES),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                cls.TOKEN_ENDPOINT,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                err_msg = resp.text
                logger.error("Microsoft token refresh failed: %s", err_msg)
                raise ValueError(f"Microsoft token refresh failed: {err_msg}")

            data = resp.json()
            return data["access_token"]

    @classmethod
    async def fetch_messages_delta(
        cls,
        access_token: str,
        delta_link: str | None = None,
        max_results: int = 500,
        folder_id: str = "Inbox",
        since_date: datetime | None = None,
    ) -> tuple[list[EmailPayload], str | None]:
        """
        Fetches new or changed messages incrementally using Microsoft Graph delta sync.
        Paginates through pages up to max_results. Returns a tuple of (emails_list, next_delta_link).
        """
        page_size = min(100, max_results)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Prefer": f"odata.maxpagesize={page_size}",
        }

        target = folder_id if folder_id else "Inbox"
        if since_date:
            since_iso = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            request_url = (
                f"{cls.GRAPH_BASE}/me/mailFolders/{target}/messages"
                f"?$filter=receivedDateTime ge {since_iso}&$top={page_size}&$orderby=receivedDateTime desc"
            )
        else:
            request_url = (
                delta_link or f"{cls.GRAPH_BASE}/me/mailFolders/{target}/messages/delta"
            )

        async with httpx.AsyncClient(timeout=20.0) as client:
            emails: list[EmailPayload] = []
            next_url: str | None = request_url
            next_delta: str | None = None

            while next_url and len(emails) < max_results:
                resp = await client.get(next_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("value", []):
                    if len(emails) >= max_results:
                        break
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
                    conv_id = item.get("conversationId") or f"ms-conv-{msg_id}"

                    emails.append(
                        EmailPayload(
                            conversation_id=conv_id,
                            message_id=f"msg-graph-{msg_id}",
                            received_at=received_at,
                            subject=subject,
                            body=body_content,
                        )
                    )

                next_delta = data.get("@odata.deltaLink")
                next_url = data.get("@odata.nextLink")
                if not next_url:
                    break

            return emails, next_delta or next_url
