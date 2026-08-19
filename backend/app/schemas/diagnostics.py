from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DiagnosticsStatsResponse(BaseModel):
    total_runs: int
    success_count: int
    error_count: int
    success_rate: float
    category_counts: dict[str, int]
    category_error_counts: dict[str, int]


class TracePayloadSummary(BaseModel):
    name: str
    error: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: float | None = None


class TraceSummaryResponse(BaseModel):
    id: int
    run_id: str
    category: str
    event_type: str
    status: str
    payload_summary: TracePayloadSummary
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TraceDetailResponse(BaseModel):
    id: int
    run_id: str
    category: str
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class DiagnosticsPurgeResponse(BaseModel):
    message: str
