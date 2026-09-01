import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.applications import ActionItemModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel


@pytest.mark.asyncio
async def test_get_system_badges_counts(db_session):
    # Seed staging item
    staging = StagingItemModel(
        email_subject="Test Interview Request",
        email_raw_body="Job posting test body",
        status="PENDING",
    )
    db_session.add(staging)

    # Seed pending action item
    action = ActionItemModel(
        title="Follow up interview",
        status="PENDING",
    )
    db_session.add(action)

    # Seed active evaluation task and completed task
    active_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        status="PROCESSING",
        title_hint="Backend Dev",
        raw_text="Job posting text",
    )
    completed_task = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        status="COMPLETED",
        title_hint="Frontend Dev",
        raw_text="Job posting text",
    )
    db_session.add_all([active_task, completed_task])
    await db_session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/api/v1/system/badges")
        assert res.status_code == 200
        data = res.json()
        assert data["staging_count"] >= 1
        assert data["pending_action_items_count"] >= 1
        assert data["active_queue_tasks_count"] >= 1
