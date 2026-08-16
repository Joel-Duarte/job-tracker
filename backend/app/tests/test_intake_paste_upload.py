import io
from unittest.mock import AsyncMock, patch

import pytest
from app.core.database import get_db
from app.main import app
from app.schemas.intake import ExtractedEmailInfo
from app.services.file_parser import parse_eml, parse_txt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_parse_eml_and_ics():
    raw_eml = b"""From: recruiter@uber.com
To: applicant@example.com
Subject: Interview Scheduled with Uber
Date: Fri, 15 Aug 2026 10:00:00 +0000
Message-ID: <msg-uber-12345@uber.com>
Content-Type: multipart/mixed; boundary="BOUNDARY"

--BOUNDARY
Content-Type: text/plain; charset="utf-8"

Hi candidate, your interview is confirmed for tomorrow.

--BOUNDARY
Content-Type: text/calendar; name="invite.ics"
Content-Disposition: attachment; filename="invite.ics"

BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Technical Interview with Uber
DTSTART:20260816T140000Z
DTEND:20260816T150000Z
DESCRIPTION:Uber backend engineer screen.
END:VEVENT
END:VCALENDAR
--BOUNDARY--
"""
    payload = parse_eml(raw_eml)
    assert payload.subject == "Interview Scheduled with Uber"
    assert payload.message_id == "<msg-uber-12345@uber.com>"
    assert "your interview is confirmed" in payload.body
    assert "Technical Interview with Uber" in payload.body


def test_parse_txt():
    raw_txt = b"""Subject: Application Confirmation - Netflix
From: jobs@netflix.com

Thank you for applying to the Senior Distributed Systems Engineer role at Netflix."""

    payload = parse_txt(raw_txt, "netflix.txt")
    assert payload.subject == "Application Confirmation - Netflix"
    assert "Senior Distributed Systems Engineer" in payload.body


@pytest.mark.asyncio
async def test_intake_paste_endpoint(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    extracted = ExtractedEmailInfo(
        company="Datadog",
        position="Core Services Engineer",
        email_type="JOB_APPLICATION",
        event_type="APPLICATION_SUBMITTED",
        status="APPLIED",
        summary="Application submitted to Datadog.",
        action_required=False,
        action=None,
    )

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = extracted

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/intake/paste",
                json={
                    "text": "Thank you for applying to Datadog as Core Services Engineer!",
                    "subject": "Datadog Application Received",
                },
            )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["route"] == "commit"
        assert data["company"] == "Datadog"
        assert data["position"] == "Core Services Engineer"
        assert data["application_id"] is not None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_intake_upload_endpoint(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    extracted = ExtractedEmailInfo(
        company="Palantir",
        position="Forward Deployed Engineer",
        email_type="JOB_APPLICATION",
        event_type="APPLICATION_SUBMITTED",
        status="APPLIED",
        summary="Applied to Palantir.",
        action_required=False,
        action=None,
    )

    sample_eml = b"""From: recruiting@palantir.com
Subject: We received your application - Palantir
Date: Fri, 15 Aug 2026 12:00:00 +0000
Message-ID: <msg-palantir-888@palantir.com>
Content-Type: text/plain; charset="utf-8"

Thanks for applying to Palantir for Forward Deployed Engineer."""

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = extracted

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            files = [
                ("files", ("palantir.eml", io.BytesIO(sample_eml), "message/rfc822")),
            ]
            res = await ac.post(
                "/api/v1/intake/upload",
                files=files,
            )

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["status"] == "success"
        assert data[0]["company"] == "Palantir"
        assert data[0]["position"] == "Forward Deployed Engineer"

    app.dependency_overrides.clear()
