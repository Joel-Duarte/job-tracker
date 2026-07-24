import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Optional
import asyncio

from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailPayload


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
    mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
    mail.login(account.username, account.app_password)
    mail.select(account.folder)

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
) -> List[EmailPayload]:
    """Async wrapper to offload blocking IMAP network operations to threadpool."""
    return await asyncio.to_thread(_fetch_imap_emails_sync, account, since_date)