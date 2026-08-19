import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm_factory import (
    _EMBEDDINGS_CACHE,
    clear_embeddings_cache,
    get_embeddings_model,
)
from app.core.prompts import (
    _PROMPT_CACHE,
    clear_prompt_cache,
    get_prompt_template,
)
from app.routers.agent_chat import prune_and_sanitize_tool_output
from app.services.llm import split_text_semantically, truncate_text_semantically


def test_semantic_truncation_and_splitting():
    """Test split_text_semantically and truncate_text_semantically."""
    short_text = "Short job description text."
    assert truncate_text_semantically(short_text, max_chars=100) == short_text

    long_text = ("## Section Header\n" + "Word " * 200 + "\n\n") * 50
    truncated = truncate_text_semantically(long_text, max_chars=500)
    assert len(truncated) <= 500
    assert len(truncated) > 0

    chunks = split_text_semantically(long_text, chunk_size=200, chunk_overlap=10)
    assert len(chunks) > 1


def test_prune_and_sanitize_tool_output():
    """Test prune_and_sanitize_tool_output utility."""
    payload = {
        "metadata": {"raw": "secret"},
        "items": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "name": "Test",
    }
    sanitized = prune_and_sanitize_tool_output(payload, max_array_length=5)
    parsed = json.loads(sanitized)
    assert "metadata" not in parsed
    assert parsed["name"] == "Test"
    assert len(parsed["items"]) == 5
    assert parsed["items"] == [1, 2, 3, 4, 5]

    raw_str_json = json.dumps(payload)
    sanitized_str = prune_and_sanitize_tool_output(raw_str_json, max_array_length=3)
    parsed_str = json.loads(sanitized_str)
    assert len(parsed_str["items"]) == 3

    assert prune_and_sanitize_tool_output("plain text error") == "plain text error"


@pytest.mark.asyncio
async def test_prompt_caching_unit():
    """Unit test for in-memory prompt template cache and invalidation without DB."""
    clear_prompt_cache()
    assert len(_PROMPT_CACHE) == 0

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = (
        "Template content for {raw_webpage_data}"
    )
    mock_session.execute.return_value = mock_result

    # First call - queries session
    tmpl1 = await get_prompt_template(mock_session, "jd_extraction")
    assert "jd_extraction" in _PROMPT_CACHE
    assert mock_session.execute.call_count == 1

    # Second call - returns from cache
    tmpl2 = await get_prompt_template(mock_session, "jd_extraction")
    assert tmpl1 == tmpl2
    assert mock_session.execute.call_count == 1

    # Invalidate cache
    clear_prompt_cache("jd_extraction")
    assert "jd_extraction" not in _PROMPT_CACHE

    # Third call - queries session again
    await get_prompt_template(mock_session, "jd_extraction")
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_embeddings_caching_unit():
    """Unit test for Embeddings model instance caching and invalidation."""
    clear_embeddings_cache()
    assert len(_EMBEDDINGS_CACHE) == 0

    with patch(
        "app.core.llm_factory.get_active_llm_config_dict", new_callable=AsyncMock
    ) as mock_cfg:
        mock_cfg.return_value = {
            "provider_name": "openai",
            "embedding_model_name": "text-embedding-3-small",
            "api_base": None,
            "api_key": "test-key",
        }
        with patch("app.core.llm_factory.init_embeddings") as mock_init:
            mock_emb = AsyncMock()
            mock_init.return_value = mock_emb

            emb1 = await get_embeddings_model(None)
            assert mock_init.call_count == 1
            assert len(_EMBEDDINGS_CACHE) == 1

            emb2 = await get_embeddings_model(None)
            assert emb1 is emb2
            assert mock_init.call_count == 1

            clear_embeddings_cache()
            assert len(_EMBEDDINGS_CACHE) == 0


@pytest.mark.asyncio
async def test_interview_guide_generator_stream():
    """Unit test for generate_interview_guide_stream async generator."""
    from app.schemas.applications import GenerateInterviewGuideRequest
    from app.services.interview_guide import generate_interview_guide_stream

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None  # Application not found case
    mock_session.execute.return_value = mock_res

    req = GenerateInterviewGuideRequest(selected_sections=["role_company_brief"])
    stream = generate_interview_guide_stream(mock_session, 999, req)

    chunks = []
    async for chunk in stream:
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "Application ID 999 not found" in chunks[0]
