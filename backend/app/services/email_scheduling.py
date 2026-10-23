"""Evidence gates and persistent, versioned calendar occurrence state."""

import hashlib
import re
from datetime import UTC, datetime

from sqlalchemy import select

from app.services.email_normalization import normalize_instant, resolve_deadline


def validate_extraction(
    data: dict, latest: str, received: str | None, zone: str
) -> dict:
    data = dict(data)
    issues = []

    def supported(field):
        evidence = data.get(field)
        return (
            isinstance(evidence, str)
            and bool(evidence.strip())
            and evidence.strip() in latest
        )

    acknowledgment = bool(
        re.fullmatch(
            r"[\s!.,]*(?:thanks(?: you)?|thank you|got it|received|noted|obrigad[oa]|merci|gracias)[\s!.,]*",
            latest,
            flags=re.I,
        )
    )
    if acknowledgment:
        data.update(
            status=None, action_required=False, action=None, event_type="STATUS_UPDATE"
        )
    if acknowledgment or not supported("status_evidence"):
        data["status"] = None
    if acknowledgment or not supported("action_evidence"):
        data.update(action_required=False, action=None)
    if (
        not supported("status_evidence")
        and not supported("action_evidence")
        and not data.get("meeting_proposal")
    ):
        data["event_type"] = (
            "STATUS_UPDATE"
            if data.get("email_type") in {"JOB_APPLICATION", "RECRUITER_OUTREACH"}
            else "OTHER"
        )
    data["due_date"] = None  # legacy model output must never drive scheduling
    deadline = None
    if supported("deadline_evidence"):
        deadline = resolve_deadline(data["deadline_evidence"], received, zone)
        if deadline.get("issue"):
            issues.append(deadline["issue"])
    proposal = data.get("meeting_proposal")
    if proposal and (not isinstance(proposal, str) or proposal not in latest):
        proposal = None
    if data.get("event_type") == "INTERVIEW_SCHEDULED":
        data["event_type"] = "INTERVIEW_REQUESTED"
    data["temporal"] = {
        "version": 2,
        "deadline": deadline,
        "meeting_proposal": proposal,
        "issues": issues,
        "timezone": zone,
    }
    return data


def calendar_issue(
    events: list[dict], sender: str | None, zone: str = "UTC"
) -> str | None:
    if not events:
        return None
    if len(events) != 1:
        return "MULTIPLE_CALENDAR_EVENTS"
    item = events[0]
    if item.get("error") or not item.get("uid") or not item.get("organizer"):
        return "INVALID_CALENDAR"
    if item.get("recurring"):
        return "RECURRING_CALENDAR_REVIEW"
    if item.get("method") not in ("REQUEST", "CANCEL", "REPLY"):
        return "UNSUPPORTED_CALENDAR_METHOD"
    if item.get("method") != "REPLY" and (sender or "").lower() != item["organizer"]:
        return "CALENDAR_ORGANIZER_MISMATCH"
    if item.get("method") == "REQUEST" and (
        item.get("date_only")
        or not normalize_instant(item.get("start"), item.get("timezone") or zone)
    ):
        return "INVALID_CALENDAR_TIME"
    return None


async def apply_calendar(
    db, application_id: int, item: dict, zone: str
) -> tuple[dict | None, bool]:
    from app.models.applications import EmailCalendarOccurrenceModel

    key = hashlib.sha256(
        f"{application_id}|{item['organizer']}|{item['uid']}|{item.get('recurrence_id', '')}".encode()
    ).hexdigest()
    occurrence = (
        await db.execute(
            select(EmailCalendarOccurrenceModel)
            .where(EmailCalendarOccurrenceModel.identity_key == key)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if item["method"] == "REPLY":
        return None, False
    stamp = normalize_instant(item.get("stamp")) or datetime.min.replace(tzinfo=UTC)
    revision = (item.get("sequence", 0), stamp)
    if occurrence:
        old_stamp = normalize_instant(
            occurrence.calendar_data.get("stamp")
        ) or datetime.min.replace(tzinfo=UTC)
        if revision <= (occurrence.calendar_data.get("sequence", 0), old_stamp):
            return None, False
    else:
        occurrence = EmailCalendarOccurrenceModel(
            identity_key=key, application_id=application_id, calendar_data={}
        )
        db.add(occurrence)
    cancelled = item["method"] == "CANCEL" or item.get("status") == "CANCELLED"
    start = normalize_instant(item.get("start"), item.get("timezone") or zone)
    occurrence.calendar_data = {
        **item,
        "cancelled": cancelled,
        "start_utc": start.isoformat() if start else None,
    }
    occurrence.scheduled_at = None if cancelled else start
    return {
        "calendar": occurrence.calendar_data,
        "scheduled_at": occurrence.scheduled_at.isoformat()
        if occurrence.scheduled_at
        else None,
        "schedule_state": "cancelled" if cancelled else "confirmed",
    }, True


def current_schedule(events, actions, occurrences=None):
    """Select latest revision per occurrence; never revive a cancelled occurrence."""
    ordered = sorted(
        events or [],
        key=lambda event: (
            normalize_instant(event.email_received_at)
            or datetime.min.replace(tzinfo=UTC)
        ),
        reverse=True,
    )
    # Explicit user scheduling is authoritative until a later calendar revision.
    if (
        ordered
        and not occurrences
        and (ordered[0].raw_payload or {}).get("interview_stage")
        == "Task Completed / Awaiting Response"
    ):
        return None, "Task Completed / Awaiting Response"
    schedule_events = [
        event
        for event in ordered
        if (event.raw_payload or {}).get("schedule_state")
        or (event.raw_payload or {}).get("scheduled_at")
    ]
    if schedule_events and schedule_events[0].source_channel == "MANUAL":
        manual = schedule_events[0].raw_payload
        if (
            manual.get("schedule_state") == "cancelled"
            or manual.get("interview_stage") == "Task Completed / Awaiting Response"
        ):
            return None, None
        return normalize_instant(manual.get("scheduled_at")), manual.get(
            "interview_stage"
        )
    if occurrences:
        active = [
            (
                normalize_instant(row.scheduled_at),
                row.calendar_data.get("summary") or "Interview",
            )
            for row in occurrences
            if row.scheduled_at
        ]
        if not active:
            return None, None
        future = [item for item in active if item[0] >= datetime.now(UTC)]
        return min(future) if future else max(active)
    seen = set()
    scheduled = []
    has_v2 = any(
        bool(
            (event.raw_payload or {}).get("calendar")
            or (event.raw_payload or {}).get("schedule_state")
        )
        for event in ordered
    )
    for event in ordered:
        payload = event.raw_payload or {}
        calendar = payload.get("calendar")
        if calendar:
            key = (
                calendar.get("organizer"),
                calendar.get("uid"),
                calendar.get("recurrence_id"),
            )
            if key in seen:
                continue
            seen.add(key)
            # Compare protocol revision rather than message arrival order.
            revisions = [
                other.raw_payload
                for other in ordered
                if (other.raw_payload or {}).get("calendar")
                and (
                    other.raw_payload["calendar"].get("organizer"),
                    other.raw_payload["calendar"].get("uid"),
                    other.raw_payload["calendar"].get("recurrence_id"),
                )
                == key
            ]
            payload = max(
                revisions,
                key=lambda p: (
                    p["calendar"].get("sequence", 0),
                    p["calendar"].get("stamp") or "",
                ),
            )
            if payload.get("schedule_state") == "confirmed":
                instant = normalize_instant(payload.get("scheduled_at"))
                if instant:
                    scheduled.append((instant, calendar.get("summary")))
        elif payload.get("scheduled_at") and not has_v2:
            instant = normalize_instant(payload["scheduled_at"])
            if instant:
                return instant, payload.get("interview_stage")
    if scheduled:
        now = datetime.now(UTC)
        future = [item for item in scheduled if item[0] >= now]
        return min(future) if future else max(scheduled)
    if not has_v2:
        for action in actions or []:
            if (
                not action.temporal_metadata
                and action.status == "PENDING"
                and "interview" in (action.title or "").lower()
                and action.due_date
            ):
                return action.due_date, action.title
    return None, next(
        (
            (event.raw_payload or {}).get("interview_stage")
            for event in ordered
            if (event.raw_payload or {}).get("interview_stage")
        ),
        None,
    )


def schedule_version(app, scheduled):
    if scheduled is None:
        return None
    for event in app.events or []:
        payload = event.raw_payload or {}
        if payload.get("temporal", {}).get("version") == 2 and normalize_instant(
            payload.get("scheduled_at")
        ) == normalize_instant(scheduled):
            return 2
    return None
