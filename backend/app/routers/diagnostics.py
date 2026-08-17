import json
import zipfile
from io import BytesIO

from fastapi import APIRouter, Depends
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
