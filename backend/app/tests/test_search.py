import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel


@pytest.mark.asyncio
async def test_application_keyword_search_and_disabled_semantic_route(
    db_session: AsyncSession,
):
    app.dependency_overrides[get_db] = lambda: db_session
    company = CompanyModel(name="Datadog", name_normalized="datadog")
    db_session.add(company)
    await db_session.flush()
    db_session.add(
        ApplicationModel(
            company_id=company.id,
            position="Senior Telemetry Engineer",
            position_normalized="senior telemetry engineer",
            status="REJECTED",
        )
    )
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        search = await client.get(
            "/api/v1/search/applications", params={"q": "Datadog"}
        )
        semantic = await client.get("/api/v1/search/semantic", params={"q": "Datadog"})

    assert search.status_code == 200
    assert search.json()[0]["company_name"] == "Datadog"
    assert search.json()[0]["status"] == "REJECTED"
    assert semantic.status_code == 410
    app.dependency_overrides.clear()
