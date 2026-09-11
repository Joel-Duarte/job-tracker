import asyncio
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


@pytest.mark.asyncio
async def test_interactive_headroom_reserves_slot_for_priority_one():
    from app.core.ai_queue import ProviderConcurrencyManager

    mgr = ProviderConcurrencyManager()
    provider_id = 9999
    max_concurrency = 2  # 1 background slot + 1 interactive headroom slot

    # Acquire 1st background task (Priority 2) -> Should succeed
    acquired_bg1 = False

    async def bg_task_1():
        nonlocal acquired_bg1
        async with mgr.acquire(provider_id, max_concurrency, priority=2):
            acquired_bg1 = True
            await asyncio.sleep(0.1)

    t1 = asyncio.create_task(bg_task_1())
    await asyncio.sleep(0.01)
    assert acquired_bg1 is True

    # Attempt 2nd background task (Priority 2) -> Must wait because slot 2 is reserved for interactive headroom!
    acquired_bg2 = False

    async def bg_task_2():
        nonlocal acquired_bg2
        async with mgr.acquire(provider_id, max_concurrency, priority=2):
            acquired_bg2 = True

    t2 = asyncio.create_task(bg_task_2())
    await asyncio.sleep(0.01)
    assert acquired_bg2 is False  # Blocked by headroom reservation!

    # Now fire an interactive task (Priority 1) -> Must acquire the reserved headroom slot immediately!
    acquired_interactive = False

    async def interactive_task():
        nonlocal acquired_interactive
        async with mgr.acquire(provider_id, max_concurrency, priority=1):
            acquired_interactive = True

    t3 = asyncio.create_task(interactive_task())
    await asyncio.sleep(0.01)
    assert acquired_interactive is True  # Acquired headroom slot!

    await asyncio.gather(t1, t2, t3)
    assert acquired_bg2 is True  # Completed after slot was freed


def test_candidate_prefix_is_byte_identical_across_different_jobs():
    from app.core.prompts import format_candidate_prefix

    cv_data = {
        "raw_text": "Alex Morgan, Staff Engineer...",
        "extracted_skills": ["Python", "FastAPI", "Go", "Kubernetes"],
        "years_of_experience": 8.5,
    }
    prefix1 = format_candidate_prefix(cv_data)
    prefix2 = format_candidate_prefix(cv_data)
    assert prefix1 == prefix2
    assert (
        "FastAPI, Go, Kubernetes, Python" in prefix1
        or "Python, FastAPI, Go, Kubernetes" in prefix1
    )


def test_jd_guardrail_caps_verbose_postings():
    from app.core.prompts import sanitize_and_cap_jd

    massive_jd = "Responsibilities and requirements: " + (
        "Go distributed systems " * 3000
    )
    capped = sanitize_and_cap_jd(massive_jd, max_tokens=2500)
    # 2500 tokens is approximately 10,000 characters
    assert len(capped) <= 10500
    assert "[Job posting truncated to fit context window]" in capped


@pytest.mark.asyncio
async def test_parallel_section_generation_respects_concurrency():
    from app.services.interview_guide_graph import generate_all_sections_parallel

    sections = ["tech_depth", "system_design", "behavioral", "culture_fit"]
    progress_events = []

    async def mock_generate_section(sec, *args, **kwargs):
        await asyncio.sleep(0.02)
        return f"<h3>{sec}</h3><p>Content</p>"

    with patch(
        "app.services.interview_guide_graph.generate_single_section",
        side_effect=mock_generate_section,
    ):
        results = await generate_all_sections_parallel(
            sections=sections,
            provider_id=1,
            max_concurrency=2,
            progress_callback=lambda cur, tot: progress_events.append((cur, tot)),
        )

    assert len(results) == 4
    assert len(progress_events) == 4
    assert progress_events[-1] == (4, 4)
    assert all("<h3>" in r for r in results)


def test_repetitive_loop_detection():
    from app.services.benchmark_service import detect_repetitive_loops

    clean_text = (
        "The candidate has strong experience in Python, FastAPI, and PostgreSQL."
    )
    assert detect_repetitive_loops(clean_text) is False

    looping_text = "Experience in " + ("the same tech stack the same tech stack " * 20)
    assert detect_repetitive_loops(looping_text) is True


def test_factual_grounding_check():
    from app.services.benchmark_service import check_factual_grounding

    valid_output = "The candidate's 8+ years of experience with FastAPI and PostgreSQL matches the role."
    grounding_skills = ["FastAPI", "PostgreSQL", "Go"]
    assert check_factual_grounding(valid_output, grounding_skills) is True

    hallucinated_output = (
        "This person seems like a good fit for general business administration."
    )
    assert check_factual_grounding(hallucinated_output, grounding_skills) is False


@pytest.mark.asyncio
async def test_lm_studio_unload_dispatch():
    from app.services.provider_lifecycle_service import release_engine_vram

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "models": [{"id": "qwen3.5:9b", "instance_id": "qwen3.5-inst-1"}]
    }

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.text = '{"instance_id": "qwen3.5-inst-1"}'

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
    ):
        mock_get.return_value = mock_get_resp
        mock_post.return_value = mock_post_resp

        res = await release_engine_vram(
            base_url="http://localhost:1234/v1",
            model_name="qwen3.5:9b",
        )
        assert res["success"] is True
        assert res["engine"] == "lmstudio"
        mock_post.assert_called_once()
        assert "/api/v1/models/unload" in str(mock_post.call_args[0][0])
        assert mock_post.call_args[1]["json"] == {"instance_id": "qwen3.5-inst-1"}


@pytest.mark.asyncio
async def test_vllm_sleep_dispatch():
    from app.services.provider_lifecycle_service import release_engine_vram

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        res = await release_engine_vram(
            base_url="http://localhost:8000/v1",
            model_name="qwen3.5:9b",
        )
        assert res["success"] is True
        assert res["engine"] == "vllm"
        assert "/sleep" in str(mock_post.call_args[0][0])


@pytest.mark.asyncio
async def test_ollama_unload_dispatch():
    from app.services.provider_lifecycle_service import release_engine_vram

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "models": [{"name": "llama3.1:latest", "size_vram": 4000000000}]
    }

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"done": True}

    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
    ):
        mock_get.return_value = mock_get_resp
        mock_post.return_value = mock_post_resp

        res = await release_engine_vram(
            base_url="http://localhost:11434",
            provider_type="ollama",
            model_name="llama3.1",
        )
        assert res["success"] is True
        assert res["engine"] == "ollama"
        assert "unloaded from Ollama VRAM" in res["message"]
        mock_post.assert_called_once()
        assert "/api/generate" in str(mock_post.call_args[0][0])
        assert mock_post.call_args[1]["json"] == {
            "model": "llama3.1:latest",
            "keep_alive": 0,
        }


@pytest.mark.asyncio
async def test_ollama_already_clear():
    from app.services.provider_lifecycle_service import release_engine_vram

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"models": []}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_get_resp

        res = await release_engine_vram(
            base_url="http://localhost:11434",
            provider_type="ollama",
        )
        assert res["success"] is True
        assert res["engine"] == "ollama"
        assert "already clear" in res["message"]


@pytest.mark.asyncio
async def test_sglang_release_dispatch():
    from app.services.provider_lifecycle_service import release_engine_vram

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        res = await release_engine_vram(
            base_url="http://localhost:30000/v1",
            engine_type="sglang",
        )
        assert res["success"] is True
        assert res["engine"] == "sglang"
        assert "/release_memory" in str(mock_post.call_args[0][0])


@pytest.mark.asyncio
async def test_provider_benchmark_endpoint():
    transport = ASGITransport(app=app)
    mock_res = {
        "provider_id": 1,
        "provider_name": "Local LM studio",
        "model_name": "qwen/qwen3.5-9b",
        "single_stream_tps": 46.2,
        "dual_stream_tps": 61.8,
        "is_parallel_verified": True,
        "quality_gate_passed": True,
        "recommended_max_concurrency": 2,
        "details": "2 slots verified with 100% schema fidelity.",
        "execution_time_seconds": 1.5,
    }
    with patch(
        "app.services.benchmark_service.run_capacity_benchmark",
        new_callable=AsyncMock,
        return_value=mock_res,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/ai/providers/1/benchmark", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert data["recommended_max_concurrency"] == 2
            assert data["is_parallel_verified"] is True


@pytest.mark.asyncio
async def test_provider_release_vram_endpoint():
    transport = ASGITransport(app=app)
    mock_res = {
        "success": True,
        "engine": "lmstudio",
        "message": "Model unloaded from VRAM",
    }
    with patch(
        "app.services.provider_lifecycle_service.release_provider_vram",
        new_callable=AsyncMock,
        return_value=mock_res,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/v1/ai/providers/1/release-vram")
            assert resp.status_code == 200
            assert resp.json()["success"] is True
