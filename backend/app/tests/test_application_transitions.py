import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationEventModel, ApplicationModel, CompanyModel, JobPostingModel


@pytest.mark.asyncio
async def test_application_transitions_and_deletion(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    # 1. Seed Company and Application
    company = CompanyModel(name="Linear Labs", name_normalized="linear labs", domain="linear.app")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Backend Engineer",
        position_normalized="senior backend engineer",
        status="APPLIED",
        application_key="linear-backend-101",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Transition to TECHNICAL_INTERVIEW with interview stage and scheduled_at
        with patch("app.routers.applications.async_enqueue_application_embedding", new_callable=AsyncMock):
            resp = await client.post(
                f"/api/v1/applications/{application.id}/transition",
                json={
                    "status": "TECHNICAL_INTERVIEW",
                    "interview_stage": "System Design / Live Coding",
                    "scheduled_at": "2026-08-20T14:30:00Z",
                    "notes": "Met with hiring manager, scheduling system design next week.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "TECHNICAL_INTERVIEW"
            assert data["latest_event"] is not None
            assert data["latest_event"]["email_event_type"] == "STATUS_CHANGE"

        # 3. Transition to OFFER with offered salary, offer_received_date, and decision_deadline
        with patch("app.routers.applications.async_enqueue_application_embedding", new_callable=AsyncMock):
            resp = await client.post(
                f"/api/v1/applications/{application.id}/transition",
                json={
                    "status": "OFFER",
                    "offered_salary": 210000,
                    "currency": "USD",
                    "offer_received_date": "2026-08-25",
                    "decision_deadline": "2026-09-01",
                    "notes": "Official offer package received.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "OFFER"

        # Check job_posting in DB was updated with salary
        jp_stmt = select(JobPostingModel).where(JobPostingModel.application_id == application.id)
        jp_res = await db_session.execute(jp_stmt)
        jp = jp_res.scalar_one_or_none()
        assert jp is not None
        assert jp.salary_min == 210000

        # 4. Transition to REJECTED with rejection reason and rejection_date
        with patch("app.routers.applications.async_enqueue_application_embedding", new_callable=AsyncMock):
            resp = await client.post(
                f"/api/v1/applications/{application.id}/transition",
                json={
                    "status": "REJECTED",
                    "rejection_reason": "Offer Declined by Candidate",
                    "rejection_date": "2026-09-02",
                    "notes": "Declined offer due to competing role.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "REJECTED"

        # 5. Verify timeline events count in DB
        events_stmt = select(ApplicationEventModel).where(ApplicationEventModel.email_application_id == application.id)
        events_res = await db_session.execute(events_stmt)
        events = events_res.scalars().all()
        assert len(events) == 3

        # 6. Delete application
        del_resp = await client.delete(f"/api/v1/applications/{application.id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"

        # Verify application and events are deleted from DB
        app_stmt = select(ApplicationModel).where(ApplicationModel.id == application.id)
        app_res = await db_session.execute(app_stmt)
        assert app_res.scalar_one_or_none() is None

        # Verify application and events are deleted from DB
        app_stmt = select(ApplicationModel).where(ApplicationModel.id == application.id)
        app_res = await db_session.execute(app_stmt)
        assert app_res.scalar_one_or_none() is None
