import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.outputs import LLMResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostics import TraceEventModel
from app.services.postgres_tracer import PostgresTracer


@pytest.mark.asyncio
async def test_async_background_persistence(db_session: AsyncSession):
    tracer = PostgresTracer()

    run_id = "11111111-1111-1111-1111-111111111111"
    await tracer.on_chain_start(
        serialized={"name": "test_chain"},
        inputs={"input": "hello"},
        run_id=run_id,
        name="test_chain",
    )
    await tracer.on_chain_end(
        outputs={"output": "world"},
        run_id=run_id,
    )

    # Wait for background persistence tasks
    await tracer.flush()

    # Query DB to verify
    result = await db_session.execute(
        select(TraceEventModel).where(TraceEventModel.run_id == run_id)
    )
    events = result.scalars().all()
    assert len(events) == 1
    event = events[0]
    assert event.run_id == run_id
    assert event.category == "llm"
    assert event.event_type == "chain"
    assert event.payload["name"] == "test_chain"
    assert event.payload["outputs"] == {"output": "world"}


@pytest.mark.asyncio
async def test_concurrent_llm_runs(db_session: AsyncSession):
    tracer = PostgresTracer()

    async def execute_run(index: int):
        parent_id = f"00000000-0000-0000-0000-00000000000{index}"
        child_llm_id = f"00000000-0000-0000-0000-00000000001{index}"

        # Start parent chain
        await tracer.on_chain_start(
            serialized={"name": f"parent_chain_{index}"},
            inputs={"q": f"question_{index}"},
            run_id=parent_id,
            name=f"parent_chain_{index}",
        )

        # Simulate nested LLM start
        await tracer.on_llm_start(
            serialized={"name": "gpt-4o"},
            prompts=[f"prompt_{index}"],
            run_id=child_llm_id,
            parent_run_id=parent_id,
        )

        await asyncio.sleep(0.01)

        # End child LLM
        await tracer.on_llm_end(
            response=LLMResult(generations=[]),
            run_id=child_llm_id,
        )

        # End parent chain
        await tracer.on_chain_end(
            outputs={"a": f"answer_{index}"},
            run_id=parent_id,
        )

    # Execute 10 concurrent runs in parallel
    await asyncio.gather(*(execute_run(i) for i in range(10)))

    # Flush all background DB persistence tasks
    await tracer.flush()

    # Verify no active runs left in tracer.run_map
    assert len(tracer.run_map) == 0

    # Query DB to verify all 10 parent traces were persisted
    result = await db_session.execute(
        select(TraceEventModel).where(TraceEventModel.category == "llm")
    )
    events = result.scalars().all()
    persisted_run_ids = {e.run_id for e in events}

    expected_parent_ids = {f"00000000-0000-0000-0000-00000000000{i}" for i in range(10)}
    assert expected_parent_ids.issubset(persisted_run_ids)


@pytest.mark.asyncio
async def test_postgres_tracer_db_error_handling(db_session: AsyncSession):
    tracer = PostgresTracer()
    run_id = "22222222-2222-2222-2222-222222222222"

    with patch(
        "app.services.postgres_tracer.AsyncSessionLocal",
        side_effect=Exception("Database connection failure"),
    ):
        await tracer.on_chain_start(
            serialized={"name": "failing_chain"},
            inputs={"x": 1},
            run_id=run_id,
        )
        await tracer.on_chain_end(
            outputs={"y": 2},
            run_id=run_id,
        )

        # Flush should complete without raising any exception to the request thread
        await tracer.flush()


# --- Unit tests without Docker dependency ---


@pytest.mark.asyncio
async def test_unit_async_background_persistence():
    tracer = PostgresTracer()
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None

    with patch("app.services.postgres_tracer.AsyncSessionLocal", return_value=mock_cm):
        run_id = "11111111-1111-1111-1111-111111111111"
        await tracer.on_chain_start(
            serialized={"name": "test_chain"},
            inputs={"input": "hello"},
            run_id=run_id,
            name="test_chain",
        )
        await tracer.on_chain_end(
            outputs={"output": "world"},
            run_id=run_id,
        )
        await tracer.flush()

        assert mock_session.add.called
        assert mock_session.commit.called
        event = mock_session.add.call_args[0][0]
        assert event.run_id == run_id
        assert event.category == "llm"
        assert event.event_type == "chain"


@pytest.mark.asyncio
async def test_unit_concurrent_llm_runs():
    tracer = PostgresTracer()
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session
    mock_cm.__aexit__.return_value = None

    with patch("app.services.postgres_tracer.AsyncSessionLocal", return_value=mock_cm):

        async def execute_run(index: int):
            parent_id = f"00000000-0000-0000-0000-00000000000{index}"
            child_llm_id = f"00000000-0000-0000-0000-00000000001{index}"

            await tracer.on_chain_start(
                serialized={"name": f"parent_chain_{index}"},
                inputs={"q": f"question_{index}"},
                run_id=parent_id,
            )
            await tracer.on_llm_start(
                serialized={"name": "gpt-4o"},
                prompts=[f"prompt_{index}"],
                run_id=child_llm_id,
                parent_run_id=parent_id,
            )
            await asyncio.sleep(0.001)
            await tracer.on_llm_end(
                response=LLMResult(generations=[]),
                run_id=child_llm_id,
            )
            await tracer.on_chain_end(
                outputs={"a": f"answer_{index}"},
                run_id=parent_id,
            )

        await asyncio.gather(*(execute_run(i) for i in range(10)))
        await tracer.flush()

        assert len(tracer.run_map) == 0
        assert mock_session.add.call_count == 10


@pytest.mark.asyncio
async def test_unit_postgres_tracer_db_error_handling():
    tracer = PostgresTracer()
    run_id = "22222222-2222-2222-2222-222222222222"

    with patch(
        "app.services.postgres_tracer.AsyncSessionLocal",
        side_effect=Exception("Database connection failure"),
    ):
        await tracer.on_chain_start(
            serialized={"name": "failing_chain"},
            inputs={"x": 1},
            run_id=run_id,
        )
        await tracer.on_chain_end(
            outputs={"y": 2},
            run_id=run_id,
        )
        await tracer.flush()
