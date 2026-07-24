import json
from typing import Any, Dict
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import get_prompt_template
from app.schemas.llm import EmailExtractionResult, ApplicationSummaryResult

llm_client = AsyncOpenAI(
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
)


async def extract_email_info(db: AsyncSession, email_content: str) -> EmailExtractionResult:
    """Fetches prompt from DB and parses email content using LM Studio."""
    template = await get_prompt_template(db, "extraction")
    prompt = template.format(email_content=email_content)

    response = await llm_client.beta.chat.completions.parse(
        model=settings.LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You parse job application emails into structured data."},
            {"role": "user", "content": prompt},
        ],
        response_format=EmailExtractionResult,
    )

    parsed = response.choices[0].message.parsed
    assert parsed is not None
    return parsed


async def summarize_application_status(
    db: AsyncSession, events_timeline: list[Dict[str, Any]]
) -> ApplicationSummaryResult:
    """Fetches prompt from DB and summarizes timeline events for embeddings."""
    events_str = json.dumps(events_timeline, indent=2)
    template = await get_prompt_template(db, "summarization")
    prompt = template.format(events_str=events_str)

    response = await llm_client.beta.chat.completions.parse(
        model=settings.LLM_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You summarize job application timelines for embeddings."},
            {"role": "user", "content": prompt},
        ],
        response_format=ApplicationSummaryResult,
    )

    parsed = response.choices[0].message.parsed
    assert parsed is not None
    return parsed

    