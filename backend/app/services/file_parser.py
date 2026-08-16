import email
import hashlib
import io
import logging
import uuid
from datetime import UTC, datetime
from email import policy
from email.utils import parsedate_to_datetime

from app.schemas.intake import EmailPayload

logger = logging.getLogger(__name__)


def _extract_ics_summary(ics_bytes: bytes) -> str:
    """Extracts summary and date info from raw .ics calendar payload."""
    try:
        text = ics_bytes.decode("utf-8", errors="replace")
        lines = text.splitlines()
        extracted: list[str] = []
        for line in lines:
            if line.startswith("SUMMARY:"):
                extracted.append(f"Meeting Title: {line[8:].strip()}")
            elif line.startswith("DTSTART"):
                extracted.append(f"Start: {line.split(':', 1)[-1].strip()}")
            elif line.startswith("DTEND"):
                extracted.append(f"End: {line.split(':', 1)[-1].strip()}")
            elif line.startswith("DESCRIPTION:"):
                extracted.append(f"Description: {line[12:].strip()}")
        if extracted:
            return "\n[Calendar Event (.ics)]\n" + "\n".join(extracted)
    except Exception as err:
        logger.warning("Failed parsing .ics attachment: %s", err)
    return ""


def parse_eml(content: bytes) -> EmailPayload:
    """Parses raw RFC 822 / MIME .eml bytes into EmailPayload."""
    msg = email.message_from_bytes(content, policy=policy.default)

    subject = msg.get("Subject", "No Subject").strip()
    sender = msg.get("From", "").strip()
    message_id = msg.get("Message-ID", f"eml-{uuid.uuid4().hex[:12]}").strip()
    conversation_id = msg.get("Thread-Topic") or msg.get("In-Reply-To") or message_id

    # Parse date
    received_at = datetime.now(UTC)
    date_header = msg.get("Date")
    if date_header:
        try:
            parsed_dt = parsedate_to_datetime(date_header)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=UTC)
            received_at = parsed_dt
        except Exception:
            pass

    # Extract body and calendar attachments
    body_parts: list[str] = []
    ics_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if (
                content_type == "text/plain"
                and "attachment" not in content_disposition
                or (
                    content_type == "text/html"
                    and not body_parts
                    and "attachment" not in content_disposition
                )
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(
                        payload.decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                    )
            elif (
                content_type == "text/calendar"
                or part.get_filename()
                and part.get_filename().endswith(".ics")
            ):
                raw_ics = part.get_payload(decode=True)
                if raw_ics:
                    ics_summary = _extract_ics_summary(raw_ics)
                    if ics_summary:
                        ics_parts.append(ics_summary)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(
                payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            )

    full_body = "\n".join(body_parts).strip() if body_parts else msg.get_payload() or ""
    if isinstance(full_body, list):
        full_body = "\n".join(str(p) for p in full_body)
    if ics_parts:
        full_body += "\n" + "\n".join(ics_parts)

    return EmailPayload(
        conversation_id=conversation_id,
        message_id=message_id,
        received_at=received_at,
        subject=subject or "No Subject",
        body=full_body,
    )


def parse_msg(content: bytes) -> EmailPayload:
    """Parses Microsoft Outlook .msg binary bytes into EmailPayload."""
    import extract_msg

    msg = extract_msg.Message(io.BytesIO(content))
    subject = msg.subject or "No Subject"
    message_id = msg.messageId or f"msg-{uuid.uuid4().hex[:12]}"
    conversation_id = msg.conversationTopic or message_id

    received_at = msg.date or datetime.now(UTC)
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=UTC)

    body = msg.body or msg.htmlBody or ""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")

    ics_parts: list[str] = []
    if hasattr(msg, "attachments"):
        for att in msg.attachments:
            if (
                hasattr(att, "longFilename")
                and att.longFilename
                and att.longFilename.endswith(".ics")
            ):
                ics_summary = _extract_ics_summary(att.data)
                if ics_summary:
                    ics_parts.append(ics_summary)

    if ics_parts:
        body += "\n" + "\n".join(ics_parts)

    return EmailPayload(
        conversation_id=conversation_id,
        message_id=message_id,
        received_at=received_at,
        subject=subject,
        body=body,
    )


def parse_txt(content: bytes, filename: str = "upload.txt") -> EmailPayload:
    """Parses plaintext / raw thread text into EmailPayload."""
    text = content.decode("utf-8", errors="replace").strip()
    lines = text.splitlines()

    subject = ""
    body_lines = []
    in_headers = True

    # Simple check for basic header block
    for idx, line in enumerate(lines):
        if in_headers:
            lower = line.lower()
            if lower.startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif (
                lower.startswith("from:")
                or lower.startswith("date:")
                or lower.startswith("to:")
            ):
                continue
            elif line.strip() == "":
                in_headers = False
            else:
                in_headers = False
                body_lines.append(line)
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip() if body_lines else text
    if not subject:
        # Take first non-empty line up to 80 chars or fallback to filename
        first_line = lines[0].strip() if lines else filename
        subject = first_line[:80] if len(first_line) > 0 else filename

    # Compute deterministic message_id from content hash
    content_hash = hashlib.sha256(content).hexdigest()[:16]
    msg_id = f"txt-{content_hash}"

    return EmailPayload(
        conversation_id=f"conv-{content_hash}",
        message_id=msg_id,
        received_at=datetime.now(UTC),
        subject=subject,
        body=body,
    )


def parse_uploaded_file(filename: str, content: bytes) -> EmailPayload:
    """Dispatches file parsing based on extension (.eml, .msg, .txt)."""
    fn_lower = filename.lower()
    if fn_lower.endswith(".eml"):
        return parse_eml(content)
    elif fn_lower.endswith(".msg"):
        return parse_msg(content)
    elif fn_lower.endswith(".txt"):
        return parse_txt(content, filename=filename)
    else:
        # Default to text parser for other formats (e.g. .log, .raw)
        return parse_txt(content, filename=filename)
