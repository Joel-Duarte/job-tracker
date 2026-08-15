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
    "assessment": (
        "You are an expert technical recruiter and career coach. Analyze the following job description for pre-application qualification. "
        "Extract company name, position, required skills, compensation range, and evaluate the match score (0-100), key strengths, and missing qualification keywords.\n\n"
        "Job Description:\n{job_description}"
    ),
    "agent_system": (
        "You are the intelligent Job Tracker Agent. You help the user manage, query, and optimize their job search pipeline.\n"
        "You have access to tools for semantic vector search, querying application timelines, listing statuses, and updating application records.\n"
        "When performing actions that modify data (e.g. updating statuses, deleting items), summarize what you are about to do clearly."
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