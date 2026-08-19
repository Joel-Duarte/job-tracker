from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEmbeddingModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.services.llm import (
    async_enqueue_application_embedding,
    generate_and_save_application_embedding,
    generate_embedding,
)


@pytest.mark.asyncio
async def test_generate_embedding_decoupled():
    mock_embeddings = AsyncMock()
    mock_embeddings.aembed_documents.return_value = [[0.1] * 768]

    with patch(
        "app.services.llm.get_task_embeddings_model",
        new=AsyncMock(return_value=mock_embeddings),
    ):
        vec = await generate_embedding(db=None, text_input="Test embedding content")
        assert len(vec) == 768
        assert vec[0] == 0.1
        mock_embeddings.aembed_documents.assert_called_once_with(
            ["Test embedding content"]
        )


@pytest.mark.asyncio
async def test_generate_and_save_application_embedding_decoupled(
    db_session: AsyncSession,
):
    comp = CompanyModel(name="TechCorp", name_normalized="techcorp")
    db_session.add(comp)
    await db_session.flush()

    app_model = ApplicationModel(
        company_id=comp.id,
        position="Senior Software Engineer",
        position_normalized="senior software engineer",
        status="APPLIED",
        application_date=datetime.now(UTC),
    )
    db_session.add(app_model)
    await db_session.flush()

    event = ApplicationEventModel(
        email_application_id=app_model.id,
        email_event_type="APPLICATION_SUBMITTED",
        email_summary="Submitted application form online.",
        email_received_at=datetime.now(UTC),
    )
    db_session.add(event)
    await db_session.commit()

    mock_vector = [0.2] * 768

    with patch(
        "app.services.llm.generate_embedding",
        new=AsyncMock(return_value=mock_vector),
    ) as mock_gen_emb:
        result = await generate_and_save_application_embedding(
            db=db_session,
            application_id=app_model.id,
        )

        assert result is not None
        assert result.email_application_id == app_model.id
        assert "TechCorp" in result.content
        assert "Senior Software Engineer" in result.content
        assert result.metadata_["company"] == "TechCorp"
        assert result.embedding == mock_vector

        # Ensure generate_embedding was called without holding the session
        mock_gen_emb.assert_called_once()
        assert mock_gen_emb.call_args[0][0] is None


@pytest.mark.asyncio
async def test_async_enqueue_application_embedding_lifecycle(
    db_session: AsyncSession,
):
    comp = CompanyModel(name="Acme Inc", name_normalized="acme inc")
    db_session.add(comp)
    await db_session.flush()

    app_model = ApplicationModel(
        company_id=comp.id,
        position="Lead Platform Engineer",
        position_normalized="lead platform engineer",
        status="INTERVIEW",
    )
    db_session.add(app_model)
    await db_session.commit()

    mock_record = ApplicationEmbeddingModel(
        email_application_id=app_model.id,
        content="Sample content",
        metadata_={"company": "Acme Inc"},
        embedding=[0.3] * 768,
    )

    with patch(
        "app.services.llm.generate_and_save_application_embedding",
        new=AsyncMock(return_value=mock_record),
    ) as mock_save_emb:
        await async_enqueue_application_embedding(application_id=app_model.id)

        mock_save_emb.assert_called_once_with(
            db=None,
            application_id=app_model.id,
            skip_llm_summary=True,
        )

    # Verify IntakeEvaluationTaskModel was recorded and marked COMPLETED
    stmt = select(IntakeEvaluationTaskModel).where(
        IntakeEvaluationTaskModel.title_hint
        == f"Application {app_model.id} Vector Embedding"
    )
    res = await db_session.execute(stmt)
    task = res.scalar_one_or_none()
    assert task is not None
    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"


@pytest.mark.asyncio
async def test_embedding_network_timeout_and_failure_handling(
    db_session: AsyncSession,
):
    comp = CompanyModel(name="FailCo", name_normalized="failco")
    db_session.add(comp)
    await db_session.flush()

    app_model = ApplicationModel(
        company_id=comp.id,
        position="DevOps Specialist",
        position_normalized="devops specialist",
        status="APPLIED",
    )
    db_session.add(app_model)
    await db_session.commit()

    # Simulate network timeout exception during embedding generation
    with patch(
        "app.services.llm.generate_and_save_application_embedding",
        new=AsyncMock(side_effect=TimeoutError("Embedding service network timeout")),
    ):
        await async_enqueue_application_embedding(application_id=app_model.id)

    # Verify task was recorded and marked FAILED without orphaned sessions
    stmt = select(IntakeEvaluationTaskModel).where(
        IntakeEvaluationTaskModel.title_hint
        == f"Application {app_model.id} Vector Embedding"
    )
    res = await db_session.execute(stmt)
    task = res.scalar_one_or_none()
    assert task is not None
    assert task.status == "FAILED"
    assert "Embedding service network timeout" in (task.error_message or "")


@pytest.mark.asyncio
async def test_pgvector_cosine_distance_query(db_session: AsyncSession):
    comp = CompanyModel(name="VectorCorp", name_normalized="vectorcorp")
    db_session.add(comp)
    await db_session.flush()

    app_model = ApplicationModel(
        company_id=comp.id,
        position="AI Engineer",
        position_normalized="ai engineer",
        status="APPLIED",
    )
    db_session.add(app_model)
    await db_session.flush()

    vec_1 = [1.0] + [0.0] * 767

    emb_1 = ApplicationEmbeddingModel(
        email_application_id=app_model.id,
        content="AI Engineer Application",
        metadata_={"company": "VectorCorp"},
        embedding=vec_1,
    )
    db_session.add(emb_1)
    await db_session.commit()

    # Perform pgvector cosine distance query using SQLAlchemy / text
    query_vector = [1.0] + [0.0] * 767
    query_str = text(
        """
        SELECT email_application_id, content, embedding <=> :q_vec AS cosine_distance
        FROM email_application_embeddings
        ORDER BY embedding <=> :q_vec ASC
        LIMIT 1
        """
    )

    res = await db_session.execute(query_str, {"q_vec": str(query_vector)})
    row = res.first()

    assert row is not None
    assert row.email_application_id == app_model.id
    assert row.content == "AI Engineer Application"
    # Exact vector match should yield cosine distance ~0.0
    assert abs(row.cosine_distance) < 1e-4
