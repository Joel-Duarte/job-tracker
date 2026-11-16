from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.services.diagram_catalog import (
    evaluate_canvas_topology,
    match_component_to_catalog,
    resolve_challenge_blueprint,
)


@pytest.mark.asyncio
async def test_list_and_get_challenges_hide_interviewer_brief(
    db_session: AsyncSession,
):
    """GET /challenges and /challenges/{slug} return curated challenges without leaking hidden briefs."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            list_res = await ac.get("/api/v1/system-design/challenges")
            assert list_res.status_code == 200
            challenges = list_res.json()
            assert len(challenges) == 8

            raw_list_text = list_res.text
            for secret in (
                "interviewer_brief",
                "hidden_context",
                "over_engineering_traps",
                "30,000 DAU",
                "250,000 location updates/sec",
            ):
                assert secret not in raw_list_text

            spotify_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            assert spotify_res.status_code == 200
            spotify = spotify_res.json()
            assert spotify["slug"] == "spotify-100k"
            assert "interviewer_brief" not in spotify
            assert "30,000 DAU" not in spotify_res.text

            filtered_res = await ac.get(
                "/api/v1/system-design/challenges",
                params={"difficulty": "EASY"},
            )
            assert filtered_res.status_code == 200
            assert len(filtered_res.json()) == 1
            assert filtered_res.json()[0]["slug"] == "url-shortener"

            missing_res = await ac.get(
                "/api/v1/system-design/challenges/does-not-exist"
            )
            assert missing_res.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_start_session_and_requirements_interview_flow(
    db_session: AsyncSession,
):
    """Stage A -> Stage B Q&A injects hidden brief to interviewer LLM without leaking it to API caller."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge = ch_res.json()

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge["id"],
                    "mode": "INTERVIEW",
                    "variant_id": "lean-100k-streaming",
                },
            )
            assert start_res.status_code == 201
            session_data = start_res.json()
            session_id = session_data["id"]

            assert session_data["mode"] == "INTERVIEW"
            assert session_data["stage"] == "REQUIREMENTS"
            assert session_data["status"] == "IN_PROGRESS"
            assert len(session_data["requirements_transcript"]) == 1
            assert session_data["requirements_transcript"][0]["turn_index"] == 1
            assert session_data["requirements_transcript"][0]["role"] == "interviewer"

            mock_reply = AsyncMock()
            mock_reply.content = (
                "<think>Hidden brief states 30,000 DAU and 3,000-5,000 peak streams.</think>"
                "Expect around 30,000 daily active users out of 100,000 registered users, "
                "with roughly 3,000 to 5,000 concurrent audio streams at evening peak. "
                "What catalog size or latency SLA would you like to clarify next?"
            )

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = mock_reply
                mock_get_model.return_value = mock_model

                msg_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={
                        "message": "How many daily active users and concurrent streams do we expect?"
                    },
                )

            assert msg_res.status_code == 200
            updated = msg_res.json()
            assert "interviewer_brief" not in msg_res.text
            assert "<think>" not in msg_res.text

            transcript = updated["requirements_transcript"]
            assert len(transcript) == 3
            assert transcript[1]["turn_index"] == 2
            assert transcript[1]["role"] == "candidate"
            assert transcript[2]["turn_index"] == 3
            assert transcript[2]["role"] == "interviewer"
            assert "30,000 daily active users" in transcript[2]["content"]

            mock_get_model.assert_called_once()
            assert mock_get_model.call_args.kwargs["task_type"] == (
                "SYSTEM_DESIGN_INTERVIEWER"
            )
            sent_messages = mock_model.ainvoke.call_args.args[0]
            assert isinstance(sent_messages[0], SystemMessage)
            assert "30,000 DAU" in sent_messages[0].content
            assert "INTERVIEW MODE" in sent_messages[0].content
            assert isinstance(sent_messages[1], AIMessage)
            assert isinstance(sent_messages[2], HumanMessage)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_practice_mode_toggle_and_prompt_injection(
    db_session: AsyncSession,
):
    """Toggling to PRACTICE switches the interviewer system prompt to coaching mode."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge = ch_res.json()

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge["id"], "mode": "INTERVIEW"},
            )
            session_id = start_res.json()["id"]

            mode_res = await ac.patch(
                f"/api/v1/system-design/sessions/{session_id}/mode",
                json={"mode": "PRACTICE"},
            )
            assert mode_res.status_code == 200
            assert mode_res.json()["mode"] == "PRACTICE"

            mock_reply = AsyncMock()
            mock_reply.content = (
                "Great direction! Also consider asking about read/write ratio "
                "and redirect latency targets."
            )

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = mock_reply
                mock_get_model.return_value = mock_model

                msg_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={"message": "Should redirects be faster than creation?"},
                )

            assert msg_res.status_code == 200
            sent_messages = mock_model.ainvoke.call_args.args[0]
            assert "PRACTICE / COACHING MODE" in sent_messages[0].content
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_extract_and_lock_requirements_ledger_transitions_stage(
    db_session: AsyncSession,
):
    """Ledger extraction populates structured requirements; locking transitions REQUIREMENTS <-> DESIGN."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "INTERVIEW"},
            )
            session_id = start_res.json()["id"]

            extracted_json = """{
                "functional_requirements": ["Create short alias", "Redirect to long URL"],
                "non_functional_requirements": ["p99 latency < 30ms", "99.99% availability"],
                "scale_estimates": {"read_qps_peak": "12000", "write_qps_peak": "120"},
                "out_of_scope": ["User accounts"],
                "notes": "Read-heavy 100:1 workload."
            }"""
            mock_extract_res = AsyncMock()
            mock_extract_res.content = extracted_json

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = mock_extract_res
                mock_get_model.return_value = mock_model

                ext_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/extract"
                )

            assert ext_res.status_code == 200
            ext_data = ext_res.json()
            assert ext_data["stage"] == "REQUIREMENTS"
            ledger = ext_data["requirements_ledger"]
            assert ledger["is_locked"] is False
            assert ledger["functional_requirements"] == [
                "Create short alias",
                "Redirect to long URL",
            ]
            assert ledger["scale_estimates"]["read_qps_peak"] == "12000"

            lock_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": [
                        "Create short alias",
                        "HTTP 302 redirect",
                    ],
                    "non_functional_requirements": [
                        "p99 latency < 30ms",
                        "99.99% availability",
                    ],
                    "scale_estimates": {
                        "read_qps_peak": "12000",
                        "write_qps_peak": "120",
                    },
                    "out_of_scope": ["User accounts"],
                    "notes": "Locked baseline for diagramming.",
                    "is_locked": True,
                },
            )
            assert lock_res.status_code == 200
            locked_data = lock_res.json()
            assert locked_data["requirements_ledger"]["is_locked"] is True
            assert locked_data["stage"] == "DESIGN"

            unlock_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    **locked_data["requirements_ledger"],
                    "is_locked": False,
                },
            )
            assert unlock_res.status_code == 200
            assert unlock_res.json()["requirements_ledger"]["is_locked"] is False
            assert unlock_res.json()["stage"] == "REQUIREMENTS"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_and_delete_session(db_session: AsyncSession, tmp_path, monkeypatch):
    """Sessions can be listed and deleted along with any stored session diagram folder."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/rate-limiter")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "PRACTICE"},
            )
            assert start_res.status_code == 201
            session_id = start_res.json()["id"]

            session_dir = tmp_path / f"session_{session_id}"
            session_dir.mkdir(parents=True, exist_ok=True)
            (session_dir / "v1.png").write_bytes(b"fake-png-bytes")

            list_res = await ac.get("/api/v1/system-design/sessions")
            assert list_res.status_code == 200
            sessions = list_res.json()
            assert any(s["id"] == session_id for s in sessions)

            del_res = await ac.delete(f"/api/v1/system-design/sessions/{session_id}")
            assert del_res.status_code == 204
            assert not session_dir.exists()

            get_res = await ac.get(f"/api/v1/system-design/sessions/{session_id}")
            assert get_res.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_adaptive_default_mode_and_assisted_hint_tracking(
    db_session: AsyncSession,
):
    """Sessions default to ADAPTIVE and log assisted=True when hints are requested."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id},
            )
            assert start_res.status_code == 201
            session_data = start_res.json()
            assert session_data["mode"] == "ADAPTIVE"
            session_id = session_data["id"]

            mock_model = AsyncMock()
            hint_reply = AsyncMock()
            hint_reply.content = (
                "Think about read vs write QPS ratio and redirect latency bounds."
            )
            normal_reply = AsyncMock()
            normal_reply.content = "Expect 100 writes/sec and 10,000 redirects/sec."
            mock_model.ainvoke.side_effect = [normal_reply, hint_reply]

            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=mock_model,
            ):
                r1 = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={"message": "What read vs write QPS should we expect?"},
                )
                assert r1.status_code == 200

                r2 = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={
                        "message": "I want to make sure I cover constraints cleanly.",
                        "request_hint": True,
                    },
                )
                assert r2.status_code == 200

            turns = r2.json()["requirements_transcript"]
            assert turns[1]["assisted"] is False
            assert turns[2]["assisted"] is False
            assert turns[3]["assisted"] is True
            assert turns[4]["assisted"] is True

            first_sys = mock_model.ainvoke.call_args_list[0].args[0][0].content
            second_sys = mock_model.ainvoke.call_args_list[1].args[0][0].content
            assert "ADAPTIVE STAKEHOLDER MODE" in first_sys
            assert "COACHING HINT REQUESTED" not in first_sys
            assert "COACHING HINT REQUESTED" in second_sys
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_custom_manual_and_ai_generated_challenges_lifecycle(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Custom challenges can be authored manually, generated via AI+web search, and deleted; built-ins stay protected."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            manual_res = await ac.post(
                "/api/v1/system-design/challenges",
                json={
                    "title": "Design a Webhook Delivery Engine",
                    "category": "DISTRIBUTED_SYSTEMS",
                    "difficulty": "MEDIUM",
                    "prompt_summary": "Reliable multi-tenant webhook fanout with retries and DLQ.",
                    "initial_prompt": "Design a webhook delivery platform supporting exponential backoff and tenant isolation.",
                    "tags": ["webhooks", "queues"],
                    "expected_components": ["Webhook API", "Retry Queue", "DLQ"],
                    "scale_notes": "5,000 events/sec peak across 10k tenants",
                },
            )
            assert manual_res.status_code == 201
            manual = manual_res.json()
            assert manual["is_builtin"] is False
            assert "interviewer_brief" not in manual

            ai_reply = AsyncMock()
            ai_reply.content = """{
                "title": "Design a Multi-Region Feature Flag Service",
                "category": "DATA_INFRASTRUCTURE",
                "difficulty": "HARD",
                "prompt_summary": "Low-latency edge evaluation of feature flags with audit log.",
                "initial_prompt": "Design a feature flagging system delivering sub-10ms flag reads globally.",
                "tags": ["feature-flags", "edge"],
                "interviewer_brief": {
                    "hidden_context": {"scale_targets": "500k evaluations/sec"},
                    "expected_components": ["Control Plane", "Edge CDN", "Streaming Invalidation"],
                    "over_engineering_traps": ["Direct synchronous DB read per flag check"],
                    "defence_questions": ["How do you handle flag rollback under split-brain?"]
                }
            }"""

            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    return_value=AsyncMock(ainvoke=AsyncMock(return_value=ai_reply)),
                ),
                patch(
                    "app.services.web_search.search_web",
                    new=AsyncMock(
                        return_value=[
                            {
                                "title": "Streaming Feature Flags at Edge",
                                "snippet": "SSE push updates reduce SDK polling overhead.",
                                "url": "https://example.com/flags",
                            }
                        ]
                    ),
                ),
            ):
                gen_res = await ac.post(
                    "/api/v1/system-design/challenges/generate",
                    json={
                        "topic": "Feature flag distribution at global edge",
                        "difficulty": "HARD",
                        "use_web_search": True,
                    },
                )
            assert gen_res.status_code == 201
            generated = gen_res.json()
            assert generated["is_builtin"] is False
            assert "interviewer_brief" not in generated
            assert generated["difficulty"] == "HARD"

            # Edit the AI-generated custom challenge via PUT and verify custom editable fields preserved
            edit_res = await ac.put(
                f"/api/v1/system-design/challenges/{generated['id']}",
                json={
                    "title": "Design a Global Edge Feature Flag Platform",
                    "category": "DATA_INFRASTRUCTURE",
                    "difficulty": "HARD",
                    "prompt_summary": "Updated summary: ultra-low-latency flag evaluation with streaming invalidation.",
                    "initial_prompt": "Updated prompt: design a multi-region feature flag service with sub-10ms reads.",
                    "tags": ["feature-flags", "edge", "sse"],
                    "expected_components": ["Control Plane", "Edge CDN"],
                    "scale_notes": "1M evaluations/sec global peak",
                },
            )
            assert edit_res.status_code == 200
            edited = edit_res.json()
            assert edited["title"] == "Design a Global Edge Feature Flag Platform"
            assert "interviewer_brief" not in edited
            assert edited["tags"] == ["feature-flags", "edge", "sse"]
            assert edited["expected_components"] == ["Control Plane", "Edge CDN"]
            assert edited["scale_notes"] == "1M evaluations/sec global peak"

            # F-07: Omitting tags preserves existing tags instead of overwriting with defaults
            preserve_res = await ac.put(
                f"/api/v1/system-design/challenges/{generated['id']}",
                json={
                    "title": "Design a Global Edge Feature Flag Platform v2",
                    "category": "DATA_INFRASTRUCTURE",
                    "difficulty": "HARD",
                    "prompt_summary": "Updated summary v2: ultra-low-latency flag evaluation.",
                    "initial_prompt": "Updated prompt v2: design a multi-region feature flag service.",
                },
            )
            assert preserve_res.status_code == 200
            preserved = preserve_res.json()
            assert preserved["tags"] == ["feature-flags", "edge", "sse"]
            assert preserved["expected_components"] == ["Control Plane", "Edge CDN"]
            assert preserved["scale_notes"] == "1M evaluations/sec global peak"

            # F-05: Start sessions on custom and built-in challenges, then verify deletion archives
            # rather than cascade-deleting session history or stored diagrams.
            sess_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": manual["id"]},
            )
            assert sess_res.status_code == 201
            manual_session_id = sess_res.json()["id"]

            del_manual = await ac.delete(
                f"/api/v1/system-design/challenges/{manual['id']}"
            )
            assert del_manual.status_code == 204

            # Session linked to deleted/archived custom challenge MUST remain accessible
            hist_res = await ac.get(
                f"/api/v1/system-design/sessions/{manual_session_id}"
            )
            assert hist_res.status_code == 200
            assert hist_res.json()["challenge"]["id"] == manual["id"]

            # Built-in challenge deletion also archives cleanly & protects interviewer_brief
            builtin_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            builtin_data = builtin_res.json()
            assert builtin_data["expected_components"] == []
            assert builtin_data["scale_notes"] == ""
            builtin_id = builtin_data["id"]

            builtin_sess_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": builtin_id},
            )
            assert builtin_sess_res.status_code == 201
            builtin_session_id = builtin_sess_res.json()["id"]

            del_builtin = await ac.delete(
                f"/api/v1/system-design/challenges/{builtin_id}"
            )
            assert del_builtin.status_code == 204

            after_del_list = await ac.get("/api/v1/system-design/challenges")
            assert after_del_list.status_code == 200
            remaining_builtins = [
                c for c in after_del_list.json() if c["is_builtin"] is True
            ]
            assert len(remaining_builtins) == 7

            # Session linked to archived built-in challenge also remains intact
            assert (
                await ac.get(f"/api/v1/system-design/sessions/{builtin_session_id}")
            ).status_code == 200

            # Reset defaults unarchives all 8 built-in challenges while preserving custom & sessions
            reset_res = await ac.post("/api/v1/system-design/challenges/reset-defaults")
            assert reset_res.status_code == 200
            reset_items = reset_res.json()
            assert len([c for c in reset_items if c["is_builtin"] is True]) == 8
            assert any(
                c["title"] == "Design a Global Edge Feature Flag Platform v2"
                for c in reset_items
            )
            assert (
                await ac.get(f"/api/v1/system-design/sessions/{builtin_session_id}")
            ).status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_f02_backend_stage_enforcement_and_completed_immutability(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """F-02: Enforces strict server-side stage transitions and rejects mutations on COMPLETED sessions."""
    import json

    import app.services.system_design_service as sd_service_module
    from app.services.system_design_service import DEFAULT_RUBRIC_DIMENSIONS

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake-png"
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge_id = ch_res.json()["id"]
            session_id = (
                await ac.post(
                    "/api/v1/system-design/sessions",
                    json={"challenge_id": challenge_id},
                )
            ).json()["id"]

            # 1. Locking an empty ledger must fail with 400
            empty_lock = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": [],
                    "non_functional_requirements": [],
                    "scale_estimates": {},
                    "out_of_scope": [],
                    "is_locked": True,
                },
            )
            assert empty_lock.status_code == 400

            # 2. Diagram upload, review, defence, evaluate before locking must fail with 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/diagrams",
                    files={"file": ("v1.png", fake_png, "image/png")},
                    data={"notes": "Early"},
                )
            ).status_code == 400
            assert (
                await ac.post(f"/api/v1/system-design/sessions/{session_id}/review")
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={"message": "Skip directly to defence"},
                )
            ).status_code == 400
            assert (
                await ac.post(f"/api/v1/system-design/sessions/{session_id}/evaluate")
            ).status_code == 400

            # Lock valid requirements -> DESIGN stage
            assert (
                await ac.put(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                    json={
                        "functional_requirements": ["Create short URL"],
                        "non_functional_requirements": ["p99 < 30ms"],
                        "scale_estimates": {"read_qps": "10000"},
                        "out_of_scope": [],
                        "is_locked": True,
                    },
                )
            ).status_code == 200

            # 3. Requirements discovery & extraction rejected once locked / in DESIGN stage
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={"message": "More requirements"},
                )
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/extract"
                )
            ).status_code == 400

            # 4. Upload diagram in DESIGN -> unlocking ledger rejected once diagram exists; defence/evaluate still rejected before review
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/diagrams",
                    files={"file": ("v1.png", fake_png, "image/png")},
                    data={"notes": "Arch v1"},
                )
            ).status_code == 201
            assert (
                await ac.put(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                    json={
                        "functional_requirements": ["Create short URL"],
                        "non_functional_requirements": ["p99 < 30ms"],
                        "scale_estimates": {"read_qps": "10000"},
                        "out_of_scope": [],
                        "is_locked": False,
                    },
                )
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={"message": "Early defence"},
                )
            ).status_code == 400
            assert (
                await ac.post(f"/api/v1/system-design/sessions/{session_id}/evaluate")
            ).status_code == 400

            # 5. Complete review -> REVIEW stage, evaluate still rejected without candidate defence turn
            rev_reply = AsyncMock()
            rev_reply.content = json.dumps(
                {
                    "interpreted_components": ["API", "Redis", "Postgres"],
                    "interpreted_data_flows": ["Client -> API -> Redis"],
                    "visual_clarifications_needed": [],
                    "strengths": ["Fast redirect path via Redis"],
                    "missing_components": [],
                    "bottlenecks_and_spofs": ["Single Redis primary"],
                    "unnecessary_complexity": [],
                    "requirement_gaps": [],
                    "overall_impression": "Good baseline.",
                    "suggested_defence_topics": ["How do you handle Redis failover?"],
                }
            )
            def_reply = AsyncMock()
            def_reply.content = "Makes sense on Sentinel failover."
            eval_reply = AsyncMock()
            eval_reply.content = json.dumps(
                {
                    "overall_score": 80.0,
                    "readiness_rating": "INTERVIEW_READY",
                    "executive_summary": "Solid design with clear caching and persistence trade-offs.",
                    "rubric_scores": [
                        {
                            "dimension": d,
                            "score": 4,
                            "evidence": f"Candidate demonstrated {d} cleanly in ledger and diagram.",
                            "critique": f"Add quantitative bounds for {d}.",
                        }
                        for d in DEFAULT_RUBRIC_DIMENSIONS
                    ],
                    "key_strengths": ["Low-latency redirect caching"],
                    "critical_gaps": ["Document failover latency bounds"],
                    "recommended_next_steps": ["Add health check annotations"],
                }
            )
            mock_model = AsyncMock()
            mock_model.ainvoke.side_effect = [rev_reply, def_reply, eval_reply]
            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=mock_model,
            ):
                assert (
                    await ac.post(f"/api/v1/system-design/sessions/{session_id}/review")
                ).status_code == 202
                # Evaluate before candidate defence turn must return 400
                assert (
                    await ac.post(
                        f"/api/v1/system-design/sessions/{session_id}/evaluate"
                    )
                ).status_code == 400

                # Participate in defence -> DEFENCE stage -> then complete evaluation
                assert (
                    await ac.post(
                        f"/api/v1/system-design/sessions/{session_id}/defence/message",
                        json={
                            "message": "We use Redis Sentinel with Postgres fallback on cache miss."
                        },
                    )
                ).status_code == 200
                assert (
                    await ac.post(
                        f"/api/v1/system-design/sessions/{session_id}/evaluate"
                    )
                ).status_code == 202

            # 6. COMPLETED session rejects all further mutations with 400
            done_session = (
                await ac.get(f"/api/v1/system-design/sessions/{session_id}")
            ).json()
            assert done_session["status"] == "COMPLETED"
            assert done_session["stage"] == "COMPLETED"

            assert (
                await ac.patch(
                    f"/api/v1/system-design/sessions/{session_id}/mode",
                    json={"mode": "PRACTICE"},
                )
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={"message": "Post completion"},
                )
            ).status_code == 400
            assert (
                await ac.put(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                    json={
                        "functional_requirements": ["Create short URL"],
                        "non_functional_requirements": [],
                        "scale_estimates": {},
                        "out_of_scope": [],
                        "is_locked": True,
                    },
                )
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/diagrams",
                    files={"file": ("v2.png", fake_png, "image/png")},
                    data={"notes": "Post completion"},
                )
            ).status_code == 400
            assert (
                await ac.post(f"/api/v1/system-design/sessions/{session_id}/review")
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={"message": "Post completion"},
                )
            ).status_code == 400
            assert (
                await ac.post(f"/api/v1/system-design/sessions/{session_id}/evaluate")
            ).status_code == 400
            assert (
                await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/import-evaluation",
                    json={"raw_response": '{"rubric_scores": []}'},
                )
            ).status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_structured_interviewer_brief_and_url_shortener_stakeholder_roleplay(
    db_session: AsyncSession,
):
    """Stakeholder roleplay answers concrete brief facts progressively, handles unspecified items, and auto-heals legacy prompts."""
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    from sqlalchemy import select

    from app.core.prompts import DEFAULT_PROMPTS, PromptModel, seed_default_prompts
    from app.models.system_design import SystemDesignChallengeModel
    from app.services.system_design_seed import seed_system_design_challenges

    await seed_system_design_challenges(db_session)
    challenges = (
        (await db_session.execute(select(SystemDesignChallengeModel))).scalars().all()
    )
    assert len(challenges) == 8
    required_brief_keys = {
        "business_context",
        "scale_estimates",
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
        "priorities",
        "out_of_scope",
    }
    for ch in challenges:
        brief = ch.interviewer_brief or {}
        missing = required_brief_keys - set(brief.keys())
        assert not missing, f"{ch.slug} missing structured brief keys: {missing}"

    # Verify legacy interviewer prompt in DB gets auto-healed to stakeholder roleplay
    legacy = PromptModel(
        name="system_design_interviewer",
        template="Old prompt: Make the candidate drive discovery. push back and ask what workload or SLA justifies it.",
    )
    db_session.add(legacy)
    await db_session.commit()
    await seed_default_prompts(db_session)
    await db_session.commit()
    await db_session.refresh(legacy)
    assert legacy.template == DEFAULT_PROMPTS["system_design_interviewer"]
    assert "Stakeholder" in legacy.template
    assert "NEVER BOUNCE" in legacy.template

    captured_prompts: list[str] = []
    scenario_replies = {
        "creation volume": "We expect about 3.3M new shortened URLs created per day (~100M/month), averaging 40 writes/s and peaking at 120 writes/s.",
        "user traffic": "We have ~80M MAU and 20M DAU generating ~330M redirects per day (~4,000 QPS average, ~12,000 QPS peak) at a 100:1 read-to-write ratio.",
        "expire": "Links have a default 5-year retention lifecycle (~300M active records), and creators can optionally set an explicit TTL (returning HTTP 410/404 once expired).",
        "public or private": "Short links are public by default with no login required to redirect; 7-char Base62 codes must be non-sequential and non-predictable to prevent enumeration, with HTTPS and malicious URL blocklist checks.",
        "analytics": "Click count analytics are asynchronous and eventually consistent—a 1-5 minute freshness lag is acceptable so analytics never slow down the <30ms p99 redirect path.",
        "qr code": "QR code generation is not specified in our current business requirements. As a baseline assumption, we can treat QR rendering as a client-side or separate post-MVP add-on if you want to note that.",
    }

    async def fake_invoke(chat_model, messages, tracer, db, task_type=None):
        sys_msg = str(messages[0].content)
        captured_prompts.append(sys_msg)
        last_user = str(messages[-1].content).lower()
        for key, text in scenario_replies.items():
            if key in last_user:
                return MagicMock(content=text)
        return MagicMock(content="Unmatched test turn.")

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            assert ch_res.status_code == 200
            challenge_id = ch_res.json()["id"]

            sess_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge_id,
                    "mode": "INTERVIEW",
                    "variant_id": "public-consumer-shortener",
                },
            )
            assert sess_res.status_code == 201
            session_id = sess_res.json()["id"]

            questions_and_assertions = [
                (
                    "What is our expected daily URL creation volume?",
                    ["3.3M", "100M/month"],
                ),
                (
                    "What user traffic (MAU/DAU and redirect QPS) should we expect?",
                    ["80M MAU", "20M DAU", "330M redirects", "12,000 QPS"],
                ),
                ("Do links expire or have a TTL?", ["5-year", "TTL"]),
                (
                    "Are links public or private, and what are the security expectations?",
                    ["public", "non-predictable", "HTTPS"],
                ),
                (
                    "What consistency and freshness do we need for click analytics?",
                    ["eventually consistent", "1-5 minute"],
                ),
                (
                    "Should we support QR code generation for each short link?",
                    ["not specified", "assumption"],
                ),
            ]

            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    new=AsyncMock(return_value=MagicMock()),
                ),
                patch(
                    "app.services.system_design_service._invoke_llm_adaptive",
                    side_effect=fake_invoke,
                ),
            ):
                for question, expected_tokens in questions_and_assertions:
                    res = await ac.post(
                        f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                        json={"message": question},
                    )
                    assert res.status_code == 200
                    transcript = res.json()["requirements_transcript"]
                    reply = transcript[-1]["content"]
                    for token in expected_tokens:
                        assert token in reply
                    assert "what do you think" not in reply.lower()

            # Ensure the hidden brief was injected into the stakeholder system prompt
            assert len(captured_prompts) == 6
            brief_check = json.dumps({"daily_creation_volume": "3.3M"})
            assert "3.3M new shortened URLs" in captured_prompts[0]
            assert "80M monthly active users" in captured_prompts[0]
            assert "non-sequential" in captured_prompts[0]
            assert brief_check  # keep lint clean
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_requirements_ledger_distinguishes_confirmed_assumptions_and_unresolved(
    db_session: AsyncSession,
):
    """Live ledger extraction and manual update distinguish confirmed requirements, assumptions, and unresolved questions."""
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge_id = ch_res.json()["id"]
            sess_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "ADAPTIVE"},
            )
            session_id = sess_res.json()["id"]

            extracted_json = json.dumps(
                {
                    "functional_requirements": [
                        "Create 7-char Base62 short URLs",
                        "Optional user-specified TTL expiration",
                    ],
                    "non_functional_requirements": [
                        "99.99% redirect availability",
                        "p99 redirect latency < 30ms",
                        "Eventual consistency (1-5 min lag) for click analytics",
                    ],
                    "scale_estimates": {
                        "creation_volume": "3.3M/day (~100M/month)",
                        "traffic": "80M MAU, 20M DAU, 12,000 peak redirect QPS",
                    },
                    "out_of_scope": ["Custom branded domain SSL"],
                    "assumptions": [
                        "Assumption: QR code rendering deferred to client side post-MVP"
                    ],
                    "unresolved_questions": [
                        "Whether custom aliases require authenticated user accounts"
                    ],
                    "notes": "Focus on read-heavy redirect cache path.",
                }
            )

            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    new=AsyncMock(return_value=MagicMock()),
                ),
                patch(
                    "app.services.system_design_service._invoke_llm_adaptive",
                    new=AsyncMock(return_value=MagicMock(content=extracted_json)),
                ),
            ):
                ext_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/extract"
                )
            assert ext_res.status_code == 200
            ledger = ext_res.json()["requirements_ledger"]
            assert ledger["assumptions"] == [
                "Assumption: QR code rendering deferred to client side post-MVP"
            ]
            assert ledger["unresolved_questions"] == [
                "Whether custom aliases require authenticated user accounts"
            ]
            assert ledger["is_locked"] is False

            # Locking ledger preserves assumptions & unresolved questions and advances stage to DESIGN
            lock_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ledger["functional_requirements"],
                    "non_functional_requirements": ledger[
                        "non_functional_requirements"
                    ],
                    "scale_estimates": ledger["scale_estimates"],
                    "out_of_scope": ledger["out_of_scope"],
                    "assumptions": ledger["assumptions"],
                    "unresolved_questions": [],
                    "notes": ledger["notes"],
                    "is_locked": True,
                },
            )
            assert lock_res.status_code == 200
            locked = lock_res.json()
            assert locked["stage"] == "DESIGN"
            assert locked["requirements_ledger"]["is_locked"] is True
            assert locked["requirements_ledger"]["assumptions"] == ledger["assumptions"]
            assert locked["requirements_ledger"]["unresolved_questions"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_seed_determinism_anti_repeat_and_explicit_variant_selection(
    db_session: AsyncSession,
):
    """Verify anti-repeat random default, deterministic brief_seed replay, and explicit variant_id."""
    from sqlalchemy import select

    from app.models.system_design import SystemDesignSessionModel
    from app.services.system_design_service import SystemDesignService

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            assert ch_res.status_code == 200
            challenge = ch_res.json()
            assert len(challenge["available_variants"]) == 3

            # 1. Consecutive default blind starts never repeat immediately preceding variant_id
            observed_variant_ids: list[str] = []
            for _ in range(4):
                s_res = await ac.post(
                    "/api/v1/system-design/sessions",
                    json={"challenge_id": challenge["id"], "mode": "ADAPTIVE"},
                )
                assert s_res.status_code == 201
                payload = s_res.json()
                assert payload["brief_seed"]
                assert payload["variant_selection_mode"] == "random"
                # Blind until COMPLETED
                assert payload["variant_id"] is None
                assert payload["variant_title"] is None
                assert "session_brief" not in payload

                row = (
                    await db_session.execute(
                        select(SystemDesignSessionModel).where(
                            SystemDesignSessionModel.id == payload["id"]
                        )
                    )
                ).scalar_one()
                assert row.variant_id
                if observed_variant_ids:
                    assert row.variant_id != observed_variant_ids[-1]
                observed_variant_ids.append(row.variant_id)

            # 2. Seed determinism: same brief_seed always yields identical variant_id + session_brief
            s_a = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge["id"],
                    "brief_seed": "staff-drill-99",
                },
            )
            s_b = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge["id"],
                    "brief_seed": "STAFF-DRILL-99",
                },
            )
            assert s_a.status_code == 201 and s_b.status_code == 201
            assert s_a.json()["brief_seed"] == "staff-drill-99"
            assert s_b.json()["brief_seed"] == "staff-drill-99"
            row_a = await SystemDesignService.get_session(db_session, s_a.json()["id"])
            row_b = await SystemDesignService.get_session(db_session, s_b.json()["id"])
            assert row_a.variant_id == row_b.variant_id
            assert row_a.session_brief == row_b.session_brief

            # 3. Explicit variant selection reveals variant_title upfront and rejects invalid IDs
            exp_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge["id"],
                    "variant_id": "enterprise-compliance-linker",
                },
            )
            assert exp_res.status_code == 201
            exp_data = exp_res.json()
            assert exp_data["variant_selection_mode"] == "explicit"
            assert exp_data["variant_id"] == "enterprise-compliance-linker"
            assert exp_data["variant_title"] == "Enterprise Internal Compliance Linker"

            bad_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge["id"],
                    "variant_id": "nonexistent-archetype",
                },
            )
            assert bad_res.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_variant_session_brief_isolation_across_all_pipeline_stages(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Stakeholder, Diagram Review, Defence, Final Evaluation, and Frontier Export all use session_brief."""
    import base64
    from unittest.mock import MagicMock

    from app.services import system_design_service
    from app.services.system_design_service import SystemDesignService

    monkeypatch.setattr(
        system_design_service,
        "SYSTEM_DESIGN_DATA_DIR",
        tmp_path,
    )
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="
    )

    captured_prompts: list[str] = []

    async def _capture_llm(chat_model, messages, tracer, db, **kwargs):
        sys_msg = next(
            (m.content for m in messages if isinstance(m, SystemMessage)), ""
        )
        captured_prompts.append(str(sys_msg))
        return AIMessage(
            content="Enterprise PostgreSQL suffices for 150,000 employees."
        )

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge_id = ch_res.json()["id"]

            # Explicit Enterprise Compliance Linker variant (150,000 employees, PostgreSQL YAGNI)
            s_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge_id,
                    "variant_id": "enterprise-compliance-linker",
                    "brief_seed": "ent-001",
                },
            )
            assert s_res.status_code == 201
            session_id = s_res.json()["id"]

            # Stage B: Requirements Stakeholder prompt receives Enterprise brief, NOT Consumer/AdTech
            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    new=AsyncMock(return_value=MagicMock()),
                ),
                patch(
                    "app.services.system_design_service._invoke_llm_adaptive",
                    new=_capture_llm,
                ),
            ):
                msg_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={"message": "Who are the users and expected scale?"},
                )
            assert msg_res.status_code == 200
            assert "150,000 employees" in captured_prompts[-1]
            assert "300M DAU" not in captured_prompts[-1]

            # Lock ledger -> DESIGN
            lock_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Create internal SSO short links"],
                    "non_functional_requirements": ["Audit trail for every redirect"],
                    "scale_estimates": {"dau": "150,000 employees"},
                    "out_of_scope": ["Public anonymous links"],
                    "notes": "Enterprise compliant shortener",
                    "is_locked": True,
                },
            )
            assert lock_res.status_code == 200

            # Upload diagram v1
            up_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("arch.png", png_bytes, "image/png")},
                data={"notes": "SSO proxy + Postgres"},
            )
            assert up_res.status_code == 201

            # Stage C/D: prepare_diagram_review_context injects Enterprise session_brief
            rev_ctx = await SystemDesignService.prepare_diagram_review_context(
                db_session, session_id, diagram_version=1
            )
            assert "150,000 employees" in rev_ctx["sys_prompt"]
            assert "300M DAU" not in rev_ctx["sys_prompt"]

            # persist_architecture_review without suggested_defence_topics seeds from variant's defence_questions
            reviewed = await SystemDesignService.persist_architecture_review(
                db_session,
                session_id,
                {
                    "diagram_version": 1,
                    "interpreted_components": ["SSO Proxy", "PostgreSQL"],
                    "interpreted_data_flows": [
                        "Employee -> SSO Proxy -> App -> Postgres"
                    ],
                    "visual_clarifications_needed": [],
                    "strengths": ["Avoided unnecessary distributed KGS"],
                    "missing_components": [],
                    "bottlenecks_and_spofs": [],
                    "unnecessary_complexity": [],
                    "requirement_gaps": [],
                    "overall_impression": "Right-sized enterprise design.",
                    "suggested_defence_topics": [],
                },
            )
            session_obj = await SystemDesignService.get_session(db_session, session_id)
            variant_q0 = session_obj.session_brief["defence_questions"][0]
            assert reviewed.defence_transcript[0]["content"] == variant_q0

            # Stage E: Defence turn receives Enterprise session_brief
            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    new=AsyncMock(return_value=MagicMock()),
                ),
                patch(
                    "app.services.system_design_service._invoke_llm_adaptive",
                    new=_capture_llm,
                ),
            ):
                def_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={
                        "message": "PostgreSQL + SSO handles 150k corporate users easily."
                    },
                )
            assert def_res.status_code == 200
            assert "150,000 employees" in captured_prompts[-1]
            assert "300M DAU" not in captured_prompts[-1]

            # Stage F: Final Evaluation context + Frontier Packet inject Enterprise session_brief
            eval_ctx = await SystemDesignService.prepare_final_evaluation_context(
                db_session, session_id
            )
            assert "150,000 employees" in eval_ctx["sys_prompt"]
            assert "300M DAU" not in eval_ctx["sys_prompt"]

            packet_res = await ac.get(
                f"/api/v1/system-design/sessions/{session_id}/frontier-packet"
            )
            assert packet_res.status_code == 200
            md = packet_res.json()["markdown_packet"]
            assert "#ent-001" in md
            assert "150,000 employees" in md
            assert "300M DAU" not in md
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_challenge_generation_normalizes_three_variants(
    db_session: AsyncSession,
):
    """Generated custom challenges store 3 distinct requirement variants playable by variant_id."""
    import json

    from app.services.system_design_service import SystemDesignService

    generated_payload = {
        "title": "Design a Real-Time Fraud Scoring Engine",
        "category": "DATA_INFRASTRUCTURE",
        "difficulty": "HARD",
        "prompt_summary": "Score card swipes and transfers in real time.",
        "initial_prompt": "Design a fraud scoring system. Clarify SLA, traffic, and constraints first.",
        "tags": ["fraud", "streaming", "low-latency"],
        "interviewer_brief": {
            "variants": [
                {
                    "variant_id": "lean-neobank-mvp",
                    "title": "Lean Neobank Rules Engine",
                    "focus_summary": "Deterministic rules with single-region PostgreSQL.",
                    "business_context": {"product_goal": "Launch basic rule scoring"},
                    "scale_estimates": {"qps": "500 req/s"},
                    "functional_requirements": ["Score swipe rules"],
                    "non_functional_requirements": ["< 80ms p99"],
                    "constraints": ["Zero ML infra team"],
                    "priorities": ["P0: Simple deterministic rules"],
                    "out_of_scope": ["Deep neural embeddings"],
                    "expected_components": ["Rule Engine", "PostgreSQL"],
                    "over_engineering_traps": ["Flink + Kafka for 500 QPS"],
                    "defence_questions": [
                        "Why avoid streaming stateful engines at 500 QPS?"
                    ],
                },
                {
                    "variant_id": "global-card-network",
                    "title": "Global Card Network Scorer",
                    "focus_summary": "100k TPS multi-region online feature store + Flink.",
                    "business_context": {"product_goal": "Global issuer fraud SLA"},
                    "scale_estimates": {"qps": "100,000 TPS peak"},
                    "functional_requirements": ["Real-time velocity features"],
                    "non_functional_requirements": ["< 25ms p99 strict failover"],
                    "constraints": ["PCI-DSS cardholder isolation"],
                    "priorities": ["P0: Fail-open/fallback rule circuit breaker"],
                    "out_of_scope": ["Batch tax reporting"],
                    "expected_components": [
                        "Edge Scorer",
                        "Redis Feature Store",
                        "Flink",
                    ],
                    "over_engineering_traps": ["Synchronous cross-ocean consensus"],
                    "defence_questions": [
                        "How do you keep feature freshness under 1s across regions?"
                    ],
                },
                {
                    "variant_id": "crypto-withdrawal-guard",
                    "title": "Exchange Withdrawal Hold Guard",
                    "focus_summary": "Fail-closed high-value anomaly review with human escalation.",
                    "business_context": {
                        "product_goal": "Prevent irreversible on-chain drains"
                    },
                    "scale_estimates": {"qps": "4,000 withdrawals/s peak"},
                    "functional_requirements": [
                        "Graph risk scoring",
                        "Manual analyst queue",
                    ],
                    "non_functional_requirements": [
                        "Zero false-negative bypass (fail-closed)"
                    ],
                    "constraints": ["Irreversible ledger settlements"],
                    "priorities": ["P0: Fail-closed holds on score timeout"],
                    "out_of_scope": ["Credit card chargebacks"],
                    "expected_components": [
                        "Hold State Machine",
                        "Graph Store",
                        "Analyst Case Queue",
                    ],
                    "over_engineering_traps": [
                        "Fail-open auto-approvals during timeouts"
                    ],
                    "defence_questions": [
                        "Why is fail-closed mandatory here unlike retail checkout?"
                    ],
                },
            ]
        },
    }

    ctx = {
        "topic_text": "Real-Time Fraud Scoring",
        "difficulty": "HARD",
    }
    challenge = await SystemDesignService.persist_generated_challenge(
        db_session, ctx, generated_payload
    )
    variants = challenge.interviewer_brief.get("variants") or []
    assert len(variants) == 3

    # Top-level brief inherits primary variant fallback cleanly
    assert challenge.interviewer_brief.get("expected_components") == [
        "Rule Engine",
        "PostgreSQL",
    ]

    # Starting an explicit session on variant 3 snapshots ONLY variant 3 into session_brief
    session = await SystemDesignService.start_session(
        db_session,
        challenge.id,
        variant_id="crypto-withdrawal-guard",
        brief_seed="fraud-test-seed",
    )
    assert session.variant_id == "crypto-withdrawal-guard"
    assert session.session_brief["scale_estimates"]["qps"] == "4,000 withdrawals/s peak"
    assert "variants" not in session.session_brief
    assert "global-card-network" not in json.dumps(session.session_brief)


@pytest.mark.asyncio
async def test_challenge_context_and_frontier_prompt_include_notes_research_emails_and_dedup(
    db_session: AsyncSession,
):
    """Frontier challenge prompt and context builder pull app notes, research, emails, and existing challenge list."""
    from datetime import UTC, datetime

    from app.models.applications import (
        ApplicationEventModel,
        ApplicationModel,
        CompanyModel,
        JobPostingModel,
    )

    company = CompanyModel(
        name="Stripe",
        name_normalized="stripe",
        notes="Heavy Go/Java/Ruby ledger reliability focus",
        pros=["High-throughput webhook & billing infrastructure"],
        company_research={"architecture": "Cell-based multi-region payment pods"},
    )
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Staff Backend Engineer, Ledger",
        status="TECHNICAL_INTERVIEW",
        notes="Recruiter note: expects deep dive on webhook ordering, DLQs, and private salary target $280k.",
        match_analysis_payload={"focus_gaps": ["Double-entry ledger sharding"]},
    )
    db_session.add(application)
    await db_session.flush()

    posting = JobPostingModel(
        application_id=application.id,
        job_url="https://stripe.com/jobs/listing/staff-backend-ledger",
        description_markdown="Own idempotent multi-region payment clearing and event pipelines.",
        required_skills=["Distributed Systems", "PostgreSQL", "Kafka", "Idempotency"],
        structured_spec={"domain": "payments-clearing", "sla": "99.999%"},
    )
    db_session.add(posting)

    event = ApplicationEventModel(
        email_application_id=application.id,
        email_event_type="INTERVIEW_INVITE",
        email_subject="Stripe Architecture Loop Scheduling",
        email_summary="60m system design round covering high-reliability webhook fanout & ledger reconciliation.",
        email_received_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/system-design/challenges/frontier-prompt",
                json={
                    "application_id": application.id,
                    "difficulty": "HARD",
                    "use_web_search": False,
                    "extra_context": "Focus on outbox pattern vs CDC trade-offs.",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["filename"].startswith("stripe-")
            assert set(data["context_signals"]) >= {
                "Application Notes",
                "Job Posting & Skills",
                "Company Research",
                "Match Gap Analysis",
                "Interview Email Clues",
                "Extra Focus Clues",
            }
            prompt = data["markdown_prompt"]
            assert "EXISTING CHALLENGES — DO NOT DUPLICATE" in prompt
            assert "Design a URL Shortener" in prompt
            assert "Recruiter note: expects deep dive on webhook ordering" in prompt
            assert "Cell-based multi-region payment pods" in prompt
            assert (
                "60m system design round covering high-reliability webhook fanout"
                in prompt
            )
            assert "Focus on outbox pattern vs CDC trade-offs." in prompt
            assert "NEVER copy private compensation figures" in prompt
            assert "Design a URL Shortener" in data["existing_challenge_titles"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_and_import_challenge_duplicate_detection_repair_and_override(
    db_session: AsyncSession,
):
    """Enforce duplicate 409 handling, 1 controlled repair retry in AI generation, and allow_duplicate override."""
    import json as _json

    def _make_variant_payload(title: str, slug_prefix: str) -> dict:
        def _v(vid: str, vtitle: str, goal: str, qps: str) -> dict:
            return {
                "variant_id": vid,
                "title": vtitle,
                "focus_summary": goal,
                "business_context": {
                    "product_goal": goal,
                    "target_users": "Developers",
                },
                "scale_estimates": {"dau": "1M", "daily_volume": "100M", "qps": qps},
                "functional_requirements": [f"{vtitle} ingestion", "Audit trail"],
                "non_functional_requirements": ["p99 < 40ms", "99.99% availability"],
                "constraints": ["Zero silent data loss"],
                "priorities": ["P0: Idempotency"],
                "out_of_scope": ["Billing UI"],
                "hidden_context": {
                    "scale_targets": qps,
                    "key_constraints": ["Ordered delivery"],
                },
                "expected_components": ["API Gateway", "Kafka", "Ledger DB"],
                "over_engineering_traps": ["Two-phase commit across internet webhooks"],
                "defence_questions": [
                    f"How does {vtitle} avoid duplicate side effects?"
                ],
            }

        return {
            "title": title,
            "category": "DISTRIBUTED_SYSTEMS",
            "difficulty": "HARD",
            "prompt_summary": f"Architect {title} with strong operational guarantees and clear failure boundaries.",
            "initial_prompt": f"Let us design {title}. Begin by clarifying requirements, expected throughput, and consistency SLAs.",
            "tags": [slug_prefix, "distributed"],
            "interviewer_brief": {
                "variants": [
                    _v(
                        f"{slug_prefix}-mvp",
                        "Cost-Optimized Core",
                        "Single-region reliable baseline",
                        "5k QPS",
                    ),
                    _v(
                        f"{slug_prefix}-scale",
                        "Global Multi-Region",
                        "Active-active low latency",
                        "250k QPS",
                    ),
                    _v(
                        f"{slug_prefix}-strict",
                        "Audit-Strict Ledger",
                        "Strong consistency & replay",
                        "40k QPS",
                    ),
                ]
            },
        }

    dup_reply = AsyncMock()
    dup_reply.content = _json.dumps(
        _make_variant_payload("Build a URL Shortener Service", "url-dup")
    )
    distinct_reply = AsyncMock()
    distinct_reply.content = _json.dumps(
        _make_variant_payload(
            "Design a Multi-Region Ledger Idempotency Engine", "ledger-idem"
        )
    )

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1) Import rejecting duplicate against built-in URL Shortener -> 409
            import_dup_res = await ac.post(
                "/api/v1/system-design/challenges/import",
                json={
                    "raw_response": f"```json\n{dup_reply.content}\n```",
                    "difficulty": "MEDIUM",
                    "allow_duplicate": False,
                },
            )
            assert import_dup_res.status_code == 409
            assert "Design a URL Shortener" in import_dup_res.json()["detail"]

            # 2) Import with malformed/incomplete variants -> 400
            bad_import = await ac.post(
                "/api/v1/system-design/challenges/import",
                json={
                    "raw_response": '{"title": "Valid Enough Title", "prompt_summary": "Summary is valid enough.", "initial_prompt": "Design something real for users.", "interviewer_brief": {"variants": [{"title": "Only One"}]}}',
                },
            )
            assert bad_import.status_code == 400

            # 3) Local AI repair retry: Attempt 1 overlaps built-in URL Shortener, Attempt 2 returns distinct challenge
            repair_ainvoke = AsyncMock(side_effect=[dup_reply, distinct_reply])
            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=AsyncMock(ainvoke=repair_ainvoke),
            ):
                repaired_res = await ac.post(
                    "/api/v1/system-design/challenges/generate",
                    json={
                        "topic": "Payment ledger idempotency",
                        "difficulty": "HARD",
                        "use_web_search": False,
                    },
                )
            assert repaired_res.status_code == 201
            assert (
                repaired_res.json()["title"]
                == "Design a Multi-Region Ledger Idempotency Engine"
            )
            assert repair_ainvoke.await_count == 2

            # 4) Residual duplicate across both AI attempts -> 409 Conflict
            stuck_ainvoke = AsyncMock(side_effect=[dup_reply, dup_reply])
            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=AsyncMock(ainvoke=stuck_ainvoke),
            ):
                conflict_res = await ac.post(
                    "/api/v1/system-design/challenges/generate",
                    json={
                        "topic": "Short links",
                        "difficulty": "MEDIUM",
                        "use_web_search": False,
                    },
                )
            assert conflict_res.status_code == 409

            # 5) Explicit allow_duplicate=True succeeds on import -> 201
            override_res = await ac.post(
                "/api/v1/system-design/challenges/import",
                json={
                    "raw_response": dup_reply.content,
                    "difficulty": "MEDIUM",
                    "allow_duplicate": True,
                },
            )
            assert override_res.status_code == 201
            assert override_res.json()["title"] == "Build a URL Shortener Service"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_canvas_builder_hints_flow_review_and_penalty_scoring(
    db_session: AsyncSession, tmp_path: Path, monkeypatch
):
    """Verify catalog API, canvas Flow JSON submission & text-LLM review, 2-tier hints, INTERVIEW block, and Stage 5 penalty."""
    import json as _json
    from unittest.mock import AsyncMock, patch

    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.main import app
    from app.services.diagram_catalog import (
        match_component_to_catalog,
        summarize_diagram_flow,
    )
    from app.services.system_design_seed import seed_system_design_challenges
    from app.services.system_design_service import SystemDesignService

    monkeypatch.setattr(
        "app.services.system_design_service.SYSTEM_DESIGN_DATA_DIR",
        tmp_path,
    )

    matched_cache = match_component_to_catalog("Redis Read-Through Cache")
    assert matched_cache["type_id"] == "distributed_cache"
    assert matched_cache["is_custom"] is False

    matched_consensus = match_component_to_catalog("Etcd Consensus Coordinator")
    assert matched_consensus["type_id"] == "consensus_store"

    matched_custom = match_component_to_catalog("Proprietary Quorum Allocation Ring")
    assert matched_custom["is_custom"] is True

    sample_summary = summarize_diagram_flow(
        {
            "nodes": [
                {"id": "n1", "type_id": "api_gateway", "label": "Edge API Gateway"},
                {
                    "id": "n2",
                    "type_id": "relational_db",
                    "label": "Postgres Primary",
                    "tech_stack": "PostgreSQL 16",
                },
                {"id": "n3", "type_id": "custom", "label": "Orphan Audit Log"},
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "protocol": "SQL Query",
                    "delivery_mode": "sync",
                    "label": "Persist short code",
                }
            ],
        }
    )
    assert sample_summary["node_count"] == 3
    assert sample_summary["edge_count"] == 1
    assert "Orphan Audit Log" in sample_summary["isolated_nodes"]
    assert any("Isolated" in d for d in sample_summary["topology_diagnostics"])

    await seed_system_design_challenges(db_session)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1) Canonical catalog endpoint returns 7 categories & 36+ blocks
            cat_res = await ac.get("/api/v1/system-design/catalog")
            assert cat_res.status_code == 200
            cat_data = cat_res.json()
            assert len(cat_data["categories"]) == 7
            assert len(cat_data["blocks"]) >= 36

            # 2) Start ADAPTIVE URL Shortener session & lock requirements ledger
            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": 1, "mode": "ADAPTIVE"},
            )
            assert start_res.status_code == 201
            session_id = start_res.json()["id"]

            lock_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Create short URL", "301 Redirect"],
                    "non_functional_requirements": [
                        "<50ms p99 redirect",
                        "99.99% availability",
                    ],
                    "scale_estimates": {"dau": "10M", "writes_per_sec": "116"},
                    "out_of_scope": ["Custom analytics BI"],
                    "assumptions": [],
                    "unresolved_questions": [],
                    "notes": "Read heavy 100:1",
                    "is_locked": True,
                },
            )
            assert lock_res.status_code == 200

            # 3) Request 1st next_component hint -> reveals 1 component at 0-pt deduction (Coached)
            hint1 = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/hint",
                json={"hint_mode": "next_component", "current_nodes": []},
            )
            assert hint1.status_code == 200
            h1_data = hint1.json()
            assert len(h1_data["newly_revealed"]) == 1
            assert h1_data["hints_used_count"] == 1
            assert h1_data["penalty_points"] == 0.0
            assert h1_data["is_coached"] is True

            # Calling reveal_all works in any mode and remains idempotent at 0.0 penalty
            reveal_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/hint",
                json={"hint_mode": "reveal_all", "current_nodes": []},
            )
            assert reveal_res.status_code == 200
            rev_data = reveal_res.json()
            assert rev_data["revealed_all_bank"] is True
            assert rev_data["penalty_points"] == 0.0
            assert rev_data["expected_paths"]
            first_step = rev_data["expected_paths"][0]["steps"][0]
            assert isinstance(first_step, dict)
            assert "source_label" in first_step and "target_label" in first_step

            repeat_reveal = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/hint",
                json={"hint_mode": "reveal_all", "current_nodes": []},
            )
            assert repeat_reveal.status_code == 200
            assert repeat_reveal.json()["penalty_points"] == 0.0

            # 4) Reject empty canvas submission
            empty_canvas = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/canvas",
                json={"nodes": [], "edges": [], "notes": ""},
            )
            assert empty_canvas.status_code == 400

            # 5) Submit Canvas Flow JSON revision (catalog blocks + custom block)
            canvas_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/canvas",
                json={
                    "nodes": [
                        {
                            "id": "n-gw",
                            "type_id": "api_gateway",
                            "label": "API Gateway",
                            "category": "traffic_api",
                            "icon": "door-open",
                            "tech_stack": "Kong",
                            "notes": "Rate limits writes",
                            "is_custom": False,
                            "position": {"x": 80, "y": 80},
                        },
                        {
                            "id": "n-cache",
                            "type_id": "distributed_cache",
                            "label": "Redis Cache",
                            "category": "caching_memory",
                            "icon": "bolt",
                            "tech_stack": "Redis 7 Cluster",
                            "notes": "Hot short codes",
                            "is_custom": False,
                            "position": {"x": 320, "y": 80},
                        },
                        {
                            "id": "n-custom",
                            "type_id": "custom",
                            "label": "Base62 Allocator Ring",
                            "category": "compute_services",
                            "icon": "hash",
                            "tech_stack": "Go Worker + Etcd",
                            "notes": "Collision-free token leases",
                            "is_custom": True,
                            "position": {"x": 560, "y": 80},
                        },
                    ],
                    "edges": [
                        {
                            "id": "e1",
                            "source": "n-gw",
                            "target": "n-cache",
                            "protocol": "Redis RESP",
                            "delivery_mode": "sync",
                            "label": "Redirect lookup",
                        },
                        {
                            "id": "e2",
                            "source": "n-gw",
                            "target": "n-custom",
                            "protocol": "gRPC",
                            "delivery_mode": "sync",
                            "label": "Allocate short key",
                        },
                    ],
                    "notes": "Sub-20ms redirect path backed by Redis Cluster.",
                },
            )
            assert canvas_res.status_code == 201
            c_session = canvas_res.json()
            assert len(c_session["diagrams_metadata"]) == 1
            d_meta = c_session["diagrams_metadata"][0]
            assert d_meta["diagram_kind"] == "canvas"
            assert d_meta["node_count"] == 3
            assert d_meta["edge_count"] == 2

            # Fetch stored Flow JSON back via GET /flow
            flow_get = await ac.get(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/1/flow"
            )
            assert flow_get.status_code == 200
            assert len(flow_get.json()["nodes"]) == 3
            assert flow_get.json()["flow_summary"]["edge_count"] == 2

            # 6) Run Stage 3 Canvas Review via text-LLM path (no image bytes / VLM)
            review_reply = AsyncMock()
            review_reply.content = _json.dumps(
                {
                    "interpreted_components": [
                        "API Gateway (Kong)",
                        "Redis Cache (Redis 7 Cluster)",
                        "Base62 Allocator Ring",
                    ],
                    "interpreted_data_flows": [
                        "API Gateway -> Redis Cache [Redis RESP, sync]",
                        "API Gateway -> Base62 Allocator Ring [gRPC, sync]",
                    ],
                    "visual_clarifications_needed": [],
                    "strengths": [
                        "Clear Redis hot-key lookup and Base62 key separation."
                    ],
                    "missing_components": ["Primary SQL Store"],
                    "bottlenecks_and_spofs": ["Redis cache miss durability"],
                    "unnecessary_complexity": [],
                    "requirement_gaps": [],
                    "overall_impression": "Clean v1 canvas topology.",
                    "suggested_defence_topics": [
                        "What happens when a cold short link misses Redis?"
                    ],
                }
            )
            prepared_ctx = await SystemDesignService.prepare_diagram_review_context(
                db_session, session_id=session_id, diagram_version=1
            )
            assert prepared_ctx["diagram_kind"] == "canvas"
            review_ainvoke = AsyncMock(return_value=review_reply)
            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=AsyncMock(ainvoke=review_ainvoke),
            ):
                inference = await SystemDesignService.run_diagram_vlm_inference(
                    db_session, prepared_ctx
                )
            # Confirm message sent to model is pure text (str), NOT image_url list!
            sent_messages = review_ainvoke.await_args.args[0]
            assert isinstance(sent_messages[1].content, str)
            assert "TOPOLOGY SUMMARY" in sent_messages[1].content

            await SystemDesignService.persist_architecture_review(
                db_session, session_id=session_id, review_dict=inference["review"]
            )

            # Seed one candidate defence turn so import_frontier_evaluation preconditions pass
            session_obj = await SystemDesignService._get_session_for_update(
                db_session, session_id
            )
            session_obj.stage = "DEFENCE"
            session_obj.defence_transcript = [
                {
                    "turn_index": 1,
                    "role": "interviewer",
                    "content": "What happens on cache miss?",
                    "stage": "DEFENCE",
                    "timestamp": "2026-11-15T23:00:00Z",
                },
                {
                    "turn_index": 2,
                    "role": "candidate",
                    "content": "It falls back to Postgres read replica and populates Redis with TTL.",
                    "stage": "DEFENCE",
                    "assisted": False,
                    "timestamp": "2026-11-15T23:01:00Z",
                },
            ]
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(session_obj, "defence_transcript")
            await db_session.commit()

            # 7) Import 90/100 scorecard -> net score must reflect -18.0 hint penalty (= 72.0 / INTERVIEW_READY)
            dimensions = [
                "Requirements Clarity",
                "Scope & Prioritization",
                "Back-of-the-Envelope Estimation",
                "API & Interface Design",
                "Data Model & Storage Choice",
                "High-Level Architecture",
                "Scalability & Partitioning",
                "Reliability & Fault Tolerance",
                "Caching & Latency Optimization",
                "Right-Sizing & Simplicity (YAGNI)",
                "Trade-off Justification",
                "Defence Communication Under Pressure",
            ]
            # 12 * 4.5 isn't int; use six 5s + six 4s -> sum=54 -> 54/60*100 = 90.0
            rubric_rows = [
                {
                    "dimension": dim,
                    "score": 5 if idx < 6 else 4,
                    "evidence": f"Evidence observed for {dim}.",
                    "critique": f"Solid execution on {dim}.",
                }
                for idx, dim in enumerate(dimensions)
            ]
            import_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/import-evaluation",
                json={
                    "raw_response": _json.dumps(
                        {
                            "overall_score": 90.0,
                            "readiness_rating": "STRONG_HIRE",
                            "executive_summary": "Strong design.",
                            "rubric_scores": rubric_rows,
                            "key_strengths": ["Fast read path"],
                            "critical_gaps": ["Add SQL backup"],
                            "recommended_next_steps": ["Add DB primary/replica nodes"],
                        }
                    )
                },
            )
            assert import_res.status_code == 200
            final_data = import_res.json()
            assert final_data["overall_score"] == 90.0
            assert final_data["readiness_rating"] == "STRONG_HIRE"
            assert final_data["final_evaluation"]["raw_score"] == 90.0
            assert final_data["final_evaluation"]["guidance_penalty"] == 0.0
            assert final_data["final_evaluation"]["assistance_mode"] == "COACHED"
            assert final_data["final_evaluation"]["xp_earned"] == 100
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_live_turn_by_turn_ledger_sync_and_clean_reply(db_session: AsyncSession):
    """Turn-by-turn stakeholder replies merge <ledger_json> updates into the ledger and strip tags from transcript."""
    import json
    from unittest.mock import AsyncMock, MagicMock, patch

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/url-shortener")
            challenge_id = ch_res.json()["id"]
            sess_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "ADAPTIVE"},
            )
            session_id = sess_res.json()["id"]

            # Seed an existing manual edit so we verify turn-by-turn merge preserves user edits
            seed_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Custom manual requirement"],
                    "non_functional_requirements": [],
                    "scale_estimates": {"custom_quota": "10 req/min per IP"},
                    "out_of_scope": [],
                    "assumptions": [],
                    "unresolved_questions": [],
                    "notes": "Keep manual notes",
                    "is_locked": False,
                },
            )
            assert seed_res.status_code == 200

            turn_1_reply = (
                "Expect 80M MAU, ~20M DAU, and 12,000 peak redirect QPS with p99 under 30ms.\n"
                "<ledger_json>\n"
                + json.dumps(
                    {
                        "functional_requirements": [
                            "custom manual requirement",  # case-insensitive duplicate ignored
                            "Redirect short links via 302",
                        ],
                        "non_functional_requirements": ["p99 redirect latency < 30ms"],
                        "scale_estimates": {"peak_redirect_qps": "12,000 QPS"},
                        "out_of_scope": ["Custom SSL vanity certs"],
                        "assumptions": [
                            "Eventual consistency acceptable for click counts"
                        ],
                        "unresolved_questions": [
                            "Do anonymous users get custom aliases?"
                        ],
                    }
                )
                + "\n</ledger_json>"
            )

            turn_2_reply = "Yes, anonymous callers get random 7-char Base62 codes."

            replies = iter([turn_1_reply, turn_2_reply])

            async def fake_invoke(*_args, **_kwargs):
                return MagicMock(content=next(replies))

            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    new=AsyncMock(return_value=MagicMock()),
                ),
                patch(
                    "app.services.system_design_service._invoke_llm_adaptive",
                    side_effect=fake_invoke,
                ),
            ):
                res1 = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={
                        "message": "What DAU, QPS, and redirect latency SLAs do we need?"
                    },
                )
                assert res1.status_code == 200
                data1 = res1.json()
                assert (
                    "<ledger_json>"
                    not in data1["requirements_transcript"][-1]["content"]
                )
                assert (
                    "12,000 peak redirect QPS"
                    in data1["requirements_transcript"][-1]["content"]
                )
                ledger1 = data1["requirements_ledger"]
                assert ledger1["functional_requirements"] == [
                    "Custom manual requirement",
                    "Redirect short links via 302",
                ]
                assert ledger1["non_functional_requirements"] == [
                    "p99 redirect latency < 30ms"
                ]
                assert ledger1["scale_estimates"] == {
                    "custom_quota": "10 req/min per IP",
                    "peak_redirect_qps": "12,000 QPS",
                }
                assert ledger1["out_of_scope"] == ["Custom SSL vanity certs"]
                assert ledger1["assumptions"] == [
                    "Eventual consistency acceptable for click counts"
                ]
                assert ledger1["unresolved_questions"] == [
                    "Do anonymous users get custom aliases?"
                ]
                assert ledger1["notes"] == "Keep manual notes"

                # Turn 2 has no <ledger_json> trailer -> existing ledger must stay intact
                res2 = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/requirements/message",
                    json={"message": "Are anonymous users allowed custom aliases?"},
                )
                assert res2.status_code == 200
                data2 = res2.json()
                assert data2["requirements_transcript"][-1]["content"] == turn_2_reply
                assert data2["requirements_ledger"] == ledger1
    finally:
        app.dependency_overrides.clear()


def test_diagram_catalog_queue_vs_flink_and_blueprint_synthesis():
    """Verify queue descriptions avoid Flink mis-mapping, composite names split, and topology catches broken edges."""
    queue_match = match_component_to_catalog(
        "Async queue / stream for click analytics aggregation"
    )
    assert queue_match["type_id"] == "message_queue"
    assert queue_match["type_id"] != "stream_processor"

    brief = {
        "expected_components": [
            "API Gateway / Load Balancer",
            "Stateless App Service",
            "Async queue for click analytics aggregation",
            "Primary Relational DB",
        ]
    }
    ledger = {
        "functional_requirements": [
            "Optional link expiration TTL with automatic cleanup",
        ],
        "non_functional_requirements": [
            "Malicious URL blocklist check before redirect/shorten",
            "Read-heavy workload (100:1 read/write ratio) < 30ms p99",
        ],
    }

    blueprint = resolve_challenge_blueprint(brief, ledger)
    type_ids = [item["type_id"] for item in blueprint["required_components"]]
    assert "api_gateway" in type_ids
    assert "load_balancer" in type_ids
    assert "message_queue" in type_ids
    assert "stream_processor" not in type_ids
    assert "content_filter" in type_ids
    assert "scheduler" in type_ids
    assert "read_replica" in type_ids
    assert all(item.get("why_required") for item in blueprint["required_components"])
    assert len(blueprint["expected_paths"]) >= 2

    # Reproduce Screenshot 1 broken topology: DB -> Redis, CDN -> Redis, Flink -> ID Gen
    flow_payload = {
        "nodes": [
            {"id": "n1", "type_id": "cdn", "label": "CDN / Edge Cache"},
            {
                "id": "n2",
                "type_id": "distributed_cache",
                "label": "Distributed Cache (Redis)",
            },
            {"id": "n3", "type_id": "relational_db", "label": "Primary Relational DB"},
            {
                "id": "n4",
                "type_id": "stream_processor",
                "label": "Stream Processor (Flink)",
            },
            {
                "id": "n5",
                "type_id": "id_generator",
                "label": "Unique ID / Key Generator",
                "notes": "",
            },
        ],
        "edges": [
            {"id": "e1", "source": "n3", "target": "n2", "label": "feeds cache"},
            {"id": "e2", "source": "n1", "target": "n2", "label": "reads redis"},
            {"id": "e3", "source": "n4", "target": "n5", "label": "triggers id gen"},
        ],
        "notes": "",
    }
    topo = evaluate_canvas_topology(flow_payload, blueprint, brief)
    finding_titles = " | ".join(f["title"] for f in topo["findings"])
    assert "DB" in finding_titles or "Cache" in finding_titles
    assert "CDN" in finding_titles
    assert "Flink" in finding_titles or "Stream" in finding_titles
    assert "ID" in finding_titles


@pytest.mark.asyncio
async def test_reveal_requirements_coach_chat_alternatives_and_solo_xp(
    db_session: AsyncSession,
):
    """Test /requirements/reveal shortcut, /diagrams/coach-chat actions, valid DB/queue alternatives, and Solo 150 XP."""
    import json as _json
    from unittest.mock import AsyncMock, MagicMock, patch

    from sqlalchemy.orm.attributes import flag_modified

    from app.services.system_design_service import SystemDesignService

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            challenge_res = await ac.get(
                "/api/v1/system-design/challenges/url-shortener"
            )
            assert challenge_res.status_code == 200
            challenge_id = challenge_res.json()["id"]

            # 1) Session A: Reveal Requirements & jump straight to DESIGN + Studio Coach Chat
            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={
                    "challenge_id": challenge_id,
                    "mode": "ADAPTIVE",
                    "variant_id": "public-consumer-shortener",
                },
            )
            assert start_res.status_code == 201
            session_id = start_res.json()["id"]

            reveal_req = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/requirements/reveal",
                json={"lock_and_proceed": True},
            )
            assert reveal_req.status_code == 200
            rev_sess = reveal_req.json()
            assert rev_sess["stage"] == "DESIGN"
            assert rev_sess["requirements_ledger"]["is_locked"] is True
            assert len(rev_sess["requirements_ledger"]["functional_requirements"]) >= 1
            assert rev_sess["diagram_guidance"]["requirements_revealed"] is True
            assert rev_sess["diagram_guidance"]["is_coached"] is True

            # Valid alternatives (NoSQL KV + Event Stream) produce info card rather than missing errors
            alt_topo = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/hint",
                json={
                    "hint_mode": "check_topology",
                    "current_nodes": [
                        {
                            "id": "kv",
                            "type_id": "nosql_kv",
                            "label": "DynamoDB KV Store",
                        },
                        {
                            "id": "kafka",
                            "type_id": "event_stream",
                            "label": "Kafka Click Stream",
                        },
                    ],
                    "current_edges": [],
                },
            )
            assert alt_topo.status_code == 200
            alt_findings = alt_topo.json()["topology_feedback"]["findings"]
            assert any(
                f["severity"] == "info" and "Alternative" in f["title"]
                for f in alt_findings
            )

            # Coach chat returns grounded reply + clickable Apply actions
            mock_msg = MagicMock()
            mock_msg.content = "Connect API Gateway -> Stateless App Service -> ID Generator -> Storage."
            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    new_callable=AsyncMock,
                    return_value=MagicMock(),
                ),
                patch(
                    "app.services.system_design_service._invoke_llm_adaptive",
                    new_callable=AsyncMock,
                    return_value=mock_msg,
                ),
            ):
                chat_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/diagrams/coach-chat",
                    json={
                        "message": "Show me how to structure the Write Path.",
                        "current_nodes": [],
                        "current_edges": [],
                        "current_notes": "",
                    },
                )
            assert chat_res.status_code == 200
            chat_data = chat_res.json()
            assert "Stateless App Service" in chat_data["reply"]
            assert len(chat_data["suggested_actions"]) >= 1
            first_act = chat_data["suggested_actions"][0]
            assert len(first_act["blocks"]) >= 2
            assert len(first_act["edges"]) >= 1
            assert len(chat_data["session"]["diagram_guidance"]["coach_messages"]) == 2

            # 2) Session B: Pure Solo run earns 150 XP with 0 guidance penalty
            solo_start = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "ADAPTIVE"},
            )
            assert solo_start.status_code == 201
            solo_id = solo_start.json()["id"]
            await ac.put(
                f"/api/v1/system-design/sessions/{solo_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Shorten URLs"],
                    "non_functional_requirements": ["<50ms p99"],
                    "is_locked": True,
                },
            )
            await ac.post(
                f"/api/v1/system-design/sessions/{solo_id}/diagrams/canvas",
                json={
                    "nodes": [
                        {
                            "id": "n1",
                            "type_id": "app_service",
                            "label": "App Service",
                        }
                    ],
                    "edges": [],
                },
            )
            solo_obj = await SystemDesignService._get_session_for_update(
                db_session, solo_id
            )
            solo_obj.architecture_reviews = [
                {
                    "diagram_version": 1,
                    "summary": "Solo canvas looks solid.",
                    "strengths": ["Clear gateway and service"],
                    "bottlenecks_and_spofs": [],
                    "missing_components": [],
                    "requirement_gaps": [],
                    "unnecessary_complexity": [],
                    "interpreted_components": ["Stateless App Service"],
                    "interpreted_data_flows": [],
                    "visual_clarifications_needed": [],
                    "created_at": "2026-11-16T00:00:00Z",
                }
            ]
            flag_modified(solo_obj, "architecture_reviews")
            solo_obj.stage = "DEFENCE"
            solo_obj.defence_transcript = [
                {
                    "turn_index": 1,
                    "role": "candidate",
                    "content": "Unassisted architectural defence.",
                    "stage": "DEFENCE",
                    "assisted": False,
                    "timestamp": "2026-11-16T00:00:00Z",
                }
            ]
            flag_modified(solo_obj, "defence_transcript")
            await db_session.commit()

            dimensions = [
                "Requirements Clarity",
                "Scope & Prioritization",
                "Back-of-the-Envelope Estimation",
                "API & Interface Design",
                "Data Model & Storage Choice",
                "High-Level Architecture",
                "Scalability & Partitioning",
                "Reliability & Fault Tolerance",
                "Caching & Latency Optimization",
                "Right-Sizing & Simplicity (YAGNI)",
                "Trade-off Justification",
                "Defence Communication Under Pressure",
            ]
            rubric_rows = [
                {
                    "dimension": dim,
                    "score": 5 if idx < 6 else 4,
                    "evidence": f"Solo evidence for {dim}.",
                    "critique": f"Solid execution on {dim}.",
                }
                for idx, dim in enumerate(dimensions)
            ]
            solo_eval = await ac.post(
                f"/api/v1/system-design/sessions/{solo_id}/import-evaluation",
                json={
                    "raw_response": _json.dumps(
                        {
                            "overall_score": 90.0,
                            "readiness_rating": "STRONG_HIRE",
                            "executive_summary": "Solo design excellence.",
                            "rubric_scores": rubric_rows,
                            "key_strengths": ["Independent design"],
                            "critical_gaps": ["None major"],
                            "recommended_next_steps": ["Keep practicing"],
                        }
                    )
                },
            )
            assert solo_eval.status_code == 200
            solo_data = solo_eval.json()
            assert solo_data["overall_score"] == 90.0
            assert solo_data["final_evaluation"]["assistance_mode"] == "SOLO"
            assert solo_data["final_evaluation"]["xp_earned"] == 150
    finally:
        app.dependency_overrides.clear()
