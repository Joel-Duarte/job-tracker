import json
from typing import Any, Dict
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import get_prompt_template
from app.models.applications import ApplicationEmbeddingModel, ApplicationModel
from app.schemas.llm import ApplicationSummaryResult, EmailExtractionResult

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


async def generate_embedding(text_input: str) -> list[float]:
    """Generates vector embeddings using the configured LLM client."""
    # Uses the standard OpenAI-compatible embeddings endpoint
    response = await llm_client.embeddings.create(
        model=getattr(settings, "LLM_EMBEDDING_MODEL_NAME", settings.LLM_MODEL_NAME),
        input=text_input,
    )
    return response.data[0].embedding


async def generate_and_save_application_embedding(
    db: AsyncSession, application_id: int
) -> ApplicationEmbeddingModel:
    """
    Summarizes application history, generates vector representation, 
    and updates/inserts record in email_application_embeddings.
    """
    # 1. Retrieve application along with related events
    stmt = select(ApplicationModel).where(ApplicationModel.id == application_id)
    res = await db.execute(stmt)
    application = res.scalar_one_or_none()

    if not application:
        raise ValueError(f"Application ID {application_id} not found.")

    # 2. Build structured timeline array for LLM summarization
    events_timeline = []
    for event in application.events:
        events_timeline.append({
            "event_type": event.email_event_type,
            "received_at": event.email_received_at.isoformat() if event.email_received_at else None,
            "subject": event.email_subject,
            "summary": event.email_summary,
            "status_after_event": event.email_status_after_event,
        })

    # 3. Summarize timeline using LLM
    summary_result = await summarize_application_status(db, events_timeline)
    content_to_embed = getattr(summary_result, "summary", None)
    if content_to_embed is None:
        for alt_field in ("summary_text", "application_summary", "result", "text"):
            content_to_embed = getattr(summary_result, alt_field, None)
            if content_to_embed is not None:
                break
    if content_to_embed is None:
        raise ValueError("Unable to extract summary text from ApplicationSummaryResult.")

    # 4. Generate float vector
    vector = await generate_embedding(content_to_embed)

    # 5. Insert or update embedding record in DB
    emb_stmt = select(ApplicationEmbeddingModel).where(
        ApplicationEmbeddingModel.email_application_id == application_id
    )
    emb_res = await db.execute(emb_stmt)
    embedding_record = emb_res.scalar_one_or_none()

    metadata_payload = {
        "company": application.company.name if application.company else None,
        "position": application.position,
        "status": application.status,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
    }

    if not embedding_record:
        embedding_record = ApplicationEmbeddingModel(
            email_application_id=application_id,
            content=content_to_embed,
            metadata_=metadata_payload,
            embedding=vector,
        )
        db.add(embedding_record)
    else:
        embedding_record.content = content_to_embed
        embedding_record.metadata_ = metadata_payload
        embedding_record.embedding = vector

    await db.commit()
    return embedding_record