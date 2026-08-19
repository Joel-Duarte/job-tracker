import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel


@pytest.mark.asyncio
async def test_search_companies_endpoint(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    company = CompanyModel(
        name="Acme Corp Test", name_normalized="acme corp test", domain="acme.test"
    )
    db_session.add(company)
    await db_session.flush()

    app1 = ApplicationModel(
        company_id=company.id,
        position="Software Engineer",
        status="APPLIED",
    )
    db_session.add(app1)
    await db_session.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/search/companies?q=Acme")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        found = [c for c in data if c["id"] == company.id]
        assert len(found) == 1
        assert found[0]["name"] == "Acme Corp Test"
        assert found[0]["applications_count"] == 1
