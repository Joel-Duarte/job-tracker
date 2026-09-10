from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.agent_tools import (
    create_agent_tools,
    execute_analyze_pipeline_metrics,
    execute_bulk_transition_applications,
    execute_detect_stalled_applications,
    execute_enqueue_application_questions,
    execute_enqueue_company_research,
    execute_enqueue_cover_letter_generation,
    execute_evaluate_ai_fit_score,
    execute_get_application_questions,
    execute_get_candidate_profile,
    execute_get_company_details,
    execute_get_cover_letter,
    execute_get_mock_interview_history,
    execute_get_role_alignment_dossier,
    execute_get_upcoming_interviews,
    execute_list_applications,
    execute_list_companies,
    execute_manage_action_items,
    execute_manage_intake_queue,
    execute_query_market_benchmarks,
    execute_semantic_vector_search,
    execute_start_mock_interview,
    execute_update_application_pipeline,
    execute_update_company_notes,
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
    mock_company = CompanyModel(
        id=1,
        name="Acme Inc",
        name_normalized="acme inc",
        domain="acme.com",
        notes="Target employer",
        pros=["Culture"],
        red_flags=["Comp"],
        rating=4,
        company_research={"summary": "Fast-growing SaaS startup."},
    )
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

    # 8. Test start_mock_interview with persona
    with patch(
        "app.services.agent_tools.InterviewSimulatorService.start_session",
        new_callable=AsyncMock,
    ) as mock_start_session:
        mock_sim_session = MagicMock()
        mock_sim_session.id = 42
        mock_sim_session.question_mode = "TEXT_CONVERSATIONAL"
        mock_sim_session.turns_data = [
            {"question": "Describe your distributed architecture experience."}
        ]
        mock_start_session.return_value = mock_sim_session

        start_res = await execute_start_mock_interview(
            db,
            company_or_id="Acme Inc",
            question_mode="TEXT_CONVERSATIONAL",
            interviewer_persona="HIRING_MANAGER",
        )
        assert start_res["status"] == "started"
        assert start_res["session_id"] == 42
        assert start_res["interviewer_persona"] == "HIRING_MANAGER"
        assert "distributed architecture" in start_res["first_question"]

    # 9. Test get_company_details
    with patch(
        "app.services.agent_tools._resolve_company",
        new_callable=AsyncMock,
        return_value=mock_company,
    ):
        mock_app_list_res = MagicMock()
        mock_app_list_res.scalars().all.return_value = [mock_app]
        db.execute.return_value = mock_app_list_res

        comp_details = await execute_get_company_details(db, "Acme Inc")
        assert comp_details["status"] == "success"
        assert comp_details["name"] == "Acme Inc"
        assert comp_details["domain"] == "acme.com"
        assert comp_details["candidate_rating"] == 4
        assert "summary" in comp_details["company_research"]
        assert comp_details["applications_count"] == 1

    # 10. Test list_companies
    mock_company.applications = [mock_app]
    mock_companies_res = MagicMock()
    mock_companies_res.scalars().all.return_value = [mock_company]
    db.execute.return_value = mock_companies_res

    comp_list = await execute_list_companies(db, has_research=True, limit=10)
    assert len(comp_list) == 1
    assert comp_list[0]["name"] == "Acme Inc"
    assert comp_list[0]["has_research"] is True

    # 11. Test update_company_notes
    with patch(
        "app.services.agent_tools._resolve_company",
        new_callable=AsyncMock,
        return_value=mock_company,
    ):
        up_notes_res = await execute_update_company_notes(
            db,
            company_or_id="Acme Inc",
            notes="New candidate notes",
            rating=5,
        )
        assert up_notes_res["status"] == "success"
        assert mock_company.notes == "New candidate notes"
        assert mock_company.rating == 5

    def mock_create_task(coro):
        coro.close()
        return MagicMock()

    # 12. Test enqueue_company_research
    with (
        patch(
            "app.services.agent_tools._resolve_company",
            new_callable=AsyncMock,
            return_value=mock_company,
        ),
        patch(
            "asyncio.create_task", side_effect=mock_create_task
        ) as mock_create_task_spy,
    ):
        mock_no_task_res = MagicMock()
        mock_no_task_res.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_no_task_res

        q_res = await execute_enqueue_company_research(db, "Acme Inc")
        assert q_res["status"] == "queued"
        assert "task_id" in q_res
        assert mock_company.research_status == "QUEUED"
        mock_create_task_spy.assert_called_once()

    # 13. Test get_mock_interview_history
    mock_hist_session = MagicMock()
    mock_hist_session.id = 101
    mock_hist_session.application_id = 1
    mock_hist_session.status = "COMPLETED"
    mock_hist_session.persona = "TECHNICAL_BAR_RAISER"
    mock_hist_session.question_mode = "TEXT_CONVERSATIONAL"
    mock_hist_session.overall_score = 85
    mock_hist_session.readiness_rating = "STRONG_HIRE"
    mock_hist_session.summary_feedback = "Strong architectural understanding."
    mock_hist_session.turns_data = [{"q": "test"}]
    mock_hist_session.created_at = datetime.now(UTC)

    mock_sess_res = MagicMock()
    mock_sess_res.scalars().all.return_value = [mock_hist_session]
    db.execute.return_value = mock_sess_res

    history = await execute_get_mock_interview_history(db, limit=5, application_id=1)
    assert len(history) == 1
    assert history[0]["session_id"] == 101
    assert history[0]["readiness_rating"] == "STRONG_HIRE"

    # 14. Test get_cover_letter and enqueue_cover_letter_generation
    mock_app.cover_letter_text = "Dear Hiring Team..."
    mock_app.cover_letter_status = "GENERATED"
    mock_app.cover_letter_generated_at = datetime.now(UTC)
    mock_app_res = MagicMock()
    mock_app_res.scalar_one_or_none.return_value = mock_app
    db.execute.return_value = mock_app_res

    cl_data = await execute_get_cover_letter(db, application_id=1)
    assert cl_data["status"] == "success"
    assert cl_data["cover_letter_status"] == "GENERATED"
    assert "Dear Hiring Team" in cl_data["cover_letter_text"]

    with patch("asyncio.create_task", side_effect=mock_create_task) as mock_task_cl:
        q_cl = await execute_enqueue_cover_letter_generation(
            db, application_id=1, tone="enthusiastic", length="concise"
        )
        assert q_cl["status"] == "queued"
        assert mock_app.cover_letter_status == "DRAFTED"
        mock_task_cl.assert_called_once()

    # 15. Test get_application_questions and enqueue_application_questions
    mock_app.application_questions = [
        {
            "id": "q_1",
            "question": "Why Acme?",
            "answer": "Great mission.",
            "status": "GENERATED",
        }
    ]
    db.execute.return_value = mock_app_res

    qa_data = await execute_get_application_questions(db, application_id=1)
    assert qa_data["status"] == "success"
    assert qa_data["questions_count"] == 1

    with patch("asyncio.create_task", side_effect=mock_create_task) as mock_task_qa:
        q_qa = await execute_enqueue_application_questions(
            db, application_id=1, questions=["Why us?", "Tell me about a bug."]
        )
        assert q_qa["status"] == "queued"
        assert q_qa["questions_count"] == 2
        mock_task_qa.assert_called_once()

    # 16. Test get_role_alignment_dossier
    mock_dossier = MagicMock()
    mock_dossier.id = 7
    mock_dossier.role_track = "Staff Distributed Systems Engineer"
    mock_dossier.executive_positioning = {"headline": "Staff Engineer"}
    mock_dossier.bullet_rewrites = [{"original": "x", "rewritten": "y"}]
    mock_dossier.interview_talking_points = ["Talking point 1"]
    mock_dossier.skill_bridge_roadmap = ["Rust"]
    mock_dossier.generated_at = datetime.now(UTC)

    with patch(
        "app.services.role_alignment_dossier_service.get_role_alignment_dossier",
        new_callable=AsyncMock,
        return_value=mock_dossier,
    ):
        dossier_res = await execute_get_role_alignment_dossier(db, role_track="Staff")
        assert dossier_res["status"] == "success"
        assert dossier_res["role_track"] == "Staff Distributed Systems Engineer"
        assert len(dossier_res["bullet_rewrites"]) == 1

    # 17. Test get_candidate_profile
    mock_cv = CandidateCVModel(
        id=1,
        summary="Experienced distributed engineer",
        years_of_experience=10.5,
        extracted_skills=["Python", "Go", "Postgres"],
        domain_expertise=["Distributed Systems"],
        domain_experience=[{"domain": "Backend", "years": 8}],
        spoken_languages=[{"language": "English", "proficiency": "Native"}],
        raw_text="Full resume text...",
    )
    mock_cv_res = MagicMock()
    mock_cv_res.scalar_one_or_none.return_value = mock_cv
    db.execute.return_value = mock_cv_res

    profile_skills = await execute_get_candidate_profile(db, section="skills")
    assert profile_skills["years_of_experience"] == 10.5
    assert "Python" in profile_skills["extracted_skills"]

    profile_all = await execute_get_candidate_profile(db, section="all")
    assert profile_all["summary"] == "Experienced distributed engineer"

    # 18. Test bulk_transition_applications
    mock_app_applied = ApplicationModel(id=101, status="APPLIED")
    mock_app_interview = ApplicationModel(id=102, status="TECHNICAL_INTERVIEW")
    mock_bulk_res = MagicMock()
    mock_bulk_res.scalars().all.return_value = [mock_app_applied, mock_app_interview]

    mock_empty_ai = MagicMock()
    mock_empty_ai.scalars().all.return_value = []
    db.execute.side_effect = [mock_bulk_res, mock_empty_ai, mock_empty_ai]

    bulk_res = await execute_bulk_transition_applications(
        db, target_status="WITHDRAWN", reason="Offer accepted elsewhere"
    )
    assert bulk_res["status"] == "success"
    assert bulk_res["updated_count"] == 2
    assert mock_app_applied.status == "WITHDRAWN"
    assert mock_app_interview.status == "WITHDRAWN"

    # 19. Test list_applications active & assessment filtering
    mock_app_act = ApplicationModel(
        id=201,
        status="APPLIED",
        is_assessment=False,
        company=CompanyModel(name="Linear"),
        action_items=[],
        events=[],
    )
    mock_res_apps = MagicMock()
    mock_res_apps.scalars().all.return_value = [mock_app_act]
    db.execute.side_effect = None
    db.execute.return_value = mock_res_apps
    apps_list = await execute_list_applications(
        db, status="ACTIVE", include_assessments=False
    )
    assert len(apps_list) == 1
    assert apps_list[0]["company"] == "Linear"

    # 20. Test get_upcoming_interviews
    sched_time = datetime.now(UTC) + timedelta(days=2)
    mock_app_interview_sched = ApplicationModel(
        id=301,
        status="TECHNICAL_INTERVIEW",
        is_assessment=False,
        company=CompanyModel(name="Stripe"),
        position="Staff Engineer",
        action_items=[],
        events=[
            ApplicationEventModel(
                raw_payload={
                    "scheduled_at": sched_time.isoformat(),
                    "interview_stage": "System Architecture",
                }
            )
        ],
    )
    mock_app_interview_pending = ApplicationModel(
        id=302,
        status="TECHNICAL_INTERVIEW",
        is_assessment=False,
        company=CompanyModel(name="Datadog"),
        position="Backend Engineer",
        action_items=[],
        events=[
            ApplicationEventModel(
                raw_payload={"interview_stage": "Task Completed / Awaiting Response"}
            )
        ],
    )
    mock_interview_res = MagicMock()
    mock_interview_res.scalars().all.return_value = [
        mock_app_interview_sched,
        mock_app_interview_pending,
    ]
    db.execute.return_value = mock_interview_res

    interviews_res = await execute_get_upcoming_interviews(db, days_ahead=14)
    assert interviews_res["total_confirmed_interviews"] == 1
    assert interviews_res["confirmed_interviews"][0]["company"] == "Stripe"
    assert (
        "System Architecture"
        in interviews_res["confirmed_interviews"][0]["interview_stage"]
    )
    assert len(interviews_res["awaiting_scheduling_or_response"]) == 1
    assert interviews_res["awaiting_scheduling_or_response"][0]["company"] == "Datadog"
    assert (
        interviews_res["awaiting_scheduling_or_response"][0]["state"]
        == "awaiting_recruiter_reply"
    )

    # 21. Test semantic_vector_search fallback when embeddings are disabled
    with patch(
        "app.core.config_manager.get_setting",
        new_callable=AsyncMock,
        return_value=False,
    ):
        mock_search_res = MagicMock()
        mock_search_res.scalars().all.return_value = [mock_app_act]
        db.execute.return_value = mock_search_res
        search_res = await execute_semantic_vector_search(db, query="Linear backend")
        assert len(search_res) == 1
        assert search_res[0]["embeddings_enabled"] is False
        assert search_res[0]["search_mode"] == "keyword_search"

    # 22. Test LangChain Tool Factory Registration
    tools = create_agent_tools(db, enable_web_search=False)
    tool_names = [t.name for t in tools]
    assert len(tools) == 24
    assert "analyze_pipeline_metrics" in tool_names
    assert "detect_stalled_applications" in tool_names
    assert "start_mock_interview" in tool_names
    assert "get_mock_interview_history" in tool_names
    assert "get_candidate_profile" in tool_names
    assert "get_company_details" in tool_names
    assert "list_companies" in tool_names
    assert "update_company_notes" in tool_names
    assert "enqueue_company_research" in tool_names
    assert "get_cover_letter" in tool_names
    assert "enqueue_cover_letter_generation" in tool_names
    assert "get_application_questions" in tool_names
    assert "enqueue_application_questions" in tool_names
    assert "get_role_alignment_dossier" in tool_names
    assert "bulk_transition_applications" in tool_names
    assert "get_upcoming_interviews" in tool_names

    # With web search enabled:
    tools_web = create_agent_tools(db, enable_web_search=True)
    assert len(tools_web) == 26
    web_tool_names = [t.name for t in tools_web]
    assert "search_web" in web_tool_names
    assert "fetch_webpage_content" in web_tool_names
