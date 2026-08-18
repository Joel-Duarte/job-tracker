from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.services.staleness_archiver import archive_stale_applications


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_archive_stale_applications_transitions_inactive_apps(
    db_session: AsyncSession,
):
    # Setup company
    company = CompanyModel(name="Mock Company", name_normalized="mock company")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    # Setup app
    app_date = datetime.now(UTC) - timedelta(days=35)
    app = ApplicationModel(
        company_id=company.id,
        position="Software Engineer",
        status="APPLIED",
        last_activity_at=app_date,
        application_date=app_date,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Add pending action item
    action_item = ActionItemModel(
        application_id=app.id, title="Follow up", status="PENDING"
    )
    db_session.add(action_item)
    await db_session.commit()

    # Execute
    stats = await archive_stale_applications(db_session, threshold_days=30)

    # Verify
    assert stats["archived_count"] == 1
    assert app.id in stats["archived_ids"]

    await db_session.refresh(app)
    assert app.status == "ARCHIVED"
    assert app.last_activity_at > app_date  # Should be updated to now

    # Verify event created
    events = await db_session.execute(
        select(ApplicationEventModel).where(
            ApplicationEventModel.email_application_id == app.id
        )
    )
    event_list = events.scalars().all()
    assert len(event_list) == 1
    assert event_list[0].email_event_type == "STATUS_CHANGE"
    assert event_list[0].email_status_after_event == "ARCHIVED"
    assert event_list[0].source_channel == "SYSTEM"

    # Verify action items dismissed
    await db_session.refresh(action_item)
    assert action_item.status == "DISMISSED"


@pytest.mark.asyncio
async def test_archive_stale_applications_ignores_recent_apps(db_session: AsyncSession):
    # Setup company
    company = CompanyModel(name="Mock Company 2", name_normalized="mock company 2")
    db_session.add(company)
    await db_session.commit()

    # Setup app
    app_date = datetime.now(UTC) - timedelta(days=5)
    app = ApplicationModel(
        company_id=company.id,
        position="Software Engineer",
        status="APPLIED",
        last_activity_at=app_date,
        application_date=app_date,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Execute
    stats = await archive_stale_applications(db_session, threshold_days=30)

    # Verify
    assert stats["archived_count"] == 0
    await db_session.refresh(app)
    assert app.status == "APPLIED"


@pytest.mark.asyncio
async def test_archive_stale_applications_archives_stale_interviews(
    db_session: AsyncSession,
):
    # Setup company
    company = CompanyModel(name="Mock Company 3", name_normalized="mock company 3")
    db_session.add(company)
    await db_session.commit()

    # Setup app
    app_date = datetime.now(UTC) - timedelta(days=45)
    app = ApplicationModel(
        company_id=company.id,
        position="Software Engineer",
        status="TECHNICAL_INTERVIEW",
        last_activity_at=app_date,
        application_date=app_date,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Execute
    stats = await archive_stale_applications(db_session, threshold_days=30)

    # Verify
    assert stats["archived_count"] == 1
    await db_session.refresh(app)
    assert app.status == "ARCHIVED"


@pytest.mark.asyncio
async def test_admin_run_auto_archiver_endpoint(
    db_session: AsyncSession, async_client: AsyncClient
):
    # Setup company
    company = CompanyModel(name="Mock Company 4", name_normalized="mock company 4")
    db_session.add(company)
    await db_session.commit()

    app_date = datetime.now(UTC) - timedelta(days=35)
    app = ApplicationModel(
        company_id=company.id,
        position="Data Scientist",
        status="APPLIED",
        last_activity_at=app_date,
        application_date=app_date,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    # Call endpoint
    response = await async_client.post(
        "/api/v1/admin/run-auto-archiver?threshold_days=30"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["archived_count"] == 1
    assert app.id in data["archived_ids"]


@pytest.mark.asyncio
async def test_archive_stale_applications_ignores_terminal_statuses(
    db_session: AsyncSession,
):
    company = CompanyModel(name="Mock Company 5", name_normalized="mock company 5")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    old_date = datetime.now(UTC) - timedelta(days=90)
    for terminal in ("HIRED", "ARCHIVED", "WITHDRAWN", "REJECTED"):
        app = ApplicationModel(
            company_id=company.id,
            position=f"Engineer ({terminal})",
            status=terminal,
            last_activity_at=old_date,
            application_date=old_date,
        )
        db_session.add(app)
    await db_session.commit()

    stats = await archive_stale_applications(db_session, threshold_days=30)
    assert stats["archived_count"] == 0
