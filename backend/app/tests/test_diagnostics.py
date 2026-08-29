import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.diagnostics import TraceEventModel
from app.services.telemetry import record_diagnostic_event, trace_operation


@pytest.mark.asyncio
async def test_record_diagnostic_event_and_trace_operation(db_session: AsyncSession):
    # Test successful operation trace
    async with trace_operation(
        category="scraper",
        name="test_scrape_job",
        inputs={"url": "https://example.com/jobs/1"},
        db=db_session,
    ) as ctx:
        ctx["outputs"] = {"title": "Staff Engineer", "char_count": 1200}

    # Verify event exists in DB
    events = (
        await db_session.execute(
            TraceEventModel.__table__.select().where(
                TraceEventModel.category == "scraper"
            )
        )
    ).all()
    assert len(events) >= 1
    latest_event = events[-1]
    assert latest_event.category == "scraper"
    assert latest_event.payload["name"] == "test_scrape_job"
    assert latest_event.payload["status"] == "success"
    assert latest_event.payload["outputs"]["title"] == "Staff Engineer"
    assert latest_event.payload["duration_ms"] is not None


@pytest.mark.asyncio
async def test_trace_operation_exception_handling(db_session: AsyncSession):
    # Test failed operation trace
    with pytest.raises(ValueError, match="Scraping connection timeout"):
        async with trace_operation(
            category="scraper",
            name="test_scrape_failed",
            inputs={"url": "https://fail.example.com"},
            db=db_session,
        ):
            raise ValueError("Scraping connection timeout")

    events = (
        await db_session.execute(
            TraceEventModel.__table__.select().where(
                TraceEventModel.category == "scraper",
            )
        )
    ).all()
    failed_events = [e for e in events if e.payload.get("name") == "test_scrape_failed"]
    assert len(failed_events) == 1
    assert failed_events[0].payload["status"] == "error"
    assert (
        "ValueError: Scraping connection timeout" in failed_events[0].payload["error"]
    )


@pytest.mark.asyncio
async def test_diagnostics_api_endpoints(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Seed test trace events across categories
        await record_diagnostic_event(
            category="llm",
            name="job_assessment_llm",
            status="success",
            duration_ms=450.0,
            inputs={"model": "gpt-4o"},
            outputs={"fit_score": 92},
            db=db_session,
        )
        await record_diagnostic_event(
            category="email_sync",
            name="email_sync_imap",
            status="error",
            error="IMAP connection refused",
            duration_ms=120.0,
            db=db_session,
        )
        await record_diagnostic_event(
            category="worker",
            name="worker_job_assessment",
            status="success",
            duration_ms=1500.0,
            db=db_session,
        )
        await record_diagnostic_event(
            category="embedding",
            name="generate_embedding",
            status="success",
            duration_ms=80.0,
            db=db_session,
        )

        # 1. Stats endpoint
        stats_res = await ac.get("/api/v1/diagnostics/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_runs"] >= 4
        assert stats["error_count"] >= 1
        assert "category_counts" in stats
        assert "total_tokens" in stats
        assert "total_spend_usd" in stats
        assert "total_savings_usd" in stats
        assert "task_token_breakdown" in stats
        assert stats["category_counts"].get("llm", 0) >= 1
        assert stats["category_counts"].get("email_sync", 0) >= 1
        assert stats["category_counts"].get("worker", 0) >= 1
        assert stats["category_counts"].get("embedding", 0) >= 1

        # 2. Traces endpoint with category filter
        traces_llm_res = await ac.get("/api/v1/diagnostics/traces?category=llm")
        assert traces_llm_res.status_code == 200
        llm_traces = traces_llm_res.json()
        assert len(llm_traces) >= 1
        assert all(t["category"] == "llm" for t in llm_traces)

        # 3. Traces endpoint with errors_only filter
        errors_res = await ac.get("/api/v1/diagnostics/traces?errors_only=true")
        assert errors_res.status_code == 200
        error_traces = errors_res.json()
        assert len(error_traces) >= 1
        assert all(t["payload_summary"]["error"] is not None for t in error_traces)

        # 4. Single trace detail
        first_trace = llm_traces[0]
        run_id = first_trace["run_id"]
        detail_res = await ac.get(f"/api/v1/diagnostics/traces/{run_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["run_id"] == run_id
        assert detail["category"] == "llm"

        # 5. Export endpoint
        export_res = await ac.get("/api/v1/diagnostics/export")
        assert export_res.status_code == 200
        assert export_res.headers["content-type"] == "application/zip"

        # 6. Purge endpoint
        purge_res = await ac.delete("/api/v1/diagnostics/purge")
        assert purge_res.status_code == 200

        # Verify purged
        after_purge_stats = await ac.get("/api/v1/diagnostics/stats")
        assert after_purge_stats.json()["total_runs"] == 0
