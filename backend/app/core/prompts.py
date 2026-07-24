# app/core/prompts.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prompts import PromptModel

DEFAULT_PROMPTS = {
    "extraction": (
        "Extract key information from the following email body regarding a job application. "
        "Provide accurate values for all fields according to the requested output structure.\n\n"
        "Email Content:\n{email_content}"
    ),
    "summarization": (
        "Summarize the current progress and status of a job application based on its historical timeline events. "
        "Keep the snapshot clear and direct.\n\n"
        "Timeline Events:\n{events_str}"
    ),
}


async def seed_default_prompts(session: AsyncSession) -> None:
    """Seeds missing prompts into DB upon boot without overwriting existing user edits."""
    for prompt_name, default_template in DEFAULT_PROMPTS.items():
        stmt = select(PromptModel).where(PromptModel.name == prompt_name)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            session.add(PromptModel(name=prompt_name, template=default_template))

    await session.commit()


async def get_prompt_template(session: AsyncSession, prompt_name: str) -> str:
    """Retrieves prompt template from DB, falling back to default if missing."""
    stmt = select(PromptModel.template).where(PromptModel.name == prompt_name)
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()

    if template:
        return template

    return DEFAULT_PROMPTS.get(prompt_name, "")