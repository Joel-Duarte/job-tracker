import asyncio
from datetime import datetime, timezone
import email
from email.header import decode_header
import imaplib
import logging
from typing import List, Optional, Tuple

from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailPayload
from app.services.oauth_adapters import GmailOAuthAdapter, MicrosoftGraphAdapter

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
    account: EmailAccountModel, since_date: Optional[datetime] = None
) -> List[EmailPayload]:
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

    for mail_id in email_ids:
        status, msg_data = mail.fetch(mail_id, "(RFC822)")
        if status != "OK":
            continue

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject = _clean_header(msg.get("Subject", "No Subject"))
                conversation_id = msg.get("Message-ID", f"msg-{mail_id.decode()}")
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
    account: EmailAccountModel, since_date: Optional[datetime] = None
) -> Tuple[List[EmailPayload], Optional[str]]:
    """
    Fetches emails using either modern OAuth adapters (Google Workspace, Microsoft Graph)
    or basic-auth IMAP fallback. Returns (emails, new_sync_cursor).
    """
    auth_type = (account.auth_type or "IMAP").upper()

    if auth_type == "GMAIL_OAUTH":
        token = account.access_token
        # Try refreshing token if refresh token and credentials are present
        if not token and account.refresh_token and account.client_id and account.client_secret:
            try:
                token = await GmailOAuthAdapter.refresh_access_token(
                    account.client_id, account.client_secret, account.refresh_token
                )
                account.access_token = token
            except Exception as err:
                logger.error("Failed refreshing Gmail access token: %s", err)

        if not token:
            logger.warning("No valid access token for Gmail OAuth account %s", account.id)
            return [], None

        query_str = f"label:{account.folder or 'INBOX'}"
        if since_date:
            date_fmt = since_date.strftime("%Y/%m/%d")
            query_str += f" after:{date_fmt}"

        return await GmailOAuthAdapter.fetch_messages_delta(
            access_token=token,
            history_id=account.sync_cursor,
            query=query_str,
        )

    elif auth_type == "MS_GRAPH_OAUTH":
        token = account.access_token
        if not token and account.refresh_token and account.client_id and account.client_secret:
            try:
                token = await MicrosoftGraphAdapter.refresh_access_token(
                    account.client_id, account.client_secret, account.refresh_token
                )
                account.access_token = token
            except Exception as err:
                logger.error("Failed refreshing MS Graph access token: %s", err)

        if not token:
            logger.warning("No valid access token for MS Graph OAuth account %s", account.id)
            return [], None

        return await MicrosoftGraphAdapter.fetch_messages_delta(
            access_token=token,
            delta_link=account.sync_cursor,
        )

    else:
        # Standard IMAP
        emails = await asyncio.to_thread(_fetch_imap_emails_sync, account, since_date)
        return emails, None