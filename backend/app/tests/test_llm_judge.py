from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableLambda

from app.schemas.llm import HallucinationAuditResult
from app.services.llm_judge import audit_generation_grounding


@pytest.mark.asyncio
async def test_audit_generation_grounding_passed():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_response = MagicMock()
    mock_response.content = '```json\n{"passed": true, "confidence_score": 0.95, "unverified_claims": [], "critique": "All facts grounded in CV"}\n```'

    # Use RunnableLambda to properly behave as a LangChain Runnable component
    mock_model = RunnableLambda(lambda x: mock_response)

    with (
        patch(
            "app.services.llm_judge.get_prompt_template",
            new=AsyncMock(return_value="Judge prompt template"),
        ),
        patch(
            "app.services.llm_judge.get_task_chat_model",
            new=AsyncMock(return_value=mock_model),
        ),
    ):
        result = await audit_generation_grounding(
            db=mock_db,
            candidate_cv="Candidate with 5 years Python and PostgreSQL experience.",
            generated_text="I have 5 years of experience with Python and PostgreSQL.",
            context_label="Stripe Cover Letter",
            task_type="COVER_LETTER",
        )

        assert isinstance(result, HallucinationAuditResult)
        assert result.passed is True
        assert len(result.unverified_claims) == 0
        assert mock_db.add.called


@pytest.mark.asyncio
async def test_audit_generation_grounding_flagged():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_response = MagicMock()
    mock_response.content = '{"passed": false, "confidence_score": 0.8, "unverified_claims": ["PhD in Computer Science from MIT"], "critique": "Candidate does not have a PhD"}'

    mock_model = RunnableLambda(lambda x: mock_response)

    with (
        patch(
            "app.services.llm_judge.get_prompt_template",
            new=AsyncMock(return_value="Judge prompt template"),
        ),
        patch(
            "app.services.llm_judge.get_task_chat_model",
            new=AsyncMock(return_value=mock_model),
        ),
    ):
        result = await audit_generation_grounding(
            db=mock_db,
            candidate_cv="Candidate with 5 years Python and PostgreSQL experience.",
            generated_text="I hold a PhD in Computer Science from MIT.",
            context_label="Linear QA",
            task_type="APPLICATION_QA",
        )

        assert isinstance(result, HallucinationAuditResult)
        assert result.passed is False
        assert "PhD in Computer Science from MIT" in result.unverified_claims
        assert mock_db.add.called
