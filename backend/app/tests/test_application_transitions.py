from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)


@pytest.mark.asyncio
async def test_application_transitions_and_deletion(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    # 1. Seed Company and Application
    company = CompanyModel(
        name="Linear Labs", name_normalized="linear labs", domain="linear.app"
    )
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
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
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

        # 2b. Transition to Task Completed / Awaiting Response -> auto-completes action items
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/applications/{application.id}/transition",
                json={
                    "status": "TECHNICAL_INTERVIEW",
                    "interview_stage": "Task Completed / Awaiting Response",
                    "notes": "Finished take-home challenge, sent to recruiter.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "TECHNICAL_INTERVIEW"
            assert data["latest_event"]["raw_payload"].get("scheduled_at") is None
            assert data["scheduled_interview_at"] is None

        # 3. Transition to OFFER with offered salary, offer_received_date, and decision_deadline
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
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
        jp_stmt = select(JobPostingModel).where(
            JobPostingModel.application_id == application.id
        )
        jp_res = await db_session.execute(jp_stmt)
        jp = jp_res.scalar_one_or_none()
        assert jp is not None
        assert jp.salary_min == 210000

        # 4. Transition to REJECTED with rejection reason and rejection_date
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
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
        events_stmt = select(ApplicationEventModel).where(
            ApplicationEventModel.email_application_id == application.id
        )
        events_res = await db_session.execute(events_stmt)
        events = events_res.scalars().all()
        assert len(events) == 4

        # 6. Delete application
        del_resp = await client.delete(f"/api/v1/applications/{application.id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"

        # Verify application and events are deleted from DB
        app_stmt = select(ApplicationModel).where(ApplicationModel.id == application.id)
        app_res = await db_session.execute(app_stmt)
        assert app_res.scalar_one_or_none() is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_application_patch_updates(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(
        name="Acme Corp", name_normalized="acme corp", domain="acme.com"
    )
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Frontend Developer",
        position_normalized="frontend developer",
        status="APPLIED",
        application_key="acme-dev-101",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
            resp = await client.patch(
                f"/api/v1/applications/{application.id}",
                json={
                    "position": "Staff Frontend Architect",
                    "company_name": "Acme Global Technologies",
                    "company_domain": "https://www.acmeglobal.com/careers",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["position"] == "Staff Frontend Architect"
            assert data["company"]["name"] == "Acme Global Technologies"
            assert data["company"]["domain"] == "acmeglobal.com"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_activity_logging_preserves_task_completion(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    company = CompanyModel(
        name="TestCorp", name_normalized="testcorp", domain="testcorp.com"
    )
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Backend Engineer",
        position_normalized="backend engineer",
        status="TECHNICAL_INTERVIEW",
        application_key="testcorp-101",
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Complete take-home task
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/applications/{application.id}/transition",
                json={
                    "status": "TECHNICAL_INTERVIEW",
                    "interview_stage": "Task Completed / Awaiting Response",
                    "notes": "Submitted coding challenge.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["scheduled_interview_at"] is None
            assert data["has_action_required"] is False

        # 2. Log activity / general note on the application
        with patch(
            "app.routers.applications.async_enqueue_application_embedding",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                f"/api/v1/applications/{application.id}/transition",
                json={
                    "status": "TECHNICAL_INTERVIEW",
                    "event_type": "CUSTOM_NOTE",
                    "notes": "Sent a follow-up email to recruiter.",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            # Must NOT reactivate scheduled interview or create duplicate pending action items!
            assert data["scheduled_interview_at"] is None
            assert data["has_action_required"] is False
            assert data["latest_event"]["email_event_type"] == "CUSTOM_NOTE"
            assert len(data["events"]) == 2
            assert data["events"][0]["email_event_type"] == "CUSTOM_NOTE"
            assert "Status changed" not in (data["events"][0]["email_summary"] or "")
            assert "Sent a follow-up email to recruiter." in (
                data["events"][0]["email_summary"] or ""
            )

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_badges_cache_invalidation_fields(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/system/badges")
        assert resp.status_code == 200
        data = resp.json()
        assert "staging_count" in data
        assert "pending_action_items_count" in data
        assert "active_queue_tasks_count" in data
        assert "total_applications_count" in data
        assert "latest_activity_at" in data

    app.dependency_overrides.clear()
