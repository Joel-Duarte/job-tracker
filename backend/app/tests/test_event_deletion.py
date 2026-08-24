from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    OtherEventModel,
)


@pytest.mark.asyncio
async def test_delete_application_event(db_session):
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create company and application
        company = CompanyModel(
            name="Stripe Payments",
            name_normalized="stripe payments",
            domain="stripe.com",
        )
        db_session.add(company)
        await db_session.flush()

        application = ApplicationModel(
            company_id=company.id,
            position="Backend Engineer",
            position_normalized="backend engineer",
            status="APPLIED",
        )
        db_session.add(application)
        await db_session.flush()

        # Create application event
        event = ApplicationEventModel(
            email_application_id=application.id,
            email_subject="Invitation to Interview",
            email_event_type="TECHNICAL_INTERVIEW",
            email_sender="recruiter@stripe.com",
            email_received_at=datetime.now(UTC),
            email_raw_body="We would love to schedule a technical round.",
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        # Delete the event
        res = await ac.delete(f"/api/v1/events/{event.id}?source=application")
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        assert res.json()["event_id"] == event.id

        # Verify it's gone
        res_list = await ac.get(f"/api/v1/events/applications/{application.id}")
        assert res_list.status_code == 200
        assert len(res_list.json()) == 0


@pytest.mark.asyncio
async def test_delete_other_event(db_session):
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        other_event = OtherEventModel(
            email_type="NEWSLETTER",
            company="Tech Weekly",
            email_subject="Weekly Digest",
            email_sender="news@techweekly.com",
            email_received_at=datetime.now(UTC),
        )
        db_session.add(other_event)
        await db_session.commit()
        await db_session.refresh(other_event)

        res = await ac.delete(f"/api/v1/events/{other_event.id}?source=other")
        assert res.status_code == 200
        assert res.json()["status"] == "success"
