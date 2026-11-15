from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app


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
                json={"challenge_id": challenge["id"], "mode": "INTERVIEW"},
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
            assert "ADAPTIVE INTERVIEWER MODE" in first_sys
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
