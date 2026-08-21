from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.applications import (
    ActionItemModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.agent_tools import (
    create_agent_tools,
    execute_analyze_pipeline_metrics,
    execute_detect_stalled_applications,
    execute_evaluate_ai_fit_score,
    execute_manage_action_items,
    execute_manage_intake_queue,
    execute_query_market_benchmarks,
    execute_update_application_pipeline,
)


@pytest.mark.asyncio
async def test_agent_tools_unit_handlers():
    """Unit tests for agent tools execution logic with mocked database session."""
    db = AsyncMock()
    db.add = MagicMock()

    # 1. Test analyze_pipeline_metrics with mock funnel response
    mock_funnel = MagicMock()
    mock_funnel.model_dump.return_value = {
        "period": "weekly",
        "num_periods": 4,
        "funnel_stages": {"intakes": 10, "applications": 8},
    }
    with patch(
        "app.services.agent_tools.get_funnel_performance_metrics",
        new_callable=AsyncMock,
        return_value=mock_funnel,
    ):
        res = await execute_analyze_pipeline_metrics(db, period="weekly", num_periods=4)
        assert res["period"] == "weekly"
        assert res["funnel_stages"]["intakes"] == 10

    # 2. Test detect_stalled_applications
    stalled_date = datetime.now(UTC) - timedelta(days=20)
    mock_company = CompanyModel(id=1, name="Acme Inc", name_normalized="acme inc")
    mock_app = ApplicationModel(
        id=1,
        company=mock_company,
        position="Backend Dev",
        status="APPLIED",
        last_activity_at=stalled_date,
    )
    mock_res = MagicMock()
    mock_res.scalars().all.return_value = [mock_app]
    db.execute.return_value = mock_res

    stalled = await execute_detect_stalled_applications(
        db, inactivity_threshold_days=14, limit=5
    )
    assert len(stalled) == 1
    assert stalled[0]["company"] == "Acme Inc"
    assert stalled[0]["days_inactive"] >= 14

    # 3. Test query_market_benchmarks
    mock_posting = JobPostingModel(
        id=1,
        job_url="https://acme.com/job/1",
        salary_min=120000,
        salary_max=160000,
        currency="USD",
        work_model="remote",
        required_skills=["Python", "FastAPI"],
    )
    mock_postings_res = MagicMock()
    mock_postings_res.scalars().all.return_value = [mock_posting]
    db.execute.return_value = mock_postings_res

    benchmarks = await execute_query_market_benchmarks(
        db, position_keyword="Backend", limit=10
    )
    assert benchmarks["sample_size"] == 1
    assert benchmarks["salary_benchmarks"]["average_min"] == 120000.0

    # 4. Test evaluate_ai_fit_score
    mock_app_fit = ApplicationModel(
        id=10,
        company=mock_company,
        position="Backend Dev",
        status="APPLIED",
        match_analysis_payload={
            "programmatic_match_score": 88.0,
            "fit_score": 90,
            "matching_skills": ["Python"],
            "missing_skills": ["Docker"],
        },
    )
    mock_fit_res = MagicMock()
    mock_fit_res.scalars().first.return_value = mock_app_fit
    db.execute.return_value = mock_fit_res

    fit_data = await execute_evaluate_ai_fit_score(db, company_or_id="10")
    assert fit_data["fit_score"] == 90
    assert "Python" in fit_data["matching_skills"]

    # 5. Test manage_intake_queue
    mock_task = IntakeEvaluationTaskModel(
        id=5,
        task_type="JOB_ASSESSMENT",
        status="FAILED",
        stage="SCRAPING",
        job_url="https://acme.com/job",
        error_message="Error",
    )
    mock_tasks_res = MagicMock()
    mock_tasks_res.scalars().all.return_value = [mock_task]
    db.execute.return_value = mock_tasks_res
    db.get.return_value = mock_task

    queue_list = await execute_manage_intake_queue(db, action="list")
    assert len(queue_list["tasks"]) == 1

    queue_fix = await execute_manage_intake_queue(
        db, action="fix", task_id=5, fix_raw_text="Fixed text"
    )
    assert queue_fix["success"] is True
    assert mock_task.status == "PENDING"

    # 6. Test manage_action_items
    mock_item = ActionItemModel(
        id=2,
        title="Call recruiter",
        urgency="HIGH",
        status="PENDING",
        application=mock_app,
    )
    mock_items_res = MagicMock()
    mock_items_res.scalars().all.return_value = [mock_item]
    db.execute.return_value = mock_items_res
    db.get.return_value = mock_item

    items_list = await execute_manage_action_items(db, action="list")
    assert len(items_list["action_items"]) == 1

    complete_res = await execute_manage_action_items(db, action="complete", item_id=2)
    assert complete_res["success"] is True
    assert mock_item.status == "COMPLETED"

    # 7. Test update_application_pipeline
    db.execute.return_value = mock_fit_res
    with patch(
        "app.services.agent_tools.generate_and_save_application_embedding",
        new_callable=AsyncMock,
    ):
        update_res = await execute_update_application_pipeline(
            db, company_or_id="Acme Inc", new_status="TECHNICAL_INTERVIEW"
        )
        assert update_res["success"] is True
        assert mock_app_fit.status == "TECHNICAL_INTERVIEW"

    # 8. Test LangChain Tool Factory Registration
    tools = create_agent_tools(db)
    tool_names = [t.name for t in tools]
    assert len(tools) == 10
    assert "analyze_pipeline_metrics" in tool_names
    assert "detect_stalled_applications" in tool_names
