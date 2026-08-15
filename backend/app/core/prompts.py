from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prompts import PromptModel

DEFAULT_PROMPTS = {
    "jd_extraction": (
        "You are an expert recruitment data analyst. Your job is to review raw scraped website markdown text or pasted job specs and extract the essential job details.\n\n"
        "STRICT EXTRACTION BOUNDARIES:\n"
        "- Completely disregard any navigation links, cookie popups, footers, headers, ads, or legal notices.\n"
        "- Do not add any introductory text, pleasantries, or conclusions.\n"
        "- If the provided text does not contain an actual job description or job posting, you must set the 'job_found' key to false and leave the details as 'Not Specified'.\n\n"
        "Raw Webpage / Job Data:\n{raw_webpage_data}"
    ),
    "email_extraction": (
        "Extract key information from the following email body regarding a job application. "
        "Provide accurate values for all fields according to the requested output structure.\n\n"
        "Email Content:\n{email_content}"
    ),
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
        "You are an expert technical recruiter and career coach. Analyze the following job description for pre-application qualification.\n"
        "Candidate Known Skills: {candidate_skills}\n"
        "Programmatic Overlap Baseline: {programmatic_baseline}%\n\n"
        "Extract company name, position, required skills, compensation range, and evaluate the qualitative AI fit score (0-100), key matching strengths, missing keywords, and pros/cons.\n\n"
        "Job Description:\n{job_description}"
    ),
    "cv_anonymization": (
        "You are an expert resume privacy officer and talent analyst. De-identify the provided resume: remove real names, addresses, emails, phone numbers, and specific company names (replace company names with industry tags like [Fintech Scaleup], [Tech Enterprise], [Early-stage Startup]).\n"
        "Convert all date ranges into relative durations (e.g. '2018-2020' -> '2 years', '2021 - Present' -> '3.5 years').\n"
        "Extract canonical technical skills, total years of experience, and industry domains.\n\n"
        "Resume Content:\n{resume_text}"
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

    # Fallback to defaults
    if prompt_name in DEFAULT_PROMPTS:
        return DEFAULT_PROMPTS[prompt_name]

    if prompt_name == "email_extraction":
        return DEFAULT_PROMPTS.get("extraction", "")

    return ""