import json
import zipfile
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.diagnostics import TraceEventModel

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


@router.get("/export")
async def export_diagnostics(db: AsyncSession = Depends(get_db)):
    stmt = select(TraceEventModel).order_by(TraceEventModel.timestamp.desc()).limit(500)
    result = await db.execute(stmt)
    records = result.scalars().all()

    export_data = [
        {
            "id": r.id,
            "run_id": r.run_id,
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
    stmt = select(TraceEventModel.event_type, TraceEventModel.payload)
    result = await db.execute(stmt)
    records = result.all()

    total_runs = len(records)
    error_count = sum(1 for _, payload in records if payload.get("error"))
    success_count = total_runs - error_count

    return {
        "total_runs": total_runs,
        "success_count": success_count,
        "error_count": error_count,
        "success_rate": round(success_count / total_runs * 100, 2)
        if total_runs > 0
        else 0,
    }


@router.get("/traces")
async def get_traces(
    limit: int = 50,
    offset: int = 0,
    errors_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TraceEventModel).order_by(TraceEventModel.timestamp.desc())
    if errors_only:
        from sqlalchemy import text

        stmt = stmt.where(text("payload ? 'error' AND payload->>'error' IS NOT NULL"))

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    records = result.scalars().all()

    out = []
    for r in records:
        name = r.payload.get("name")
        error = r.payload.get("error")
        start_time = r.payload.get("start_time")
        end_time = r.payload.get("end_time")

        out.append(
            {
                "id": r.id,
                "run_id": r.run_id,
                "event_type": r.event_type,
                "payload_summary": {
                    "name": name,
                    "error": error,
                    "start_time": start_time,
                    "end_time": end_time,
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
        "event_type": record.event_type,
        "payload": record.payload,
        "timestamp": record.timestamp,
    }
