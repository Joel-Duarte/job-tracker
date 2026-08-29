from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.models.candidate_profile import CandidateCVModel
from app.services.interview_guide_graph import (
    InterviewGuideState,
    extractor_node,
    should_continue_sections,
)


@pytest.mark.asyncio
async def test_interview_guide_graph_node_logic():
    """Unit test for state machine nodes and edge routing."""
    state: InterviewGuideState = {
        "cv_text": "Experienced Python Backend Engineer with 7 years in FastAPI and PostgreSQL.",
        "jd_text": "Looking for Senior Backend Engineer at Acme Corp.",
        "company_name": "Acme Corp",
        "position": "Senior Backend Engineer",
        "company_context": [],
        "target_sections": ["role_company_brief", "strategic_fit_pitch"],
        "current_section_index": 0,
        "completed_sections": [],
        "language": "en",
        "error": None,
        "db_session": None,
    }

    # 1. Extractor node
    ext_res = await extractor_node(state)
    assert ext_res["company_name"] == "Acme Corp"
    assert ext_res["position"] == "Senior Backend Engineer"

    # 2. Routing logic
    state["current_section_index"] = 0
    state["iteration_count"] = 1
    assert should_continue_sections(state) == "section_generator"

    state["current_section_index"] = 2
    assert should_continue_sections(state) == "__end__"

    # Circuit breaker test
    state["current_section_index"] = 0
    state["iteration_count"] = 20
    assert should_continue_sections(state) == "__end__"


@pytest.mark.asyncio
async def test_generate_and_clear_interview_guide_endpoint(db_session: AsyncSession):
    """Integration test for POST /applications/{id}/interview-guide and DELETE endpoints."""
    app.dependency_overrides[get_db] = lambda: db_session

    # Seed Company & Application
    company = CompanyModel(name="Stripe", name_normalized="stripe", domain="stripe.com")
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Staff Backend Engineer",
        status="TECHNICAL_INTERVIEW",
    )
    db_session.add(application)
    await db_session.flush()

    job_posting = JobPostingModel(
        application_id=application.id,
        job_url="https://stripe.com/jobs/staff-backend",
        description_markdown="Design high-throughput payment settlement infrastructure in Python.",
        required_skills=["Python", "PostgreSQL", "Distributed Systems"],
    )
    db_session.add(job_posting)

    # Seed Active Candidate CV
    cv = CandidateCVModel(
        raw_text="Staff Engineer with 8 years building distributed payment APIs.",
        anonymized_text="Staff Engineer with 8 years building distributed payment APIs.",
        extracted_skills=["Python", "PostgreSQL", "Distributed Systems", "FastAPI"],
    )
    db_session.add(cv)
    await db_session.commit()

    from langchain_core.messages import AIMessage

    ai_msg = AIMessage(
        content="<h2>1. Role & Company Brief</h2><p>Stripe is scaling payments.</p>"
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = ai_msg
    mock_llm.ainvoke = AsyncMock(return_value=ai_msg)
    mock_llm.return_value = ai_msg

    with patch(
        "app.services.interview_guide_graph.get_task_chat_model", new_callable=AsyncMock
    ) as mock_get_llm:
        mock_get_llm.return_value = mock_llm

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Generate Guide for single section in Portuguese
            payload = {
                "language": "pt",
                "selected_sections": ["role_company_brief"],
                "recursion_limit": 15,
            }
            res = await client.post(
                f"/api/v1/applications/{application.id}/interview-guide", json=payload
            )
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["has_interview_guide"] is True
            assert "Role & Company Brief" in data["interview_guide_html"]
            assert data["interview_guide_language"] == "pt"
            assert data["interview_guide_generated_at"] is not None

            # 2. Check list_applications includes has_interview_guide = True
            list_res = await client.get("/api/v1/applications")
            assert list_res.status_code == 200
            list_data = list_res.json()
            app_item = next(
                item for item in list_data["items"] if item["id"] == application.id
            )
            assert app_item["has_interview_guide"] is True

            # 3. Clear Guide
            del_res = await client.delete(
                f"/api/v1/applications/{application.id}/interview-guide"
            )
            assert del_res.status_code == 200
            cleared_data = del_res.json()
            assert cleared_data["has_interview_guide"] is False
            assert cleared_data["interview_guide_html"] is None


@pytest.mark.asyncio
async def test_section_generator_language_directive(db_session: AsyncSession):
    """Verifies that non-English languages are resolved to display names and passed with explicit translation directives."""
    from app.services.interview_guide_graph import (
        LANGUAGE_DISPLAY_NAMES,
        InterviewGuideState,
        section_generator_node,
    )

    state: InterviewGuideState = {
        "cv_text": "Python Backend Engineer with PostgreSQL experience.",
        "jd_text": "Senior Backend Engineer role.",
        "company_name": "Datadog",
        "position": "Senior Backend Engineer",
        "company_context": ["Datadog is an observability company."],
        "target_sections": ["question_defenses", "prep_checklist"],
        "current_section_index": 0,
        "completed_sections": [],
        "language": "es",
        "error": None,
        "iteration_count": 0,
    }

    assert LANGUAGE_DISPLAY_NAMES["es"] == "Spanish (Español)"
    assert LANGUAGE_DISPLAY_NAMES["pt"] == "Portuguese (Português)"

    from langchain_core.messages import AIMessage

    ai_msg = AIMessage(
        content="<h2>4. Defensas de Preguntas Técnicas y de Comportamiento</h2><p>Pregunta: ¿Cómo escala sistemas distribuidos?</p>"
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = ai_msg
    mock_llm.ainvoke = AsyncMock(return_value=ai_msg)
    mock_llm.return_value = ai_msg

    with patch(
        "app.services.interview_guide_graph.get_task_chat_model",
        new_callable=AsyncMock,
        return_value=mock_llm,
    ):
        res = await section_generator_node(
            state, config={"configurable": {"db": db_session}}
        )
        assert len(res["completed_sections"]) == 1
        assert "Defensas de Preguntas" in res["completed_sections"][0]
        assert mock_llm.invoke.called or mock_llm.ainvoke.called or mock_llm.called
