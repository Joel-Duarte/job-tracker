from langchain_core.tracers.base import AsyncBaseTracer
from langchain_core.tracers.schemas import Run

from app.core.database import AsyncSessionLocal
from app.models.diagnostics import TraceEventModel


class PostgresTracer(AsyncBaseTracer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_llm_error(self, error: BaseException, *, run_id, **kwargs) -> None:
        # Override to properly mark error on the run object if the tracer catches it directly
        super().on_llm_error(error, run_id=run_id, **kwargs)

    async def _persist_run(self, run: Run) -> None:
        try:
            # Note: We serialize directly via model_dump(mode='json') to avoid UUID/datetime serialization issues
            run_dict = run.model_dump(mode="json")
            run_id = str(run.id)
            event_type = run.run_type

            async with AsyncSessionLocal() as session:
                event = TraceEventModel(
                    run_id=run_id,
                    category="llm",
                    event_type=event_type,
                    payload=run_dict,
                )
                session.add(event)
                await session.commit()
        except Exception as e:
            print(f"Error persisting run to Postgres: {e}")
        finally:
            self.run_map.clear()
