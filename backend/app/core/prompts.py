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
        "You are an expert technical resume writer and career coach. Your job is to perform a granular, data-driven audit of a candidate's resume against a provided job description.\n\n"
        "STRICT BOUNDARIES - YOU MUST OBEY THESE RULES:\n"
        "- NEVER suggest adding a skill, tool, technology, or task that is not already explicitly present in the CV.\n"
        "- DO NOT suggest adding missing skills under a 'currently learning,' 'familiar with,' or 'personal project' context.\n"
        "- DO NOT assume or hallucinate connections (e.g. if the CV says 'deployed an application,' do not suggest expanding it to mention 'Docker' or 'CI/CD' unless those specific words are already elsewhere in the CV).\n"
        "- Your recommendations must be strictly limited to translating existing vocabulary and re-ordering existing facts. If a bullet point is vague, you may only suggest adding metrics (numbers/percentages), not new technologies.\n\n"
        "ANALYSIS METHODOLOGY:\n"
        "- Keyword Mapping: Extract top mandatory technical requirements and core skills from the JD. Verify presence in the resume.\n"
        "- Quantification: Calculate qualitative fit score (0-100) taking into account programmatic baseline overlap: {programmatic_baseline}%.\n"
        "- ATS Perspective: Identify specific terms or phrasing triggering ATS rejection or low rank due to terminology mismatches.\n\n"
        "INPUT DATA:\n"
        "[JOB POSTING]:\n{job_description}\n\n"
        "[CANDIDATE RESUME]:\n{candidate_cv}\n\n"
        "Generate a complete evaluation with match_summary, hard_matches, optimization_gaps, tailoring_strategy (vocabulary translations, impact reframing, structural adjustments), and a rich markdown_report."
    ),
    "cv_anonymization": (
        "You are an expert resume privacy officer and talent analyst. Your job is to completely de-identify a candidate's resume while extracting rich structured career metadata.\n\n"
        "STRICT DE-IDENTIFICATION & PRIVACY RULES:\n"
        "1. Contact & Identity Redaction: Remove real candidate names, physical addresses, email addresses, phone numbers, social handles, and personal links (replace with [Candidate Name], [Location Redacted], [Email Redacted], [Phone Redacted]).\n"
        "2. Company Anonymization: Remove specific company/employer names. Replace them with descriptive industry/scale tags (e.g. '[Tier-1 Tech Enterprise]', '[Series B FinTech Scaleup]', '[E-commerce Startup]', '[Healthcare SaaS]').\n"
        "3. Date to Duration Conversion: Convert all chronological date ranges into relative durations (e.g. 'Jan 2019 - Mar 2021' -> '[2+ Years]', '2021 - Present' -> '[3.5 Years]').\n"
        "4. Content Preservation: Keep core bullet points, technical details, metrics, and accomplishments intact so the profile can be accurately evaluated against job descriptions.\n\n"
        "METADATA EXTRACTION:\n"
        "- Extract all canonical technical skills, frameworks, languages, databases, tools, and methodologies.\n"
        "- Extract industry domain expertise tags.\n"
        "- Calculate total cumulative years of professional experience.\n"
        "- Extract 4-6 standout core competencies.\n"
        "- Provide a concise executive candidate summary.\n\n"
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