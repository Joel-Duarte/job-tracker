import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_bulk_transition_archives_open_applications(
    db_session: AsyncSession, async_client: AsyncClient
):
    company = CompanyModel(name="BulkCo", name_normalized="bulkco")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app_applied = ApplicationModel(
        company_id=company.id, position="Role A", status="APPLIED"
    )
    app_interview = ApplicationModel(
        company_id=company.id, position="Role B", status="TECHNICAL_INTERVIEW"
    )
    app_offer = ApplicationModel(
        company_id=company.id, position="Role C", status="OFFER"
    )
    app_hired = ApplicationModel(
        company_id=company.id, position="Role D", status="HIRED"
    )
    for a in [app_applied, app_interview, app_offer, app_hired]:
        db_session.add(a)
    await db_session.commit()
    for a in [app_applied, app_interview, app_offer, app_hired]:
        await db_session.refresh(a)

    response = await async_client.post(
        "/api/v1/applications/bulk-transition",
        json={
            "target_status": "ARCHIVED",
            "from_statuses": ["APPLIED", "TECHNICAL_INTERVIEW", "OFFER"],
            "exclude_ids": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 3
    assert app_hired.id not in data["updated_ids"]

    await db_session.refresh(app_applied)
    assert app_applied.status == "ARCHIVED"
    await db_session.refresh(app_hired)
    assert app_hired.status == "HIRED"  # untouched


@pytest.mark.asyncio
async def test_bulk_transition_respects_exclude_ids(
    db_session: AsyncSession, async_client: AsyncClient
):
    company = CompanyModel(name="BulkCo2", name_normalized="bulkco2")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    keep = ApplicationModel(company_id=company.id, position="Keep Me", status="APPLIED")
    archive = ApplicationModel(
        company_id=company.id, position="Archive Me", status="APPLIED"
    )
    db_session.add(keep)
    db_session.add(archive)
    await db_session.commit()
    await db_session.refresh(keep)
    await db_session.refresh(archive)

    response = await async_client.post(
        "/api/v1/applications/bulk-transition",
        json={
            "target_status": "ARCHIVED",
            "from_statuses": ["APPLIED"],
            "exclude_ids": [keep.id],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert keep.id not in data["updated_ids"]
    assert archive.id in data["updated_ids"]


@pytest.mark.asyncio
async def test_bulk_transition_creates_timeline_events(
    db_session: AsyncSession, async_client: AsyncClient
):
    company = CompanyModel(name="BulkCo3", name_normalized="bulkco3")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = ApplicationModel(company_id=company.id, position="Role X", status="APPLIED")
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    response = await async_client.post(
        "/api/v1/applications/bulk-transition",
        json={
            "target_status": "ARCHIVED",
            "from_statuses": ["APPLIED"],
            "exclude_ids": [],
            "notes": "Archived — position filled elsewhere.",
        },
    )

    assert response.status_code == 200
    from sqlalchemy import select

    events = await db_session.execute(
        select(ApplicationEventModel).where(
            ApplicationEventModel.email_application_id == app.id
        )
    )
    event_list = events.scalars().all()
    assert len(event_list) >= 1
    assert any(e.email_event_type == "STATUS_CHANGE" for e in event_list)
    assert any(e.email_status_after_event == "ARCHIVED" for e in event_list)


@pytest.mark.asyncio
async def test_bulk_transition_dismisses_pending_action_items_on_terminal(
    db_session: AsyncSession, async_client: AsyncClient
):
    from app.models.applications import ActionItemModel

    company = CompanyModel(name="BulkCo4", name_normalized="bulkco4")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = ApplicationModel(company_id=company.id, position="Role Y", status="APPLIED")
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    ai = ActionItemModel(
        application_id=app.id,
        title="Follow up on application",
        status="PENDING",
    )
    db_session.add(ai)
    await db_session.commit()
    await db_session.refresh(ai)

    response = await async_client.post(
        "/api/v1/applications/bulk-transition",
        json={
            "target_status": "ARCHIVED",
            "from_statuses": ["APPLIED"],
            "exclude_ids": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert app.id in data["updated_ids"]

    await db_session.refresh(ai)
    assert ai.status == "DISMISSED"


@pytest.mark.asyncio
async def test_bulk_transition_ignores_terminal_from_statuses(
    db_session: AsyncSession, async_client: AsyncClient
):
    company = CompanyModel(name="BulkCo5", name_normalized="bulkco5")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app_hired = ApplicationModel(
        company_id=company.id, position="Role Z", status="HIRED"
    )
    db_session.add(app_hired)
    await db_session.commit()
    await db_session.refresh(app_hired)

    response = await async_client.post(
        "/api/v1/applications/bulk-transition",
        json={
            "target_status": "ARCHIVED",
            "from_statuses": ["HIRED", "REJECTED", "WITHDRAWN", "ARCHIVED"],
            "exclude_ids": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["updated_count"] == 0
    assert data["updated_ids"] == []

    await db_session.refresh(app_hired)
    assert app_hired.status == "HIRED"
