import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.tracers.schemas import Run

from app.services.postgres_tracer import PostgresTracer


@pytest.mark.asyncio
async def test_postgres_tracer_background_persist_and_flush():
    tracer = PostgresTracer()

    mock_run = Run(
        id=uuid.uuid4(),
        name="test_run",
        run_type="chain",
        inputs={"input": "hello"},
        outputs={"output": "world"},
    )

    with patch(
        "app.services.postgres_tracer.db_module.AsyncSessionLocal"
    ) as mock_session_local:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        await tracer._persist_run(mock_run)
        assert len(tracer._background_tasks) == 1

        await tracer.flush()
        assert len(tracer._background_tasks) == 0

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_tracer_does_not_clear_global_run_map():
    tracer = PostgresTracer()
    run_id = uuid.uuid4()
    mock_run = Run(
        id=run_id,
        name="test_run",
        run_type="llm",
        inputs={},
    )
    tracer.run_map[str(run_id)] = mock_run

    with patch(
        "app.services.postgres_tracer.db_module.AsyncSessionLocal"
    ) as mock_session_local:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        await tracer._persist_run(mock_run)
        await tracer.flush()

        # Check that run_map still contains the entry (it is managed per-run by LangChain)
        assert str(run_id) in tracer.run_map
