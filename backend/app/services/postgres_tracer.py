import asyncio
import logging

from langchain_core.tracers.base import AsyncBaseTracer
from langchain_core.tracers.schemas import Run

import app.core.database as db_module
from app.models.diagnostics import TraceEventModel

logger = logging.getLogger(__name__)


class PostgresTracer(AsyncBaseTracer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._background_tasks: set[asyncio.Task] = set()

    async def _persist_run_async(self, run: Run) -> None:
        try:
            # Note: We serialize directly via model_dump(mode='json') to avoid UUID/datetime serialization issues
            run_dict = run.model_dump(mode="json")
            run_id = str(run.id)
            event_type = run.run_type

            # Calculate duration_ms if timestamps are present
            if run.start_time and run.end_time:
                duration_ms = (run.end_time - run.start_time).total_seconds() * 1000
                run_dict["duration_ms"] = round(duration_ms, 2)

            from app.services.pricing_service import extract_usage_from_payload

            usage_info = extract_usage_from_payload(run_dict)
            run_dict.update(usage_info)

            async with db_module.AsyncSessionLocal() as session:
                event = TraceEventModel(
                    run_id=run_id,
                    category="llm",
                    event_type=event_type,
                    payload=run_dict,
                )
                session.add(event)
                await session.commit()
        except Exception as e:
            logger.error("Error persisting run to Postgres: %s", e)

    async def _persist_run(self, run: Run) -> None:
        task = asyncio.create_task(self._persist_run_async(run))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def flush(self) -> None:
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
