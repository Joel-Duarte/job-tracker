"""Lossless MIME selection and deterministic calendar/date normalization."""

import hashlib
import re
from datetime import UTC, date, datetime, timedelta
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

from dateutil import tz
from icalendar import Calendar


def message_identity(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return value.strip().strip("<>").strip()


def normalize_instant(
    value: str | datetime | None, zone: str = "UTC"
) -> datetime | None:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            result = value
        else:
            try:
                result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError:
                result = parsedate_to_datetime(value)
        if result.tzinfo is None:
            result = result.replace(tzinfo=ZoneInfo(zone))
        if not tz.datetime_exists(result) or tz.datetime_ambiguous(result):
            return None
        return result.astimezone(UTC)
    except (ValueError, TypeError, KeyError, OverflowError):
        return None


def parse_calendar(content: bytes) -> list[dict]:
    try:
        calendar = Calendar.from_ical(content)
        result = []
        for event in calendar.walk("VEVENT"):

            def temporal(key, event=event):
                field = event.get(key)
                if field is None:
                    return None
                value = field.dt
                return (
                    value.isoformat()
                    if isinstance(value, (datetime, date))
                    else str(value)
                )

            start = event.get("DTSTART")
            result.append(
                {
                    "uid": str(event.get("UID", "")),
                    "organizer": str(event.get("ORGANIZER", ""))
                    .removeprefix("mailto:")
                    .lower(),
                    "method": str(calendar.get("METHOD", "")).upper(),
                    "status": str(event.get("STATUS", "")).upper(),
                    "sequence": int(event.get("SEQUENCE", 0)),
                    "stamp": temporal("DTSTAMP"),
                    "recurrence_id": temporal("RECURRENCE-ID") or "",
                    "recurring": bool(event.get("RRULE")),
                    "start": temporal("DTSTART"),
                    "end": temporal("DTEND"),
                    "timezone": str(start.params.get("TZID", "")) if start else "",
                    "date_only": bool(start and not isinstance(start.dt, datetime)),
                    "summary": str(event.get("SUMMARY", "")),
                }
            )
        return result
    except Exception:
        return [{"error": "INVALID_CALENDAR"}]


def parse_mime(content: bytes):
    from app.schemas.intake import EmailPayload

    msg = BytesParser(policy=policy.default).parsebytes(content)
    plain, html, calendars = [], [], []

    def visit(part):
        if part.get_content_type() == "message/rfc822":
            return
        if part.is_multipart():
            for child in part.iter_parts():
                visit(child)
            return
        kind = part.get_content_type()
        if kind == "text/calendar" or (part.get_filename() or "").lower().endswith(
            ".ics"
        ):
            calendars.extend(parse_calendar(part.get_payload(decode=True) or b""))
        elif part.get_content_disposition() != "attachment" and kind in (
            "text/plain",
            "text/html",
        ):
            raw = part.get_payload(decode=True) or b""
            try:
                text = raw.decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
            except LookupError:
                text = raw.decode("utf-8", errors="replace")
            (plain if kind == "text/plain" else html).append(text)

    visit(msg)
    name, sender = parseaddr(str(msg.get("From", "")))
    identity = message_identity(str(msg.get("Message-ID", "")))
    references = re.findall(r"<[^>]+>", str(msg.get("References", "")))
    parent = message_identity(str(msg.get("In-Reply-To", "")))
    return EmailPayload(
        message_id=identity or "mime-" + hashlib.sha256(content).hexdigest(),
        internet_message_id=identity,
        conversation_id=message_identity(references[0])
        if references
        else parent or identity or "mime-" + hashlib.sha256(content).hexdigest(),
        in_reply_to=parent,
        references=[message_identity(item) for item in references],
        sender=sender or None,
        sender_name=name or None,
        subject=str(msg.get("Subject", "No Subject")),
        received_at=normalize_instant(str(msg.get("Date", ""))),
        body=html[0] if html else plain[0] if plain else "",
        plain_body=plain[0] if plain else None,
        html_body=html[0] if html else None,
        calendar_events=calendars,
    )


def resolve_deadline(excerpt: str, received: str | None, zone: str) -> dict:
    """Accept only constrained, explicit dates; never let a model invent an instant."""
    anchor = normalize_instant(received)
    day = None
    clock = None
    offset = ""
    iso_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}(?!\d)", excerpt)
    named_dates = re.findall(
        r"\b(?:\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b",
        excerpt,
        re.I,
    )
    if len(iso_dates) + len(named_dates) > 1:
        return {"issue": "MULTIPLE_DEADLINE_DATES"}
    if iso_dates:
        day = iso_dates[0]
    elif named_dates:
        from dateutil.parser import parse

        try:
            day = parse(named_dates[0]).date().isoformat()
        except ValueError:
            return {"issue": "INVALID_DEADLINE"}
    elif anchor and re.search(r"\b(today|tomorrow|hoje|amanhã)\b", excerpt, re.I):
        local = anchor.astimezone(ZoneInfo(zone))
        day = (
            local.date()
            + timedelta(days=bool(re.search(r"\b(tomorrow|amanhã)\b", excerpt, re.I)))
        ).isoformat()
    time_match = re.search(
        r"(?<!\d)(\d{1,2})[:h](\d{2})(?::(\d{2}))?\s*(AM|PM)?(Z|[+-]\d{2}:?\d{2})?\b",
        excerpt,
        re.I,
    )
    if time_match:
        hour = int(time_match[1])
        if time_match[4]:
            if not 1 <= hour <= 12:
                return {"issue": "INVALID_DEADLINE_TIME"}
            hour = hour % 12 + (12 if time_match[4].upper() == "PM" else 0)
        clock = f"{hour:02}:{time_match[2]}:{time_match[3] or '00'}"
        offset = time_match[5] or ""
        if offset.upper() == "Z":
            offset = "+00:00"
    zone_offset = re.search(
        r"\b(?:UTC|GMT)\s*([+-]\d{1,2})(?::?(\d{2}))?\b", excerpt, re.I
    )
    if zone_offset:
        hours = int(zone_offset[1])
        offset = f"{'-' if zone_offset[1].startswith('-') else '+'}{abs(hours):02}:{zone_offset[2] or '00'}"
    elif re.search(r"\b(?:UTC|GMT)\b", excerpt):
        offset = "+00:00"
    if not day:
        return {"issue": "AMBIGUOUS_DEADLINE"}
    try:
        date.fromisoformat(day)
    except ValueError:
        return {"issue": "INVALID_DEADLINE"}
    if not clock:
        return {"date": day, "precision": "date", "timezone": zone}
    explicit_zone = re.search(r"\b[A-Za-z_]+/[A-Za-z_]+(?:/[A-Za-z_]+)?\b", excerpt)
    chosen_zone = explicit_zone.group() if explicit_zone else zone
    # Abbreviations are not globally unique; an explicit offset or IANA zone is required.
    if (
        not offset
        and not explicit_zone
        and re.search(
            r"\b(?:WEST|WET|CEST|CET|BST|EEST|EET|PDT|PST|EDT|EST|CDT|CST|MDT|MST)\b",
            excerpt,
        )
    ):
        return {"issue": "AMBIGUOUS_TIMEZONE"}
    instant = normalize_instant(f"{day}T{clock}{offset}", chosen_zone)
    return (
        {"at": instant.isoformat(), "precision": "instant", "timezone": chosen_zone}
        if instant
        else {"issue": "INVALID_OR_AMBIGUOUS_TIME"}
    )
