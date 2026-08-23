import json
import zipfile
from collections import defaultdict
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_admin_access
from app.models.diagnostics import TraceEventModel

router = APIRouter(
    prefix="/diagnostics",
    tags=["Diagnostics"],
    dependencies=[Depends(verify_admin_access)],
)


@router.get("/export")
async def export_diagnostics(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TraceEventModel)
        .where(TraceEventModel.event_type != "health_check")
        .order_by(TraceEventModel.timestamp.desc())
        .limit(500)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    export_data = [
        {
            "id": r.id,
            "run_id": r.run_id,
            "category": r.category or "llm",
            "event_type": r.event_type,
            "payload": r.payload,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in records
    ]

    json_bytes = json.dumps(export_data, indent=2).encode("utf-8")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("diagnostics.json", json_bytes)

        # Read standard application logs if they exist
        try:
            with open("backend.log") as f:
                log_content = f.read()
            zip_file.writestr("backend.log", log_content)
        except Exception:
            pass

    zip_buffer.seek(0)

    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=diagnostics.zip"},
    )


@router.get("/stats")
async def get_diagnostics_stats(db: AsyncSession = Depends(get_db)):
    stmt = select(TraceEventModel.category, TraceEventModel.payload).where(
        TraceEventModel.event_type != "health_check"
    )
    result = await db.execute(stmt)
    records = result.all()

    total_runs = len(records)
    error_count = sum(1 for _, payload in records if payload.get("error"))
    success_count = total_runs - error_count

    category_counts: dict[str, int] = defaultdict(int)
    category_error_counts: dict[str, int] = defaultdict(int)

    for cat, payload in records:
        cat_key = cat or "llm"
        category_counts[cat_key] += 1
        if payload.get("error"):
            category_error_counts[cat_key] += 1

    return {
        "total_runs": total_runs,
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": round(success_count / total_runs * 100, 2)
        if total_runs > 0
        else 0,
        "category_counts": dict(category_counts),
        "category_error_counts": dict(category_error_counts),
    }


def _extract_tracer_task_name(
    run_dict: dict, default_name: str = "Unknown Task"
) -> str:
    """Helper to extract a human-readable task name from a run payload."""
    name = run_dict.get("name") or default_name

    # Check tags for LangChain runs
    tags = run_dict.get("tags", [])
    if isinstance(tags, list) and len(tags) > 0:
        meaningful_tags = [t for t in tags if t not in ("seq:step:1", "seq:step:2")]
        if meaningful_tags:
            name = meaningful_tags[0]

    return name


def _parse_filter_datetime(dt_str: str, is_end_of_day: bool = False) -> datetime | None:
    if not dt_str or not dt_str.strip():
        return None
    cleaned = dt_str.strip()
    try:
        # Handle simple date YYYY-MM-DD
        if len(cleaned) == 10 and "T" not in cleaned:
            if is_end_of_day:
                cleaned += "T23:59:59.999999"
            else:
                cleaned += "T00:00:00"
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


@router.get("/traces")
async def get_traces(
    limit: int = 100,
    offset: int = 0,
    errors_only: bool = False,
    status: str | None = Query(
        None,
        description="Filter status: 'all', 'success', or 'error'",
    ),
    category: str | None = Query(
        None,
        description="Filter traces by category (e.g. llm, scraper, email_sync, worker, embedding)",
    ),
    start_date: str | None = Query(
        None,
        description="Filter traces starting from timestamp (ISO format or YYYY-MM-DD)",
    ),
    end_date: str | None = Query(
        None,
        description="Filter traces up to timestamp (ISO format or YYYY-MM-DD)",
    ),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TraceEventModel)
        .where(TraceEventModel.event_type != "health_check")
        .order_by(TraceEventModel.timestamp.desc())
    )

    if category and category.strip() and category.lower() != "all":
        stmt = stmt.where(TraceEventModel.category == category.lower())

    from sqlalchemy import text

    normalized_status = (status or "").strip().lower()
    if errors_only or normalized_status == "error":
        stmt = stmt.where(text("payload ? 'error' AND payload->>'error' IS NOT NULL"))
    elif normalized_status == "success":
        stmt = stmt.where(
            text("NOT (payload ? 'error' AND payload->>'error' IS NOT NULL)")
        )

    if start_date:
        parsed_start = _parse_filter_datetime(start_date, is_end_of_day=False)
        if parsed_start:
            stmt = stmt.where(TraceEventModel.timestamp >= parsed_start)

    if end_date:
        parsed_end = _parse_filter_datetime(end_date, is_end_of_day=True)
        if parsed_end:
            stmt = stmt.where(TraceEventModel.timestamp <= parsed_end)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    records = result.scalars().all()

    out = []
    for r in records:
        name = _extract_tracer_task_name(r.payload, default_name=r.event_type)
        error = r.payload.get("error")
        start_time = r.payload.get("start_time")
        end_time = r.payload.get("end_time")
        duration_ms = r.payload.get("duration_ms")
        status = r.payload.get("status") or ("error" if error else "success")

        out.append(
            {
                "id": r.id,
                "run_id": r.run_id,
                "category": r.category or "llm",
                "event_type": r.event_type,
                "status": status,
                "payload_summary": {
                    "name": name,
                    "error": error,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_ms": duration_ms,
                },
                "timestamp": r.timestamp,
            }
        )
    return out


@router.get("/traces/{run_id}")
async def get_single_trace(run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(TraceEventModel).where(TraceEventModel.run_id == run_id)
    result = await db.execute(stmt)
    record = result.scalars().first()

    if not record:
        raise HTTPException(status_code=404, detail="Trace not found")

    return {
        "id": record.id,
        "run_id": record.run_id,
        "category": record.category or "llm",
        "event_type": record.event_type,
        "payload": record.payload,
        "timestamp": record.timestamp,
    }


@router.delete("/purge")
async def purge_traces(db: AsyncSession = Depends(get_db)):
    """Purges diagnostic traces for cleanup."""
    from sqlalchemy import delete

    await db.execute(delete(TraceEventModel))
    await db.commit()
    return {"message": "All diagnostic traces purged successfully."}
