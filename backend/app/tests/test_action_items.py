from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel


@pytest.mark.asyncio
async def test_action_items_crud_and_filtering(db_session):
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a company and application
        company = CompanyModel(
            name="Linear Orbit Inc.",
            name_normalized="linear orbit inc.",
            domain="linearorbit.io",
        )
        db_session.add(company)
        await db_session.flush()
        await db_session.commit()
        await db_session.refresh(company)

        application = ApplicationModel(
            company_id=company.id,
            position="Staff Distributed Systems Engineer",
            position_normalized="staff distributed systems engineer",
            status="TECHNICAL_INTERVIEW",
            application_key="linear-staff-sys",
        )
        db_session.add(application)
        await db_session.commit()
        await db_session.refresh(application)

        # 2. Create Action Items via POST
        create_payload_1 = {
            "application_id": application.id,
            "title": "Prepare system design diagrams for Linear architecture round",
            "due_date": datetime(2026, 8, 22, 14, 0, tzinfo=timezone.utc).isoformat(),
            "urgency": "HIGH",
            "status": "PENDING",
        }
        res1 = await ac.post("/api/v1/action-items", json=create_payload_1)
        assert res1.status_code == 201
        data1 = res1.json()
        assert data1["title"] == create_payload_1["title"]
        assert data1["urgency"] == "HIGH"
        assert data1["company_name"] == "Linear Orbit Inc."
        assert data1["position"] == "Staff Distributed Systems Engineer"
        item1_id = data1["id"]

        create_payload_2 = {
            "application_id": application.id,
            "title": "Follow up with recruiter regarding next steps",
            "urgency": "MEDIUM",
            "status": "PENDING",
        }
        res2 = await ac.post("/api/v1/action-items", json=create_payload_2)
        assert res2.status_code == 201
        item2_id = res2.json()["id"]

        # 3. List Action Items & verify metrics
        list_res = await ac.get("/api/v1/action-items")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 2
        assert list_data["pending_count"] >= 2
        assert list_data["high_urgency_count"] >= 1

        # 4. Filter by urgency=HIGH
        high_res = await ac.get("/api/v1/action-items?urgency=HIGH")
        assert high_res.status_code == 200
        high_data = high_res.json()
        assert all(item["urgency"] == "HIGH" for item in high_data["items"])

        # 5. Patch Action Item to COMPLETED
        patch_res = await ac.patch(
            f"/api/v1/action-items/{item1_id}",
            json={"status": "COMPLETED"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "COMPLETED"

        # Verify completed count incremented
        list_res_after = await ac.get("/api/v1/action-items")
        assert list_res_after.json()["completed_count"] >= 1

        # 6. Delete Action Item
        del_res = await ac.delete(f"/api/v1/action-items/{item2_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "success"

        # Verify 404 on deleting already deleted item
        del_res_404 = await ac.delete(f"/api/v1/action-items/{item2_id}")
        assert del_res_404.status_code == 404
