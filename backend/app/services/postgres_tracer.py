import json

import asyncpg
from langchain_core.tracers.base import AsyncBaseTracer
from langchain_core.tracers.schemas import Run

from app.core.config import settings


class PostgresTracer(AsyncBaseTracer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db_url = settings.get_database_url().replace("+asyncpg", "")

    def on_llm_error(self, error: BaseException, *, run_id, **kwargs) -> None:
        # Override to properly mark error on the run object if the tracer catches it directly
        super().on_llm_error(error, run_id=run_id, **kwargs)

    async def _persist_run(self, run: Run) -> None:
        try:
            # Note: We serialize directly via model_dump(mode='json') to avoid UUID/datetime serialization issues
            run_dict = run.model_dump(mode="json")
            run_id = str(run.id)
            event_type = run.run_type

            # Make sure to catch un-persisted errors if error exists as a property
            # Actually, `run.error` should be populated, but occasionally `run.outputs` has it or it's unhandled by langchain
            # We don't really need to do much here, Langchain usually updates `run.error`.

            conn = await asyncpg.connect(self.db_url)
            try:
                await conn.execute(
                    "INSERT INTO trace_events (run_id, event_type, payload, timestamp) VALUES ($1, $2, $3::jsonb, NOW())",
                    run_id,
                    event_type,
                    json.dumps(run_dict),
                )
            finally:
                await conn.close()
        except Exception as e:
            print(f"Error persisting run to Postgres: {e}")
        finally:
            self.run_map.clear()
