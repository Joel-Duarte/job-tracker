import base64
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.intake_tasks import IntakeEvaluationTaskModel

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake-png-payload"
FAKE_WEBP_BYTES = b"RIFF\x18\x00\x00\x00WEBPfake-webp-payload"


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

            # Review before upload must return 400
            no_diagram_review = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/review"
            )
            assert no_diagram_review.status_code == 400

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

            assert rev_res.status_code == 200
            assert "interviewer_brief" not in rev_res.text
            assert "over_engineering_traps" not in rev_res.text

            rev_data = rev_res.json()
            assert rev_data["stage"] == "REVIEW"
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

            await ac.put(
                f"/api/v1/system-design/sessions/{session_id}/requirements/ledger",
                json={
                    "functional_requirements": ["Stream tracks", "Create playlists"],
                    "non_functional_requirements": ["Low p99 playback latency"],
                    "scale_estimates": {"dau": "30000"},
                    "out_of_scope": ["Podcasts"],
                    "is_locked": True,
                },
            )
            await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/diagrams",
                files={"file": ("v1.png", FAKE_PNG_BYTES, "image/png")},
                data={"notes": "Initial CDN + Postgres design"},
            )

            mock_eval_res = AsyncMock()
            mock_eval_res.content = """<think>Checking all session artifacts.</think>{
                "overall_score": 84,
                "readiness_rating": "INTERVIEW_READY",
                "executive_summary": "Strong right-sizing for 30k DAU using CDN signed URLs and PostgreSQL.",
                "rubric_scores": [
                    {
                        "dimension": "Requirements Clarity",
                        "score": 4,
                        "evidence": "Locked ledger captured 30k DAU, streaming/playlists, and excluded podcasts.",
                        "critique": "Clear functional and scope boundaries."
                    },
                    {
                        "dimension": "Right-Sizing & Simplicity (YAGNI)",
                        "score": 5,
                        "evidence": "Chose managed Postgres + CDN signed URLs without premature microservices.",
                        "critique": "Appropriately simple for target scale."
                    },
                    {
                        "dimension": "Reliability & Fault Tolerance",
                        "score": 4,
                        "evidence": "Identified standby DB replication and short-lived CDN token expiry.",
                        "critique": "Good baseline resilience; clarify health checks."
                    }
                ],
                "key_strengths": ["Avoided over-engineering while offloading audio bytes to CDN"],
                "critical_gaps": ["Add read-replica promotion metrics and observability alerts"],
                "recommended_next_steps": ["Upload diagram v2 annotating monitoring and failover paths"]
            }"""

            with patch(
                "app.services.system_design_service.get_task_chat_model"
            ) as mock_get_model:
                mock_model = AsyncMock()
                mock_model.ainvoke.return_value = mock_eval_res
                mock_get_model.return_value = mock_model

                eval_res = await ac.post(
                    f"/api/v1/system-design/sessions/{session_id}/evaluate"
                )

            assert eval_res.status_code == 200
            assert "interviewer_brief" not in eval_res.text
            assert "<think>" not in eval_res.text

            eval_data = eval_res.json()
            assert eval_data["stage"] == "COMPLETED"
            assert eval_data["status"] == "COMPLETED"
            assert eval_data["overall_score"] == 84.0
            assert eval_data["readiness_rating"] == "INTERVIEW_READY"
            assert eval_data["completed_at"] is not None

            final_eval = eval_data["final_evaluation"]
            assert len(final_eval["rubric_scores"]) == 3
            for item in final_eval["rubric_scores"]:
                assert len(item["evidence"].strip()) >= 5

            task_stmt = select(IntakeEvaluationTaskModel).where(
                IntakeEvaluationTaskModel.task_type == "SYSTEM_DESIGN_EVALUATION"
            )
            task_row = (await db_session.execute(task_stmt)).scalar_one()
            assert task_row.status == "COMPLETED"
            assert task_row.stage == "COMPLETE"
            assert task_row.result_json["session_id"] == session_id
            assert task_row.result_json["overall_score"] == 84.0
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
                assert rev_res.status_code == 200

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

            # Two-way Frontier Evaluation Import (Markdown + JSON fence)
            frontier_pasted = """Here is my Staff-level scorecard:

```json
{
  "overall_score": 91.5,
  "readiness_rating": "STRONG_HIRE",
  "executive_summary": "Frontier review confirms clean CDN segmentation and clear failover reasoning.",
  "rubric_scores": [
    {
      "dimension": "Caching & Latency Optimization",
      "score": 5,
      "evidence": "Used range-requested HLS chunks behind CloudFront edge caches.",
      "critique": "High cache hit ratio and minimal origin load."
    }
  ],
  "key_strengths": ["Edge-first audio streaming"],
  "critical_gaps": ["Document multi-AZ Postgres promotion SLO"],
  "recommended_next_steps": ["Add cache invalidation metrics"]
}
```"""
            import_res = await ac.post(
                f"/api/v1/system-design/sessions/{session_id}/import-evaluation",
                json={"raw_response": frontier_pasted},
            )
            assert import_res.status_code == 200
            imported = import_res.json()
            assert imported["stage"] == "COMPLETED"
            assert imported["status"] == "COMPLETED"
            assert imported["overall_score"] == 91.5
            assert imported["readiness_rating"] == "STRONG_HIRE"
            assert (
                imported["final_evaluation"]["rubric_scores"][0]["dimension"]
                == "Caching & Latency Optimization"
            )
    finally:
        app.dependency_overrides.clear()
