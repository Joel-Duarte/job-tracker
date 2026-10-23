from datetime import UTC, datetime

import pytest

from app.core.html_utils import split_latest_email_message
from app.services.email_normalization import (
    normalize_instant,
    parse_calendar,
    parse_mime,
    resolve_deadline,
)
from app.services.email_scheduling import calendar_issue, validate_extraction


@pytest.mark.parametrize(
    "history",
    [
        "<blockquote>Old interview tomorrow at 10</blockquote>",
        '<div class="gmail_quote">Old interview tomorrow at 10</div>',
        "On Oct 20, HR wrote:\nOld interview tomorrow at 10",
        "-----Original Message-----\nOld interview tomorrow at 10",
        "Em 20 outubro 2026 escreveu:\nOld interview tomorrow at 10",
    ],
)
def test_latest_message_excludes_history(history):
    latest, quoted = split_latest_email_message("Thanks!\n" + history)
    assert latest == "Thanks!"
    assert "Old interview" in quoted


def test_quote_only_does_not_fall_back_to_history():
    assert split_latest_email_message("> Old request")[0] == ""
    assert split_latest_email_message("<blockquote>Old request</blockquote>")[0] == ""


def test_mime_alternatives_and_attached_history():
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = "hr@example.com"
    message["Message-ID"] = "<stable@example.com>"
    message.set_content("New plain")
    message.add_alternative(
        "<p>New HTML</p><blockquote>Old action</blockquote>", subtype="html"
    )
    old = EmailMessage()
    old.set_content("Attached historical request")
    message.add_attachment(old)
    result = parse_mime(message.as_bytes())
    assert result.message_id == "stable@example.com"
    assert result.received_at is None
    assert result.plain_body.strip() == "New plain"
    assert "Attached historical" not in result.body
    assert split_latest_email_message(result.body)[0] == "New HTML"


def test_real_instants_and_invalid_times():
    assert normalize_instant("2026-09-14T15:15:00+01:00") == datetime(
        2026, 9, 14, 14, 15, tzinfo=UTC
    )
    assert normalize_instant("garbage") is None
    assert normalize_instant("2026-03-29T01:30:00", "Europe/Lisbon") is None
    assert normalize_instant("2026-10-25T01:30:00", "Europe/Lisbon") is None


def test_deadline_precision_and_message_anchor():
    assert (
        resolve_deadline("Submit by 2026-09-14", None, "Europe/Lisbon")["date"]
        == "2026-09-14"
    )
    assert (
        resolve_deadline("Submit tomorrow", "2026-09-14T23:30:00Z", "Europe/Lisbon")[
            "date"
        ]
        == "2026-09-16"
    )
    assert resolve_deadline("Submit tomorrow", None, "Europe/Lisbon")["issue"]
    assert resolve_deadline("2026-03-29 01:30 Europe/Lisbon", None, "UTC")["issue"]


def test_history_evidence_cannot_mutate_state():
    result = validate_extraction(
        {
            "status": "REJECTED",
            "action_required": True,
            "action": "Old task",
            "action_evidence": "Old request",
            "status_evidence": "Old rejection",
            "due_date": "2026-10-20T10:00:00",
        },
        "Thanks!",
        None,
        "UTC",
    )
    assert result["status"] is None
    assert not result["action_required"]
    assert result["due_date"] is None


def test_prose_meetings_are_proposals():
    result = validate_extraction(
        {"event_type": "INTERVIEW_SCHEDULED", "meeting_proposal": "Tuesday at 14:00"},
        "Tuesday at 14:00 works",
        None,
        "UTC",
    )
    assert result["event_type"] == "INTERVIEW_REQUESTED"
    assert result["temporal"]["meeting_proposal"] == "Tuesday at 14:00"


def test_ics_timezone_and_revision_fields():
    events = parse_calendar(b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
METHOD:REQUEST\r
BEGIN:VEVENT\r
UID:one\r
ORGANIZER:mailto:hr@example.com\r
SEQUENCE:2\r
DTSTAMP:20260910T120000Z\r
DTSTART;TZID=Europe/Lisbon:20260914T153000\r
SUMMARY:Interview\r
END:VEVENT\r
END:VCALENDAR\r
""")
    assert events[0]["sequence"] == 2
    assert events[0]["timezone"] == "Europe/Lisbon"
    assert normalize_instant(events[0]["start"]).hour == 14
    assert calendar_issue(events, "hr@example.com") is None
    assert calendar_issue(events, "other@example.com") == "CALENDAR_ORGANIZER_MISMATCH"
    assert calendar_issue(events * 2, "hr@example.com") == "MULTIPLE_CALENDAR_EVENTS"


@pytest.mark.asyncio
async def test_calendar_revisions_are_idempotent(db_session):
    from app.models.applications import ApplicationModel, CompanyModel
    from app.services.email_scheduling import apply_calendar

    company = CompanyModel(name="Acme", name_normalized="acme")
    db_session.add(company)
    await db_session.flush()
    application = ApplicationModel(
        company_id=company.id,
        position="Engineer",
        position_normalized="engineer",
        status="APPLIED",
    )
    db_session.add(application)
    await db_session.flush()
    invite = {
        "uid": "same",
        "organizer": "hr@example.com",
        "method": "REQUEST",
        "sequence": 1,
        "stamp": "2026-09-01T12:00:00Z",
        "start": "2026-09-14T15:30:00+01:00",
    }
    payload, changed = await apply_calendar(db_session, application.id, invite, "UTC")
    assert changed and payload["scheduled_at"] == "2026-09-14T14:30:00+00:00"
    await db_session.flush()
    assert not (await apply_calendar(db_session, application.id, invite, "UTC"))[1]
    rescheduled = {**invite, "sequence": 2, "start": "2026-09-15T15:30:00+01:00"}
    assert (await apply_calendar(db_session, application.id, rescheduled, "UTC"))[0][
        "scheduled_at"
    ].startswith("2026-09-15")
    assert not (await apply_calendar(db_session, application.id, invite, "UTC"))[1]
    cancelled = {**rescheduled, "sequence": 3, "method": "CANCEL"}
    assert (await apply_calendar(db_session, application.id, cancelled, "UTC"))[0][
        "scheduled_at"
    ] is None
    assert not (
        await apply_calendar(
            db_session,
            application.id,
            {**invite, "method": "REPLY", "sequence": 5},
            "UTC",
        )
    )[1]
    assert application.status == "APPLIED"


@pytest.mark.asyncio
async def test_concurrent_message_import_is_atomic(db_session):
    import asyncio

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.applications import (
        ActionItemModel,
        ApplicationEventModel,
        ApplicationModel,
        CompanyModel,
    )
    from app.models.processed_email import ProcessedEmailModel
    from app.services.graph_nodes import db_commit_node

    company = CompanyModel(name="Atomic Co", name_normalized="atomic co")
    db_session.add(company)
    await db_session.flush()
    application = ApplicationModel(
        company_id=company.id,
        position="Engineer",
        position_normalized="engineer",
        status="OFFER",
    )
    db_session.add(application)
    await db_session.commit()
    state = {
        "message_id": "atomic@example.com",
        "company_id": company.id,
        "application_id": application.id,
        "is_application": True,
        "body": "Send documents",
        "subject": "Documents",
        "received_at": "2026-10-23T10:00:00Z",
        "extracted_data": {
            "event_type": "STATUS_UPDATE",
            "action_required": True,
            "action": "Send documents",
            "temporal": {"version": 2},
        },
    }
    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def run():
        async with factory() as session:
            return await db_commit_node(state, {"configurable": {"db": session}})

    results = await asyncio.gather(run(), run())
    assert sum(bool(item.get("is_duplicate")) for item in results) == 1
    assert (
        await db_session.scalar(select(func.count()).select_from(ApplicationEventModel))
        == 1
    )
    assert (
        await db_session.scalar(select(func.count()).select_from(ActionItemModel)) == 1
    )
    assert (
        await db_session.scalar(select(func.count()).select_from(ProcessedEmailModel))
        == 1
    )
    await db_session.refresh(application)
    assert application.status == "OFFER"


@pytest.mark.asyncio
async def test_timezone_override_and_invalid_zone(db_session):
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        path = "/api/v1/ai/global-settings"
        response = await client.patch(
            path,
            json={"DISPLAY_TIMEZONE": "Europe/Lisbon", "TIMEZONE_SOURCE": "manual"},
        )
        assert response.status_code == 200
        response = await client.patch(
            path,
            json={"DISPLAY_TIMEZONE": "America/New_York", "TIMEZONE_SOURCE": "auto"},
        )
        assert response.json()["DISPLAY_TIMEZONE"] == "Europe/Lisbon"
        response = await client.patch(path, json={"DISPLAY_TIMEZONE": "Invalid/Zone"})
        assert response.status_code == 422
        response = await client.patch(
            path,
            json={
                "DISPLAY_TIMEZONE": "America/New_York",
                "TIMEZONE_SOURCE": "auto",
                "RESET_TIMEZONE_OVERRIDE": True,
            },
        )
        assert response.json()["DISPLAY_TIMEZONE"] == "America/New_York"
        assert response.json()["TIMEZONE_SOURCE"] == "auto"


@pytest.mark.parametrize(
    "clause, expected",
    [
        (
            "Submit by 14 September 2026 at 4:30 PM Europe/Lisbon",
            "2026-09-14T15:30:00+00:00",
        ),
        ("Submit by September 14, 2026 at 16h30 UTC+1", "2026-09-14T15:30:00+00:00"),
        ("Submit by 2026-09-14T16:30:00+01:00", "2026-09-14T15:30:00+00:00"),
    ],
)
def test_explicit_deadline_clock_and_zone(clause, expected):
    assert resolve_deadline(clause, None, "UTC")["at"] == expected


@pytest.mark.asyncio
async def test_scheduling_migration_round_trip_preserves_legacy_deadline(db_session):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect, select

    from app.models.applications import ActionItemModel

    legacy = ActionItemModel(
        title="Existing deadline",
        due_date=datetime(2026, 9, 14, 15, tzinfo=UTC),
        status="PENDING",
    )
    db_session.add(legacy)
    await db_session.commit()
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/4f6e8a1c3d5b_reliable_email_scheduling.py"
    )
    spec = importlib.util.spec_from_file_location("scheduling_migration", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)

    def round_trip(connection):
        with Operations.context(MigrationContext.configure(connection)):
            revision.downgrade()
            assert not inspect(connection).has_table("email_calendar_occurrences")
            revision.upgrade()
            assert inspect(connection).has_table("email_calendar_occurrences")

    async with db_session.bind.begin() as connection:
        await connection.run_sync(round_trip)
    preserved = await db_session.scalar(
        select(ActionItemModel)
        .where(ActionItemModel.id == legacy.id)
        .execution_options(populate_existing=True)
    )
    assert preserved.due_date == datetime(2026, 9, 14, 15, tzinfo=UTC)
    assert preserved.temporal_metadata is None
