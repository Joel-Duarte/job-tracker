import contextlib
import logging
import time
import traceback
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.diagnostics import TraceEventModel

logger = logging.getLogger(__name__)


async def record_diagnostic_event(
    category: str,
    name: str,
    status: str = "success",
    error: str | None = None,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    run_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: AsyncSession | None = None,
) -> str:
    """Persists a programmatic execution trace event into the trace_events table."""
    generated_run_id = run_id or str(uuid.uuid4())
    now = datetime.now(UTC)
    start_dt = start_time or now
    end_dt = end_time or now

    payload = {
        "name": name,
        "category": category,
        "status": status,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "duration_ms": duration_ms,
        "error": error,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "extra": metadata or {},
    }

    try:
        if db is not None:
            event = TraceEventModel(
                run_id=generated_run_id,
                category=category,
                event_type=category,
                payload=payload,
            )
            db.add(event)
            await db.commit()
        else:
            async with AsyncSessionLocal() as session:
                event = TraceEventModel(
                    run_id=generated_run_id,
                    category=category,
                    event_type=category,
                    payload=payload,
                )
                session.add(event)
                await session.commit()
    except Exception as exc:
        logger.warning(
            "Failed to record diagnostic telemetry event for %s (%s): %s",
            name,
            category,
            exc,
        )

    return generated_run_id


@contextlib.asynccontextmanager
async def trace_operation(
    category: str,
    name: str,
    metadata: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    db: AsyncSession | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Async context manager that measures execution time and records diagnostic traces on completion or error.

    Usage:
        async with trace_operation("scraper", "scrape_job_url", inputs={"url": url}) as ctx:
            res = await do_work()
            ctx["outputs"] = {"content_length": len(res)}
    """
    ctx: dict[str, Any] = {
        "inputs": inputs or {},
        "outputs": {},
        "metadata": metadata or {},
        "run_id": str(uuid.uuid4()),
    }
    start_dt = datetime.now(UTC)
    t0 = time.perf_counter()
    err_str: str | None = None

    try:
        yield ctx
    except Exception as exc:
        err_str = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        raise
    finally:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        end_dt = datetime.now(UTC)
        final_error = err_str or ctx.get("error")
        status = ctx.get("status") or ("error" if final_error else "success")

        target_db = db or ctx.get("db")
        await record_diagnostic_event(
            category=category,
            name=name,
            status=status,
            error=final_error,
            duration_ms=duration_ms,
            metadata=ctx.get("metadata"),
            inputs=ctx.get("inputs"),
            outputs=ctx.get("outputs"),
            run_id=ctx.get("run_id"),
            start_time=start_dt,
            end_time=end_dt,
            db=target_db,
        )
