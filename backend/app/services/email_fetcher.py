import asyncio
import email
import imaplib
import logging
from datetime import UTC, datetime
from email.header import decode_header

import httpx

from app.core.config_manager import load_settings
from app.core.html_utils import clean_html_text
from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailPayload
from app.services.oauth_adapters import GmailOAuthAdapter, MicrosoftGraphAdapter
from app.services.telemetry import trace_operation

logger = logging.getLogger(__name__)


def _clean_header(header_value: str) -> str:
    """Helper to decode encoded email headers (e.g. Subject)."""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for content, encoding in decoded_parts:
        if isinstance(content, bytes):
            result.append(content.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(str(content))
    return "".join(result)


def _fetch_imap_emails_sync(
    imap_host: str | None,
    imap_port: int | None,
    username: str,
    app_password: str | None,
    folder: str = "INBOX",
    account_id: int | None = None,
    since_date: datetime | None = None,
    max_results: int = 500,
) -> list[EmailPayload]:
    """Synchronous worker that performs actual IMAP connection and retrieval using scalar params."""
    if not imap_host or not app_password:
        logger.warning(
            "IMAP host or password missing for account %s (%s)", account_id, username
        )
        raise ValueError(
            f"IMAP host or app password is not configured for account {username}."
        )

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port or 993)
        mail.login(username, app_password)
        mail.select(folder or "INBOX")

        # Build search query
        if since_date:
            date_str = since_date.strftime("%d-%b-%Y")
            search_criterion = f'(SINCE "{date_str}")'
        else:
            search_criterion = "ALL"

        status, messages = mail.search(None, search_criterion)
        if status != "OK" or not messages[0]:
            return []

        email_ids = messages[0].split()
        if len(email_ids) > max_results:
            email_ids = email_ids[-max_results:]

        results = []
        batch_size = 50

        for i in range(0, len(email_ids), batch_size):
            batch_ids = email_ids[i : i + batch_size]
            fetch_ids = b",".join(batch_ids)
            status, msg_data = mail.fetch(fetch_ids, "(RFC822)")
            if status != "OK" or not msg_data:
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    seq_num = (
                        response_part[0].split()[0].decode(errors="ignore")
                        if isinstance(response_part[0], bytes)
                        else "unknown"
                    )
                    subject = _clean_header(msg.get("Subject", "No Subject"))
                    conversation_id = msg.get("Message-ID", f"msg-{seq_num}")
                    date_header = msg.get("Date", datetime.now(UTC).isoformat())

                    # Extract body (plain text preferred, fallback to HTML)
                    body: str = ""
                    html_body: str = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            payload = part.get_payload(decode=True)
                            p_str = (
                                payload.decode(errors="ignore")
                                if isinstance(payload, bytes)
                                else str(payload or "")
                            )
                            if ctype == "text/plain" and not body:
                                body = p_str
                            elif ctype == "text/html" and not html_body:
                                html_body = p_str
                    else:
                        payload = msg.get_payload(decode=True)
                        p_str = (
                            payload.decode(errors="ignore")
                            if isinstance(payload, bytes)
                            else str(payload or "")
                        )
                        if msg.get_content_type() == "text/html":
                            html_body = p_str
                        else:
                            body = p_str

                    final_body = clean_html_text(body or html_body or "")

                    results.append(
                        EmailPayload(
                            conversation_id=conversation_id,
                            received_at=date_header,
                            subject=subject,
                            body=final_body,
                        )
                    )

        return results
    except Exception as err:
        logger.error(
            "IMAP connection/retrieval error for %s (%s): %s", username, imap_host, err
        )
        raise ValueError(
            f"IMAP connection failed for {username}@{imap_host}: {err}"
        ) from err
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


async def fetch_emails_from_account(
    account: EmailAccountModel,
    since_date: datetime | None = None,
    max_results: int = 500,
) -> tuple[list[EmailPayload], str | None]:
    """
    Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft Graph)
    or basic-auth IMAP fallback. Returns (emails, new_sync_cursor).
    Applies in-memory date filtering and sorts candidate emails in chronological arrival order (oldest to newest).
    """
    settings = await load_settings()
    if not settings.get("enable_email_intake", False):
        logger.info("Email intake is turned off in settings. Skipping email fetch.")
        return [], None

    auth_type = (account.auth_type or "IMAP").upper()

    async with trace_operation(
        category="email_sync",
        name=f"email_sync_{auth_type.lower()}",
        inputs={
            "account_id": getattr(account, "id", None),
            "username": getattr(account, "username", None),
            "auth_type": auth_type,
            "folder": getattr(account, "folder", "INBOX") or "INBOX",
            "since_date": since_date.isoformat() if since_date else None,
            "max_results": max_results,
        },
    ) as ctx:
        raw_emails: list[EmailPayload] = []
        new_cursor: str | None = None

        if auth_type == "GMAIL_OAUTH":
            token = account.access_token
            query_str = f"label:{account.folder or 'INBOX'}"
            if since_date:
                date_fmt = since_date.strftime("%Y/%m/%d")
                query_str += f" after:{date_fmt}"

            # If no token, refresh first
            if (
                not token
                and account.refresh_token
                and account.client_id
                and account.client_secret
            ):
                try:
                    token = await GmailOAuthAdapter.refresh_access_token(
                        account.client_id, account.client_secret, account.refresh_token
                    )
                    account.access_token = token
                except Exception as err:
                    logger.error("Failed refreshing Gmail access token: %s", err)

            if not token:
                raise ValueError(
                    f"No valid access token or refresh credentials for Gmail account {account.id}"
                )

            try:
                raw_emails, new_cursor = await GmailOAuthAdapter.fetch_messages_delta(
                    access_token=token,
                    history_id=account.sync_cursor,
                    max_results=max_results,
                    query=query_str,
                    since_date=since_date,
                )
            except httpx.HTTPStatusError as http_err:
                if (
                    http_err.response.status_code in (401, 403)
                    and account.refresh_token
                    and account.client_id
                    and account.client_secret
                ):
                    logger.info(
                        "Gmail access token expired (%s). Refreshing token and retrying...",
                        http_err.response.status_code,
                    )
                    token = await GmailOAuthAdapter.refresh_access_token(
                        account.client_id, account.client_secret, account.refresh_token
                    )
                    account.access_token = token
                    (
                        raw_emails,
                        new_cursor,
                    ) = await GmailOAuthAdapter.fetch_messages_delta(
                        access_token=token,
                        history_id=account.sync_cursor,
                        max_results=max_results,
                        query=query_str,
                        since_date=since_date,
                    )
                else:
                    raise

        elif auth_type == "MS_GRAPH_OAUTH":
            token = account.access_token

            # If no token, refresh first
            if (
                not token
                and account.refresh_token
                and account.client_id
                and account.client_secret
            ):
                try:
                    token = await MicrosoftGraphAdapter.refresh_access_token(
                        account.client_id, account.client_secret, account.refresh_token
                    )
                    account.access_token = token
                except Exception as err:
                    logger.error("Failed refreshing MS Graph access token: %s", err)

            if not token:
                raise ValueError(
                    f"No valid access token or refresh credentials for Microsoft Graph account {account.id}"
                )

            try:
                (
                    raw_emails,
                    new_cursor,
                ) = await MicrosoftGraphAdapter.fetch_messages_delta(
                    access_token=token,
                    delta_link=account.sync_cursor,
                    max_results=max_results,
                    folder_id=account.folder or "Inbox",
                    since_date=since_date,
                )
            except httpx.HTTPStatusError as http_err:
                if (
                    http_err.response.status_code in (401, 403)
                    and account.refresh_token
                    and account.client_id
                    and account.client_secret
                ):
                    logger.info(
                        "MS Graph access token expired (%s). Refreshing token and retrying...",
                        http_err.response.status_code,
                    )
                    token = await MicrosoftGraphAdapter.refresh_access_token(
                        account.client_id, account.client_secret, account.refresh_token
                    )
                    account.access_token = token
                    (
                        raw_emails,
                        new_cursor,
                    ) = await MicrosoftGraphAdapter.fetch_messages_delta(
                        access_token=token,
                        delta_link=account.sync_cursor,
                        max_results=max_results,
                        folder_id=account.folder or "Inbox",
                        since_date=since_date,
                    )
                else:
                    raise

        else:
            # Standard IMAP
            raw_emails = await asyncio.to_thread(
                _fetch_imap_emails_sync,
                account.imap_host,
                account.imap_port,
                account.username,
                account.app_password,
                account.folder or "INBOX",
                account.id,
                since_date,
                max_results,
            )
            new_cursor = None

        # Clean HTML bodies
        for em in raw_emails:
            em.body = clean_html_text(em.body)

        # 1. Filter by since_date in memory (universal fallback for all providers)
        filtered_emails: list[EmailPayload] = []
        if since_date:
            since_cmp = (
                since_date.replace(tzinfo=UTC)
                if since_date.tzinfo is None
                else since_date
            )
            for em in raw_emails:
                if em.received_at:
                    em_dt = (
                        em.received_at if isinstance(em.received_at, datetime) else None
                    )
                    if not em_dt:
                        try:
                            em_dt = datetime.fromisoformat(
                                str(em.received_at).replace("Z", "+00:00")
                            )
                        except Exception:
                            em_dt = None
                    if em_dt:
                        em_cmp = (
                            em_dt.replace(tzinfo=UTC) if em_dt.tzinfo is None else em_dt
                        )
                        if em_cmp < since_cmp:
                            continue
                filtered_emails.append(em)
        else:
            filtered_emails = raw_emails

        # 2. Sort candidate emails chronologically in ascending arrival order (oldest first -> newest last)
        def _get_sort_key(em: EmailPayload) -> datetime:
            if isinstance(em.received_at, datetime):
                return (
                    em.received_at
                    if em.received_at.tzinfo
                    else em.received_at.replace(tzinfo=UTC)
                )
            if isinstance(em.received_at, str):
                try:
                    dt = datetime.fromisoformat(em.received_at.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
                except Exception:
                    pass
            return datetime.min.replace(tzinfo=UTC)

        filtered_emails.sort(key=_get_sort_key)

        ctx["outputs"] = {"fetched_count": len(filtered_emails), "cursor": new_cursor}
        return filtered_emails, new_cursor
