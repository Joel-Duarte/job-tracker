import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import ApplicationModel, CompanyModel
from app.models.interview_session import InterviewSessionModel
from app.services.interview_simulator_service import InterviewSimulatorService


@pytest.mark.asyncio
async def test_start_interview_session(db_session: AsyncSession):
    company = CompanyModel(name="TechCorp", name_normalized="techcorp")
    db_session.add(company)
    await db_session.flush()

    app = ApplicationModel(
        company_id=company.id,
        position="Senior Backend Engineer",
        status="TECHNICAL_INTERVIEW",
    )
    db_session.add(app)
    await db_session.commit()

    session = await InterviewSimulatorService.start_session(
        db=db_session,
        application_id=app.id,
        persona="TECHNICAL_BAR_RAISER",
    )

    assert session.id is not None
    assert session.application_id == app.id
    assert session.persona == "TECHNICAL_BAR_RAISER"
    assert session.status == "IN_PROGRESS"
    assert len(session.turns_data) == 1
    assert session.turns_data[0]["turn_index"] == 1
    assert "question" in session.turns_data[0]


@pytest.mark.asyncio
async def test_decoupled_evaluation_strictness(db_session: AsyncSession):
    session = await InterviewSimulatorService.start_session(
        db=db_session,
        application_id=None,
        persona="HIRING_MANAGER",
    )

    mock_llm_response = AsyncMock()
    mock_llm_response.content = """{
        "score": 85,
        "star_presence": { "situation": true, "task": true, "action": true, "result": true },
        "strengths": ["Strong ownership", "Clear metric impact"],
        "missing_gaps": ["Could describe cross-team collaboration further"],
        "constructive_critique": "Excellent response focusing on delivery and ownership.",
        "exemplar_rewrite": "In my previous position, I spearheaded the database migration resulting in 30% latency reduction..."
    }"""

    with patch("app.services.interview_simulator_service.get_task_chat_model") as mock_get_model:
        mock_model_instance = AsyncMock()
        mock_model_instance.ainvoke.return_value = mock_llm_response
        mock_get_model.return_value = mock_model_instance

        updated_session = await InterviewSimulatorService.evaluate_answer(
            db=db_session,
            session_id=session.id,
            turn_index=1,
            answer_text="At my previous job I led a critical refactoring project that reduced costs by 20%.",
        )

        turns = updated_session.turns_data
        assert len(turns) == 1  # DECOUPLED: Does NOT add a new question during evaluation!
        assert turns[0]["user_answer"] == "At my previous job I led a critical refactoring project that reduced costs by 20%."
        assert turns[0]["evaluation"]["score"] == 85
        assert updated_session.overall_score == 85.0


@pytest.mark.asyncio
async def test_drill_down_generation(db_session: AsyncSession):
    session = await InterviewSimulatorService.start_session(
        db=db_session,
        application_id=None,
        persona="TECHNICAL_BAR_RAISER",
    )

    # First evaluate turn 1
    mock_llm_response = AsyncMock()
    mock_llm_response.content = """{
        "score": 75,
        "star_presence": { "situation": true, "task": true, "action": true, "result": false },
        "strengths": ["Clear situation context"],
        "missing_gaps": ["No mention of Redis cluster partition tolerance"],
        "constructive_critique": "Good explanation of caching.",
        "exemplar_rewrite": "During peak load, I configured Redis replication..."
    }"""

    mock_dd_response = AsyncMock()
    mock_dd_response.content = """{
        "question": "You mentioned cache invalidation — what if Redis cluster nodes lose partition quorum?",
        "question_type": "DRILL_DOWN"
    }"""

    with patch("app.services.interview_simulator_service.get_task_chat_model") as mock_get_model:
        mock_model_instance = AsyncMock()
        mock_model_instance.ainvoke.side_effect = [mock_llm_response, mock_dd_response]
        mock_get_model.return_value = mock_model_instance

        await InterviewSimulatorService.evaluate_answer(
            db=db_session,
            session_id=session.id,
            turn_index=1,
            answer_text="I implemented a Redis caching layer to offload main database reads.",
        )

        updated_session = await InterviewSimulatorService.generate_drill_down(
            db=db_session,
            session_id=session.id,
            turn_index=1,
        )

        turns = updated_session.turns_data
        assert len(turns) == 2
        assert turns[1]["turn_index"] == 2
        assert turns[1]["is_drill_down"] is True
        assert "Redis cluster nodes lose partition quorum" in turns[1]["question"]


@pytest.mark.asyncio
async def test_finalize_session_and_save_notes(db_session: AsyncSession):
    company = CompanyModel(name="Stripe", name_normalized="stripe")
    db_session.add(company)
    await db_session.flush()

    app = ApplicationModel(
        company_id=company.id,
        position="Staff Infrastructure Engineer",
        status="TECHNICAL_INTERVIEW",
    )
    db_session.add(app)
    await db_session.commit()

    session = await InterviewSimulatorService.start_session(
        db=db_session,
        application_id=app.id,
        persona="TECHNICAL_BAR_RAISER",
    )

    # Add evaluated turn
    turns = session.turns_data
    turns[0]["evaluation"] = {
        "score": 90,
        "star_presence": {"situation": True, "task": True, "action": True, "result": True},
        "strengths": ["Deep architectural understanding", "Metric-driven recovery"],
        "missing_gaps": ["Could elaborate on team communication"],
        "constructive_critique": "Outstanding technical depth.",
        "exemplar_rewrite": "Exemplar response...",
    }
    session.turns_data = turns
    session.overall_score = 90.0
    db_session.add(session)
    await db_session.commit()

    finalize_res = await InterviewSimulatorService.finalize_session(
        db=db_session,
        session_id=session.id,
    )

    assert finalize_res["overall_score"] == 90.0
    assert finalize_res["readiness_rating"] == "STRONG_HIRE"
    assert finalize_res["timeline_event_id"] is not None

    # Save notes
    app_with_notes = await InterviewSimulatorService.save_notes(
        db=db_session,
        session_id=session.id,
    )

    assert app_with_notes.notes is not None
    assert "Mock Interview Debrief" in app_with_notes.notes
    assert "STRONG_HIRE" in app_with_notes.notes
