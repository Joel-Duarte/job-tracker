import base64
import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.system_design_service import (
    DEFAULT_RUBRIC_DIMENSIONS,
)

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake-png-payload"
FAKE_WEBP_BYTES = b"RIFF\x18\x00\x00\x00WEBPfake-webp-payload"


def _build_full_rubric_scores(scores: list[int] | None = None) -> list[dict]:
    values = scores or [4] * len(DEFAULT_RUBRIC_DIMENSIONS)
    return [
        {
            "dimension": dim,
            "score": values[idx],
            "evidence": f"Candidate addressed {dim} during session ledger and diagram review.",
            "critique": f"Document concrete failure metrics for {dim} to advance to Staff depth.",
        }
        for idx, dim in enumerate(DEFAULT_RUBRIC_DIMENSIONS)
    ]


def _build_valid_eval_payload(scores: list[int] | None = None, **overrides) -> dict:
    rubric = _build_full_rubric_scores(scores)
    overall = round((sum(item["score"] for item in rubric) / 60.0) * 100.0, 1)
    if overall >= 88.0:
        rating = "STRONG_HIRE"
    elif overall >= 70.0:
        rating = "INTERVIEW_READY"
    elif overall >= 50.0:
        rating = "DEVELOPING"
    else:
        rating = "NEEDS_PRACTICE"
    payload = {
        "overall_score": overall,
        "readiness_rating": rating,
        "executive_summary": "Cohesive Staff-level baseline with well-bounded trade-offs across diagram and defence.",
        "rubric_scores": rubric,
        "key_strengths": [
            "Separated control plane API from high-throughput object egress"
        ],
        "critical_gaps": ["Quantify read-replica promotion failover budget under load"],
        "recommended_next_steps": [
            "Annotate queue backpressure and cache eviction bounds in diagram v2"
        ],
    }
    payload.update(overrides)
    return payload


async def _advance_session_to_defence(
    ac: AsyncClient,
    session_id: int,
    diagram_bytes: bytes = FAKE_PNG_BYTES,
    filename: str = "v1.png",
    mime_type: str = "image/png",
) -> None:
    lock_res = await ac.put(
        f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
        json={
            "functional_requirements": ["Stream audio tracks", "Playlists"],
            "non_functional_requirements": ["p99 < 300ms", "99.9% availability"],
            "scale_estimates": {"dau": "30000"},
            "out_of_scope": ["Podcasts"],
            "notes": "Baseline constraints locked",
            "is_locked": True,
        },
    )
    assert lock_res.status_code == 200

    up_res = await ac.post(
        f"/api/v1/system-design/sessions/{session_id}/diagrams",
        files={"file": (filename, diagram_bytes, mime_type)},
        data={"notes": "Initial CDN + Postgres design"},
    )
    assert up_res.status_code == 201

    mock_review_res = AsyncMock()
    mock_review_res.content = json.dumps(
        {
            "interpreted_components": ["API", "S3", "CDN", "Postgres"],
            "interpreted_data_flows": ["Client -> CDN -> S3"],
            "visual_clarifications_needed": [],
            "strengths": ["Offloads audio egress to CDN"],
            "missing_components": [],
            "bottlenecks_and_spofs": ["Single primary Postgres instance"],
            "unnecessary_complexity": [],
            "requirement_gaps": [],
            "overall_impression": "Solid right-sized baseline.",
            "suggested_defence_topics": [
                "How do you handle primary Postgres failover?"
            ],
        }
    )
    mock_defence_res = AsyncMock()
    mock_defence_res.content = (
        "Good mitigation strategy on standby promotion and connection draining."
    )

    with patch("app.services.system_design_service.get_task_chat_model") as mock_get:
        mock_model = AsyncMock()
        mock_model.ainvoke.side_effect = [mock_review_res, mock_defence_res]
        mock_get.return_value = mock_model

        rev_res = await ac.post(f"/api/v1/system-design/sessions/{session_id}/review")
        assert rev_res.status_code == 202
        def_res = await ac.post(
            f"/api/v1/system-design/sessions/{session_id}/defence/message",
            json={
                "message": "We run synchronous WAL standby with automated health-checked promotion."
            },
        )
        assert def_res.status_code == 200


@pytest.mark.asyncio
async def test_diagram_upload_validation_and_revision_versioning(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Validates image magic bytes, increments v1 -> v2, and serves stored images cleanly."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "INTERVIEW"},
            )
            session_id = start_res.json()["id"]

            # Diagram upload and review before locking requirements must fail with 400
            unlocked_upload = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("early.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Too early"},
            )
            assert unlocked_upload.status_code == 400

            no_diagram_review = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/review"
            )
            assert no_diagram_review.status_code == 400

            # Lock requirements before entering DESIGN stage
            lock_res = await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Stream audio tracks"],
                    "non_functional_requirements": ["Low latency"],
                    "scale_estimates": {"dau": "30000"},
                    "out_of_scope": [],
                    "is_locked": True,
                },
            )
            assert lock_res.status_code == 200
            assert lock_res.json()["stage"] == "DESIGN"

            # Invalid binary must fail with 400
            bad_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("notes.txt", b"not an image file", "text/plain")},
                data={"notes": "Invalid attempt"},
            )
            assert bad_res.status_code == 400

            # Upload v1 PNG
            v1_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("arch.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Initial CDN + Postgres architecture"},
            )
            assert v1_res.status_code == 201
            v1_data = v1_res.json()
            assert v1_data["stage"] == "DESIGN"
            assert len(v1_data["diagrams_metadata"]) == 1
            assert v1_data["diagrams_metadata"][0]["version"] == 1
            assert v1_data["diagrams_metadata"][0]["filename"] == "v1.png"
            assert v1_data["diagrams_metadata"][0]["mime_type"] == "image/png"

            # Retrieve v1 bytes
            img1 = await ac.get(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/1/image"
            )
            assert img1.status_code == 200
            assert img1.headers["content-type"].startswith("image/png")
            assert img1.content == FAKE_PNG_BYTES

            # Upload v2 WebP
            v2_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("pasted.webp", FAKE_WEBP_BYTES, "image/webp")},
                data={"notes": "Simplified queues after review"},
            )
            assert v2_res.status_code == 201
            v2_meta = v2_res.json()["diagrams_metadata"]
            assert [d["version"] for d in v2_meta] == [1, 2]
            assert v2_meta[1]["filename"] == "v2.webp"

            img2 = await ac.get(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/2/image"
            )
            assert img2.status_code == 200
            assert img2.headers["content-type"].startswith("image/webp")
            assert img2.content == FAKE_WEBP_BYTES
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multimodal_architecture_review_via_evaluation_worker(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Queue-backed review packages base64 image_url, stores IntakeEvaluationTaskModel, and parses review."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "INTERVIEW"},
            )
            session_id = start_res.json()["id"]

            await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Stream audio tracks", "Playlists"],
                    "non_functional_requirements": ["Playback start < 300ms"],
                    "scale_estimates": {"dau": "30000", "tracks": "500000"},
                    "out_of_scope": ["Podcasts"],
                    "notes": "Lean growth-stage team",
                    "is_locked": True,
                },
            )

            await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("v1.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Draft 1"},
            )
            await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("v2.webp", FAKE_WEBP_BYTES, "image/webp")},
                data={"notes": "Draft 2 with CDN and multi-region Kafka"},
            )

            review_json = """{
                "interpreted_components": ["Client App", "API Gateway", "CDN", "S3", "Kafka Cluster"],
                "interpreted_data_flows": ["Client -> CDN -> S3 for audio segments"],
                "visual_clarifications_needed": ["Confirm whether arrow between Client and S3 uses signed URLs or proxies via API."],
                "strengths": ["Offloads heavy audio egress to S3 + CDN"],
                "missing_components": ["Redis cache for hot metadata/playlists"],
                "bottlenecks_and_spofs": ["Single un-replicated metadata database"],
                "unnecessary_complexity": ["Multi-region Kafka cluster is over-engineered for 30,000 DAU"],
                "requirement_gaps": ["No playback search indexing strategy specified"],
                "overall_impression": "Good CDN offloading, but Kafka adds unjustified operational weight for 100k registered users.",
                "suggested_defence_topics": ["Why include a multi-region Kafka cluster when play volume is only 30k DAU?"]
            }"""
            mock_review_res = AsyncMock()
            mock_review_res.content = review_json

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = mock_review_res
                mock_get_model.return_value = mock_model

                rev_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/review"
                )

            assert rev_res.status_code == 202
            queued_payload = rev_res.json()
            assert queued_payload["active_task_id"] is not None
            assert queued_payload["active_task_status"] == "QUEUED"
            assert queued_payload["active_task_type"] == "SYSTEM_DESIGN_REVIEW"

            session_res = await ac.get(f"/api/v1/system-design/sessions/{session_id}")
            assert session_res.status_code == 200
            assert "interviewer_brief" not in session_res.text
            assert "over_engineering_traps" not in session_res.text

            rev_data = session_res.json()
            assert rev_data["stage"] == "REVIEW"
            assert rev_data["active_task_status"] is None
            assert len(rev_data["architecture_reviews"]) == 1
            review = rev_data["architecture_reviews"][0]
            assert review["diagram_version"] == 2
            assert review["visual_clarifications_needed"] == [
                "Confirm whether arrow between Client and S3 uses signed URLs or proxies via API."
            ]
            assert (
                "Single un-replicated metadata database"
                in (review["bottlenecks_and_spofs"])
            )
            assert any("Kafka" in item for item in review["unnecessary_complexity"])

            # Turn 1 in Stage E defence should be seeded automatically
            assert len(rev_data["defence_transcript"]) == 1
            assert rev_data["defence_transcript"][0]["role"] == "interviewer"
            assert "Kafka" in rev_data["defence_transcript"][0]["content"]

            # Inspect multimodal HumanMessage sent to LLM
            assert mock_get_model.call_args.kwargs["task_type"] == (
                "SYSTEM_DESIGN_REVIEWER"
            )
            sent_messages = mock_model.ainvoke.call_args.args[0]
            assert isinstance(sent_messages[0], SystemMessage)
            assert isinstance(sent_messages[1], HumanMessage)
            content_parts = sent_messages[1].content
            assert isinstance(content_parts, list)
            expected_uri = "data:image/webp;base64," + base64.b64encode(
                FAKE_WEBP_BYTES
            ).decode("ascii")
            assert content_parts[1]["type"] == "image_url"
            assert content_parts[1]["image_url"]["url"] == expected_uri

            # Verify queue record persisted in IntakeEvaluationTaskModel
            task_stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.task_type == "SYSTEM_DESIGN_REVIEW"
            )
            task_row = (await db_session.execute(task_stmt)).scalar_one()
            assert task_row.status == "COMPLETED"
            assert task_row.stage == "COMPLETE"
            assert task_row.result_json["session_id"] == session_id
            assert task_row.result_json["diagram_version"] == 2
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_interactive_defence_mode_conversation(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Defence endpoint transitions stage to DEFENCE, injects review+ledger context, and appends turns."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "INTERVIEW"},
            )
            session_id = start_res.json()["id"]

            await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Audio streaming"],
                    "non_functional_requirements": ["99.9% availability"],
                    "scale_estimates": {"dau": "30000"},
                    "out_of_scope": [],
                    "is_locked": True,
                },
            )
            await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("v1.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Draft 1"},
            )

            mock_review_res = AsyncMock()
            mock_review_res.content = """{
                "interpreted_components": ["API", "S3", "CDN", "Postgres"],
                "interpreted_data_flows": ["Client -> API -> Postgres"],
                "visual_clarifications_needed": [],
                "strengths": ["Simple monolith"],
                "missing_components": [],
                "bottlenecks_and_spofs": ["API proxying raw audio streams"],
                "unnecessary_complexity": [],
                "requirement_gaps": [],
                "overall_impression": "Check audio delivery data path.",
                "suggested_defence_topics": ["Do your API servers proxy audio bytes or do clients fetch directly from CDN signed URLs?"]
            }"""

            mock_defence_res = AsyncMock()
            mock_defence_res.content = (
                "<think>Candidate clarified signed URLs cleanly.</think>"
                "Makes sense—using short-lived CDN signed URLs keeps the API out of the hot byte path. "
                "If a playlist contains restricted tracks, how long should signed URLs live before expiry?"
            )

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.side_effect = [mock_review_res, mock_defence_res]
                mock_get_model.return_value = mock_model

                await ac.post(f"/api/v1/system-design/sessions/{session_id}/review")
                def_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={
                        "message": "Clients get a short-lived CloudFront signed URL from the API, then stream chunks straight from CDN."
                    },
                )

            assert def_res.status_code == 200
            assert "interviewer_brief" not in def_res.text
            assert "<think>" not in def_res.text

            def_data = def_res.json()
            assert def_data["stage"] == "DEFENCE"
            turns = def_data["defence_transcript"]
            assert len(turns) == 3
            assert turns[0]["role"] == "interviewer"
            assert turns[1]["role"] == "candidate"
            assert turns[2]["role"] == "interviewer"
            assert (
                "CloudFront signed URLs" in turns[2]["content"]
                or "signed URLs" in turns[2]["content"]
            )

            second_call_msgs = mock_model.ainvoke.call_args_list[1].args[0]
            assert isinstance(second_call_msgs[0], SystemMessage)
            assert "API proxying raw audio streams" in second_call_msgs[0].content
            assert "30000" in second_call_msgs[0].content
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_final_evaluation_stage_f_evidence_backed_rubric(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Stage F evaluate endpoint executes queue-backed evaluation with non-blank evidence."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id, "mode": "INTERVIEW"},
            )
            session_id = start_res.json()["id"]

            await _advance_session_to_defence(ac, session_id)

            scores = [4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 4, 4]  # sum=50 -> 83.3
            payload_json = json.dumps(_build_valid_eval_payload(scores=scores))
            mock_eval_res = AsyncMock()
            mock_eval_res.content = (
                f"<think>Checking all session artifacts.</think>{payload_json}"
            )

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = mock_eval_res
                mock_get_model.return_value = mock_model

                eval_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/evaluate"
                )

            assert eval_res.status_code == 202
            queued_eval = eval_res.json()
            assert queued_eval["active_task_id"] is not None
            assert queued_eval["active_task_status"] == "QUEUED"
            assert queued_eval["active_task_type"] == "SYSTEM_DESIGN_EVALUATION"

            done_res = await ac.get(f"/api/v1/system-design/sessions/{session_id}")
            assert done_res.status_code == 200
            assert "interviewer_brief" not in done_res.text
            assert "<think>" not in done_res.text

            eval_data = done_res.json()
            assert eval_data["stage"] == "COMPLETED"
            assert eval_data["status"] == "COMPLETED"
            assert eval_data["overall_score"] == 83.3
            assert eval_data["readiness_rating"] == "INTERVIEW_READY"
            assert eval_data["completed_at"] is not None

            final_eval = eval_data["final_evaluation"]
            assert len(final_eval["rubric_scores"]) == 12
            for item in final_eval["rubric_scores"]:
                assert 1 <= item["score"] <= 5
                assert len(item["evidence"].strip()) >= 5
                assert len(item["critique"].strip()) >= 5

            task_stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.task_type == "SYSTEM_DESIGN_EVALUATION"
            )
            task_row = (await db_session.execute(task_stmt)).scalar_one()
            assert task_row.status == "COMPLETED"
            assert task_row.stage == "COMPLETE"
            assert task_row.result_json["session_id"] == session_id
            assert task_row.result_json["overall_score"] == 83.3
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_web_search_grounding_and_frontier_packet_round_trip(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """Review/Defence web search injects grounded snippets and Frontier Packet supports export+import."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]

            start_res = await ac.post(
                "/api/v1/system-design/sessions",
                json={"challenge_id": challenge_id},
            )
            session_id = start_res.json()["id"]

            await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Audio range streaming"],
                    "non_functional_requirements": ["99.9% availability"],
                    "scale_estimates": {"dau": "30000"},
                    "out_of_scope": [],
                    "is_locked": True,
                },
            )

            await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("v1.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "HLS segments via CDN"},
            )

            mock_review_res = AsyncMock()
            mock_review_res.content = """{
                "interpreted_components": ["API", "Object Storage", "CDN"],
                "interpreted_data_flows": ["Client -> CDN"],
                "visual_clarifications_needed": [],
                "strengths": ["Separates metadata API from CDN byte path"],
                "missing_components": [],
                "bottlenecks_and_spofs": ["Single primary Postgres"],
                "unnecessary_complexity": [],
                "requirement_gaps": [],
                "overall_impression": "Clean CDN-first baseline.",
                "suggested_defence_topics": ["How do you handle primary DB failover?"]
            }"""
            mock_defence_res = AsyncMock()
            mock_defence_res.content = "Good rationale on streaming failover."

            mock_model = AsyncMock()
            mock_model.ainvoke.side_effect = [mock_review_res, mock_defence_res]

            with (
                patch(
                    "app.services.system_design_service.get_task_chat_model",
                    return_value=mock_model,
                ),
                patch(
                    "app.services.web_search.search_web",
                    new=AsyncMock(
                        return_value=[
                            {
                                "title": "Audio CDN Caching Patterns",
                                "snippet": "Range requests over HLS chunks maximize edge hit rate.",
                                "url": "https://example.com/hls",
                            }
                        ]
                    ),
                ),
            ):
                rev_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/review",
                    json={"use_web_search": True},
                )
                assert rev_res.status_code == 202

                def_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={
                        "message": "We serve range-requested HLS segments over CDN.",
                        "request_hint": True,
                        "use_web_search": True,
                    },
                )
                assert def_res.status_code == 200
                assert def_res.json()["defence_transcript"][-1]["assisted"] is True

            rev_sys = mock_model.ainvoke.call_args_list[0].args[0][0].content
            def_sys = mock_model.ainvoke.call_args_list[1].args[0][0].content
            assert "Audio CDN Caching Patterns" in rev_sys
            assert "Audio CDN Caching Patterns" in def_sys
            assert "COACHING HINT REQUESTED" in def_sys

            # Frontier Packet Export
            packet_res = await ac.get(
                f"/api/v1/system-design/sessions/{session_id}/frontier-packet"
            )
            assert packet_res.status_code == 200
            packet = packet_res.json()
            assert packet["session_id"] == session_id
            assert packet["diagram_version"] == 1
            assert "ASSISTED / HINT REQUESTED" in packet["markdown_packet"]
            assert "Requirements Clarity" in packet["markdown_packet"]
            assert packet["filename"].endswith(".md")

            # Two-way Frontier Evaluation Import (Markdown + full 12-dimension JSON fence)
            frontier_scores = [5, 5, 4, 5, 5, 5, 5, 4, 5, 5, 4, 5]  # 57/60 -> 95.0
            frontier_payload = _build_valid_eval_payload(
                scores=frontier_scores,
                executive_summary="Frontier review confirms clean CDN segmentation and clear failover reasoning.",
            )
            frontier_pasted = (
                "Here is my Staff-level scorecard:\n\n```json\n"
                + json.dumps(frontier_payload, indent=2)
                + "\n```"
            )
            import_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/import-evaluation",
                json={"raw_response": frontier_pasted},
            )
            assert import_res.status_code == 200
            imported = import_res.json()
            assert imported["stage"] == "COMPLETED"
            assert imported["status"] == "COMPLETED"
            assert imported["overall_score"] == 95.0
            assert imported["readiness_rating"] == "STRONG_HIRE"
            assert len(imported["final_evaluation"]["rubric_scores"]) == 12
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case_name,bad_raw_builder",
    [
        (
            "invalid_1_to_10_dimension_score",
            lambda: json.dumps(
                {
                    **_build_valid_eval_payload([4] * 12),
                    "rubric_scores": [
                        {
                            **_build_full_rubric_scores([4] * 12)[0],
                            "score": 8,
                        },
                        *_build_full_rubric_scores([4] * 12)[1:],
                    ],
                }
            ),
        ),
        (
            "overall_score_scale_violation",
            lambda: json.dumps(
                _build_valid_eval_payload([4] * 12, overall_score=105.0)
            ),
        ),
        (
            "missing_dimensions",
            lambda: json.dumps(
                {
                    **_build_valid_eval_payload([4] * 12),
                    "rubric_scores": _build_full_rubric_scores([4] * 12)[:11],
                }
            ),
        ),
        (
            "truncated_json_output",
            lambda: (
                '{"overall_score": 80, "rubric_scores": [{"dimension": "Requirements Clarity", "score": 4'
            ),
        ),
        (
            "truncated_inside_think_block",
            lambda: "<think>Starting deep reasoning about architecture without closing",
        ),
        (
            "contradictory_overall_and_dimension_scores",
            lambda: json.dumps(_build_valid_eval_payload([2] * 12, overall_score=95.0)),
        ),
    ],
)
async def test_f01_final_evaluation_rejects_invalid_and_repairs_once(
    db_session: AsyncSession, tmp_path, monkeypatch, case_name: str, bad_raw_builder
):
    """F-01: Invalid scores, missing dimensions, truncated JSON, and contradictions trigger one repair retry; failure keeps session incomplete."""
    import app.services.system_design_service as sd_service_module

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]

            # 1) Invalid initial output followed by successful controlled repair retry
            s1 = (
                await ac.post(
                    "/api/v1/system-design/sessions",
                    json={"challenge_id": challenge_id},
                )
            ).json()["id"]
            await _advance_session_to_defence(ac, s1)

            bad_msg = AsyncMock()
            bad_msg.content = bad_raw_builder()
            good_msg = AsyncMock()
            good_msg.content = json.dumps(_build_valid_eval_payload([4] * 12))

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get:
                mock_model = AsyncMock()
                mock_model.ainvoke.side_effect = [bad_msg, good_msg]
                mock_get.return_value = mock_model

                res1 = await ac.post(f"/api/v1/system-design/sessions/{s1}/evaluate")
            assert res1.status_code == 202, case_name
            assert mock_model.ainvoke.call_count == 2

            repaired_session = (
                await ac.get(f"/api/v1/system-design/sessions/{s1}")
            ).json()
            assert repaired_session["status"] == "COMPLETED"
            assert repaired_session["stage"] == "COMPLETED"
            assert repaired_session["overall_score"] == 80.0
            assert len(repaired_session["final_evaluation"]["rubric_scores"]) == 12

            # 2) Failed repair marks task FAILED and preserves non-completed DEFENCE session
            s2 = (
                await ac.post(
                    "/api/v1/system-design/sessions",
                    json={"challenge_id": challenge_id},
                )
            ).json()["id"]
            await _advance_session_to_defence(ac, s2)

            bad_msg_2 = AsyncMock()
            bad_msg_2.content = bad_raw_builder()
            bad_repair_msg = AsyncMock()
            bad_repair_msg.content = bad_raw_builder()

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get:
                mock_model_fail = AsyncMock()
                mock_model_fail.ainvoke.side_effect = [bad_msg_2, bad_repair_msg]
                mock_get.return_value = mock_model_fail

                res2 = await ac.post(f"/api/v1/system-design/sessions/{s2}/evaluate")
            assert res2.status_code == 202
            assert mock_model_fail.ainvoke.call_count == 2

            failed_session = (
                await ac.get(f"/api/v1/system-design/sessions/{s2}")
            ).json()
            assert failed_session["status"] == "IN_PROGRESS"
            assert failed_session["stage"] == "DEFENCE"
            assert failed_session["final_evaluation"] is None
            assert failed_session["active_task_status"] == "FAILED"
            assert failed_session["active_task_error"] is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_f03_configurable_storage_dir_and_permission_error(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """F-03: SYSTEM_DESIGN_DATA_DIR controls diagram disk storage; unwritable dir raises actionable 500 without silent fallback."""
    from app.core.config import settings

    configured_dir = tmp_path / "custom_sd_root"
    monkeypatch.setattr(settings, "SYSTEM_DESIGN_DATA_DIR", str(configured_dir))

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
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
            await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Shorten URLs"],
                    "non_functional_requirements": [],
                    "scale_estimates": {"read_qps": "5000"},
                    "out_of_scope": [],
                    "is_locked": True,
                },
            )

            up_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("arch.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Configured storage check"},
            )
            assert up_res.status_code == 201
            stored_file = configured_dir / f"session_{session_id}" / "v1.png"
            assert stored_file.is_file()

            img_res = await ac.get(
                f"/api/v1/system-design/sessions/{session_id}/diagrams/1/image"
            )
            assert img_res.status_code == 200
            assert img_res.content == FAKE_PNG_BYTES

            readonly_root = tmp_path / "readonly_sd_root"
            readonly_root.mkdir(parents=True, exist_ok=True)
            os.chmod(readonly_root, 0o500)
            monkeypatch.setattr(settings, "SYSTEM_DESIGN_DATA_DIR", str(readonly_root))
            try:
                if os.geteuid() != 0:
                    fail_res = await ac.post(
                        f"/api/v1/system-design/sessions/{session_id}/diagrams",
                        files={"file": ("v2.png", FAKE_PNG_BYTES, "image/png")},
                        data={"notes": "Should fail"},
                    )
                    assert fail_res.status_code == 500
                    assert "SYSTEM_DESIGN_DATA_DIR" in fail_res.json()["detail"]
            finally:
                os.chmod(readonly_root, 0o700)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_f04_nonblocking_queue_enqueue_cancel_and_retry(
    db_session: AsyncSession, tmp_path, monkeypatch
):
    """F-04: Review and evaluation enqueue QUEUED tasks immediately, support cancellation and retry with ANALYZING stage."""
    import app.services.system_design_service as sd_service_module
    from app.services.evaluation_worker import process_evaluation_task

    monkeypatch.setattr(sd_service_module, "SYSTEM_DESIGN_DATA_DIR", tmp_path)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ch_res = await ac.get("/api/v1/system-design/challenges/spotify-100k")
            challenge_id = ch_res.json()["id"]
            session_id = (
                await ac.post(
                    "/api/v1/system-design/sessions",
                    json={"challenge_id": challenge_id},
                )
            ).json()["id"]

            await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Stream audio"],
                    "non_functional_requirements": ["p99 < 300ms"],
                    "scale_estimates": {"dau": "30000"},
                    "out_of_scope": [],
                    "is_locked": True,
                },
            )
            await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("v1.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Queue lifecycle diagram"},
            )

            with patch("fastapi.BackgroundTasks.add_task") as mock_add_task:
                rev_q = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/review"
                )
            assert rev_q.status_code == 202
            assert mock_add_task.call_count == 1
            rev_body = rev_q.json()
            rev_task_id = rev_body["active_task_id"]
            assert rev_body["active_task_status"] == "QUEUED"
            assert rev_body["active_task_stage"] == "QUEUED"

            # Concurrent duplicate enqueue while QUEUED must fail cleanly with 400
            dup_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/review"
            )
            assert dup_res.status_code == 400

            cancel_res = await ac.post(
                f"/api/v1/intake/evaluations/{rev_task_id}/cancel"
            )
            assert cancel_res.status_code == 200
            assert cancel_res.json()["status"] == "CANCELLED"

            with patch("fastapi.BackgroundTasks.add_task") as mock_retry_bg:
                retry_res = await ac.post(
                    f"/api/v1/intake/evaluations/{rev_task_id}/retry"
                )
            assert retry_res.status_code == 200
            assert mock_retry_bg.call_count == 1
            retried = retry_res.json()
            assert retried["status"] == "QUEUED"
            assert retried["stage"] == "ANALYZING"

            mock_rev = AsyncMock()
            mock_rev.content = json.dumps(
                {
                    "interpreted_components": ["API", "CDN"],
                    "interpreted_data_flows": ["Client -> CDN"],
                    "visual_clarifications_needed": [],
                    "strengths": ["Clean separation"],
                    "missing_components": [],
                    "bottlenecks_and_spofs": ["Primary DB"],
                    "unnecessary_complexity": [],
                    "requirement_gaps": [],
                    "overall_impression": "Baseline verified.",
                    "suggested_defence_topics": ["How do you scale metadata reads?"],
                }
            )
            mock_def = AsyncMock()
            mock_def.content = "Good read replica caching explanation."
            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=AsyncMock(
                    ainvoke=AsyncMock(side_effect=[mock_rev, mock_def])
                ),
            ):
                await process_evaluation_task(rev_task_id)
                def_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/defence/message",
                    json={"message": "Read replicas plus Redis metadata cache."},
                )
                assert def_res.status_code == 200

            with patch("fastapi.BackgroundTasks.add_task") as mock_eval_bg:
                eval_q = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/evaluate"
                )
            assert eval_q.status_code == 202
            assert mock_eval_bg.call_count == 1
            eval_task_id = eval_q.json()["active_task_id"]
            assert eval_q.json()["active_task_status"] == "QUEUED"

            assert (
                await ac.post(f"/api/v1/intake/evaluations/{eval_task_id}/cancel")
            ).json()["status"] == "CANCELLED"
            with patch("fastapi.BackgroundTasks.add_task"):
                eval_retry = (
                    await ac.post(f"/api/v1/intake/evaluations/{eval_task_id}/retry")
                ).json()
            assert eval_retry["status"] == "QUEUED"
            assert eval_retry["stage"] == "ANALYZING"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_challenge_generation_creates_queued_worker_task_with_telemetry(
    db_session: AsyncSession,
):
    from sqlalchemy import select

    app.dependency_overrides[get_db] = lambda: db_session
    fake_challenge = {
        "title": "Design a Real-Time Audit Log Ingestion Pipeline",
        "category": "DATA_INFRASTRUCTURE",
        "difficulty": "HARD",
        "prompt_summary": "Build a tamper-evident event pipeline.",
        "initial_prompt": "Design a multi-tenant audit logging pipeline.",
        "tags": ["kafka", "append-only"],
        "interviewer_brief": {
            "hidden_context": {"scale_targets": "50k events/sec"},
            "expected_components": ["Ingest Gateway", "Kafka", "Immutable Store"],
            "over_engineering_traps": ["Custom blockchain"],
            "defence_questions": ["How do you guarantee ordering per tenant?"],
        },
    }
    mock_msg = AsyncMock()
    mock_msg.content = json.dumps(fake_challenge)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            with patch(
                "app.services.system_design_service.get_task_chat_model",
                return_value=AsyncMock(ainvoke=AsyncMock(return_value=mock_msg)),
            ):
                res = await ac.post(
                    "/api/v1/system-design/challenges/generate",
                    json={
                        "topic": "Real-time audit log ingestion pipeline",
                        "difficulty": "HARD",
                        "use_web_search": False,
                    },
                )
        assert res.status_code == 201
        created = res.json()
        assert created["title"] == fake_challenge["title"]

        task = (
            await db_session.execute(
                select(IntakeEvaluationTaskModel).where(
                    IntakeEvaluationTaskModel.task_type == "SYSTEM_DESIGN_CHALLENGE_GEN"
                )
            )
        ).scalar_one_or_none()
        assert task is not None
        assert task.status == "COMPLETED"
        assert task.stage == "COMPLETE"
        cp = (task.result_json or {}).get("_checkpoint", {})
        assert cp.get("completed_steps") == ["PREPARING", "GENERATING", "SAVING"]
        assert isinstance(cp.get("provider_telemetry"), dict)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_frontier_challenge_audit_upgrade_and_type_id_normalization(
    db_session: AsyncSession,
):
    """Verify non-canonical type_ids snap to catalog IDs and custom challenges can be audited/upgraded in place."""
    from app.core.database import get_db
    from app.main import app
    from app.services.system_design_service import (
        SystemDesignService,
        _normalize_generated_brief,
    )

    normalized = _normalize_generated_brief(
        {
            "variants": [
                {
                    "variant_id": "v1",
                    "title": "MVP",
                    "expected_components": [
                        "Event Log / Kafka Stream",
                        "Analytics / OLAP Store",
                    ],
                    "expected_paths": [
                        {
                            "id": "write",
                            "title": "Ingest",
                            "steps": [
                                {
                                    "source_type_id": "app_service",
                                    "target_type_id": "event_log_kafka_stream",
                                    "delivery_mode": "async",
                                },
                                {
                                    "source_type_id": "event_log_kafka_stream",
                                    "target_type_id": "analytics_olap_store",
                                    "delivery_mode": "async",
                                },
                            ],
                        }
                    ],
                    "required_capabilities": [
                        {
                            "id": "analytics",
                            "accepted_type_groups": [["analytics_olap_store"]],
                        }
                    ],
                    "defence_questions": ["How handle backpressure?"],
                },
                {
                    "variant_id": "v2",
                    "title": "Enterprise",
                    "expected_components": ["API Gateway"],
                    "defence_questions": ["How handle multi-tenant isolation?"],
                },
            ]
        }
    )
    step0 = normalized["variants"][0]["expected_paths"][0]["steps"][0]
    step1 = normalized["variants"][0]["expected_paths"][0]["steps"][1]
    assert step0["target_type_id"] == "event_stream"
    assert step1["source_type_id"] == "event_stream"
    assert step1["target_type_id"] == "olap_warehouse"
    assert normalized["variants"][0]["required_capabilities"][0][
        "accepted_type_groups"
    ] == [["olap_warehouse"]]

    await SystemDesignService._ensure_challenges_seeded(db_session)
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            import_res = await ac.post(
                "/api/v1/system-design/challenges/import",
                json={
                    "raw_response": json.dumps(
                        {
                            "title": "Design a Telemetry Anomaly Detector",
                            "category": "DATA_INFRASTRUCTURE",
                            "difficulty": "MEDIUM",
                            "prompt_summary": "Detect anomalies in real-time IoT sensor telemetry streams cleanly.",
                            "initial_prompt": "Design a telemetry ingestion and anomaly scoring pipeline.",
                            "tags": ["telemetry"],
                            "interviewer_brief": normalized,
                        }
                    )
                },
            )
            assert import_res.status_code == 201
            cid = import_res.json()["id"]

            audit_res = await ac.post(
                f"/api/v1/system-design/challenges/{cid}/frontier-audit-prompt"
            )
            assert audit_res.status_code == 200
            assert (
                "Design a Telemetry Anomaly Detector"
                in audit_res.json()["markdown_prompt"]
            )

            upgraded_payload = {
                "title": "Design a Multi-Region Telemetry Anomaly Platform",
                "category": "DATA_INFRASTRUCTURE",
                "difficulty": "HARD",
                "prompt_summary": "Upgraded scenario with full multi-region telemetry scoring and alerting.",
                "initial_prompt": "Design an end-to-end anomaly detection and alerting platform.",
                "tags": ["telemetry", "upgraded"],
                "interviewer_brief": normalized,
            }
            up_res = await ac.put(
                f"/api/v1/system-design/challenges/{cid}/frontier-import",
                json={"raw_response": json.dumps(upgraded_payload)},
            )
            assert up_res.status_code == 200
            assert (
                up_res.json()["title"]
                == "Design a Multi-Region Telemetry Anomaly Platform"
            )
            assert up_res.json()["difficulty"] == "HARD"
    finally:
        app.dependency_overrides.clear()
