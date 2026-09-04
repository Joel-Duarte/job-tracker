import pytest
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompts import (
    DEFAULT_PROMPTS,
    clear_prompt_cache,
    get_prompt_template,
    seed_default_prompts,
)


def test_all_default_prompts_compile_and_have_valid_syntax():
    """Verify every prompt in DEFAULT_PROMPTS compiles cleanly with LangChain without unescaped brace errors."""
    assert "extraction" not in DEFAULT_PROMPTS
    assert len(DEFAULT_PROMPTS) == 15

    for _prompt_name, template_str in DEFAULT_PROMPTS.items():
        assert isinstance(template_str, str)
        assert len(template_str) > 20
        # ChatPromptTemplate parses all {placeholders} and enforces {{escaped_braces}}
        prompt_obj = ChatPromptTemplate.from_template(template_str)
        assert prompt_obj is not None

        # Format with dummy values for each identified variable to ensure string interpolation succeeds
        dummy_kwargs = {var: f"dummy_{var}" for var in prompt_obj.input_variables}
        formatted = prompt_obj.format(**dummy_kwargs)
        assert len(formatted) > len(template_str) or len(dummy_kwargs) == 0


@pytest.mark.asyncio
async def test_seed_and_get_prompt_template(db_session: AsyncSession):
    """Verify seeding into DB and retrieving cached prompts works for all 15 prompts."""
    clear_prompt_cache()
    await seed_default_prompts(db_session)

    for prompt_name in DEFAULT_PROMPTS:
        tmpl = await get_prompt_template(db_session, prompt_name)
        assert tmpl == DEFAULT_PROMPTS[prompt_name]

    # Verify cache invalidation
    clear_prompt_cache("jd_extraction")
    tmpl_reloaded = await get_prompt_template(db_session, "jd_extraction")
    assert tmpl_reloaded == DEFAULT_PROMPTS["jd_extraction"]
