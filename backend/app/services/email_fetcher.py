import asyncio
import email
import imaplib
import logging
from datetime import datetime
from email.header import decode_header

from app.core.config_manager import load_settings
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
    account: EmailAccountModel, since_date: datetime | None = None
) -> list[EmailPayload]:
    """Synchronous worker that performs actual IMAP connection and retrieval."""
    if not account.imap_host or not account.app_password:
        logger.warning("IMAP host or password missing for account %s", account.id)
        return []

    mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port or 993)
    mail.login(account.username, account.app_password)
    mail.select(account.folder or "INBOX")

    # Build search query
    if since_date:
        date_str = since_date.strftime("%d-%b-%Y")
        search_criterion = f'(SINCE "{date_str}")'
    else:
        search_criterion = "ALL"

    status, messages = mail.search(None, search_criterion)
    if status != "OK" or not messages[0]:
        mail.logout()
        return []

    email_ids = messages[0].split()
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
                date_header = msg.get("Date", datetime.now().isoformat())

                # Extract plain text body
                body: str = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if isinstance(payload, bytes):
                                body = payload.decode(errors="ignore")
                            else:
                                body = str(payload)
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body = payload.decode(errors="ignore")
                    else:
                        body = str(payload)

                results.append(
                    EmailPayload(
                        conversation_id=conversation_id,
                        received_at=date_header,
                        subject=subject,
                        body=body or "",
                    )
                )

    mail.logout()
    return results


async def fetch_emails_from_account(
    account: EmailAccountModel, since_date: datetime | None = None
) -> tuple[list[EmailPayload], str | None]:
    """
    Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft Graph)
    or basic-auth IMAP fallback. Returns (emails, new_sync_cursor).
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
        },
    ) as ctx:
        if auth_type == "GMAIL_OAUTH":
            token = account.access_token
            # Try refreshing token if refresh token and credentials are present
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
                logger.warning(
                    "No valid access token for Gmail OAuth account %s", account.id
                )
                ctx["error"] = (
                    f"No valid access token for Gmail OAuth account {account.id}"
                )
                ctx["outputs"] = {"fetched_count": 0}
                return [], None

            query_str = f"label:{account.folder or 'INBOX'}"
            if since_date:
                date_fmt = since_date.strftime("%Y/%m/%d")
                query_str += f" after:{date_fmt}"

            emails, cursor = await GmailOAuthAdapter.fetch_messages_delta(
                access_token=token,
                history_id=account.sync_cursor,
                query=query_str,
            )
            ctx["outputs"] = {"fetched_count": len(emails), "cursor": cursor}
            return emails, cursor

        elif auth_type == "MS_GRAPH_OAUTH":
            token = account.access_token
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
                logger.warning(
                    "No valid access token for MS Graph OAuth account %s", account.id
                )
                ctx["error"] = (
                    f"No valid access token for MS Graph OAuth account {account.id}"
                )
                ctx["outputs"] = {"fetched_count": 0}
                return [], None

            emails, cursor = await MicrosoftGraphAdapter.fetch_messages_delta(
                access_token=token,
                delta_link=account.sync_cursor,
            )
            ctx["outputs"] = {"fetched_count": len(emails), "cursor": cursor}
            return emails, cursor

        else:
            # Standard IMAP
            emails = await asyncio.to_thread(
                _fetch_imap_emails_sync, account, since_date
            )
            ctx["outputs"] = {"fetched_count": len(emails)}
            return emails, None
