import json
from typing import Any, Dict
from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.llm import EmailExtractionResult, ApplicationSummaryResult

# Initialize AsyncOpenAI pointing directly to LM Studio server configuration
llm_client = AsyncOpenAI(
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
)


async def extract_email_info(email_content: str) -> EmailExtractionResult:
    """Extracts structured job application information from email content."""
    
    prompt = (
        "Extract key information from the following email body regarding a job application. "
        "Provide accurate values for all fields according to the requested output structure.\n\n"
        f"Email Content:\n{email_content}"
    )

    response = await llm_client.beta.chat.completions.parse(
        model=settings.LLM_MODEL_NAME,
        temperature=0.2,
        top_p=1.0,
        messages=[
            {"role": "system", "content": "You parse job application emails into structured data."},
            {"role": "user", "content": prompt},
        ],
        response_format=EmailExtractionResult,
    )

    parsed = response.choices[0].message.parsed
    assert parsed is not None
    return parsed


async def summarize_application_status(events_timeline: list[Dict[str, Any]]) -> ApplicationSummaryResult:
    """Summarizes current application timeline state to feed semantic vector embeddings."""
    
    events_str = json.dumps(events_timeline, indent=2)
    prompt = (
        "Summarize the current progress and status of a job application based on its historical timeline events. "
        "Keep the snapshot clear and direct.\n\n"
        f"Timeline Events:\n{events_str}"
    )

    response = await llm_client.beta.chat.completions.parse(
        model=settings.LLM_MODEL_NAME,
        temperature=0.1,
        top_p=1.0,
        messages=[
            {"role": "system", "content": "You summarize job application timelines for embeddings."},
            {"role": "user", "content": prompt},
        ],
        response_format=ApplicationSummaryResult,
    )

    parsed = response.choices[0].message.parsed
    assert parsed is not None
    return parsed