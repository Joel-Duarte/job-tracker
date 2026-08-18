import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.models.applications import ApplicationModel
from app.models.candidate_profile import CandidateCVModel
from app.services.postgres_tracer import PostgresTracer

logger = logging.getLogger(__name__)


class CoverLetterLLMResult(BaseModel):
    cover_letter_markdown: str = Field(
        description="The complete cover letter formatted in clean Markdown."
    )
    highlighted_skills: list[str] = Field(
        default_factory=list,
        description="List of candidate skills emphasized in the cover letter.",
    )


async def generate_cover_letter_chain(
    db: AsyncSession,
    company_name: str,
    job_title: str,
    job_description: str | None = None,
    candidate_cv: str | None = None,
    candidate_skills: list[str] | None = None,
    candidate_experience: str | None = None,
    custom_instructions: str | None = None,
    tone: str | None = None,
) -> CoverLetterLLMResult:
    """
    Builds and executes the LangChain generation chain for cover letter creation.
    Wraps LLM call with PostgresTracer() for 'llm' telemetry category.
    """
    llm = await get_task_chat_model(db, task_type="COVER_LETTER", temperature=0.4)
    structured_llm = llm.with_structured_output(CoverLetterLLMResult)
    template_str = await get_prompt_template(db, "cover_letter")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert executive resume writer and cover letter strategist.",
            ),
            ("human", template_str),
        ]
    )

    skills_str = (
        ", ".join(candidate_skills)
        if candidate_skills
        else "General Software Engineering Profile"
    )
    chain_inputs: dict[str, Any] = {
        "company_name": company_name or "Target Employer",
        "job_title": job_title or "Target Position",
        "job_description": job_description or "Standard engineering responsibilities.",
        "candidate_cv": candidate_cv or "Candidate profile",
        "candidate_skills": skills_str,
        "candidate_experience": candidate_experience or "General experience",
        "custom_instructions": custom_instructions or "None",
        "tone": tone or "Professional and confident",
    }

    try:
        chain = prompt | structured_llm
        result = await chain.ainvoke(
            chain_inputs,
            config={"callbacks": [PostgresTracer()]},
        )
        if isinstance(result, CoverLetterLLMResult):
            return result
        return CoverLetterLLMResult.model_validate(result)
    except Exception as err:
        logger.warning(
            "Structured cover letter generation fallback triggered due to error: %s",
            err,
        )
        raw_chain = prompt | llm
        response = await raw_chain.ainvoke(
            chain_inputs,
            config={"callbacks": [PostgresTracer()]},
        )
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        return CoverLetterLLMResult(
            cover_letter_markdown=content.strip(),
            highlighted_skills=candidate_skills[:5] if candidate_skills else [],
        )


async def generate_cover_letter_for_application(
    db: AsyncSession,
    application_id: int,
    custom_instructions: str | None = None,
    tone: str | None = None,
) -> CoverLetterLLMResult:
    """
    Retrieves application details, linked job posting, and candidate profile,
    then executes cover letter generation.
    """
    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            joinedload(ApplicationModel.job_posting),
        )
        .where(ApplicationModel.id == application_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise ValueError(f"Application ID {application_id} not found.")

    company_name = app.company.name if app.company else "Company"
    position = app.position or "Software Engineer"
    jd_text = (
        app.job_posting.description_markdown
        if app.job_posting and app.job_posting.description_markdown
        else f"Position: {position} at {company_name}"
    )

    # Fetch active CV profile
    cv_stmt = select(CandidateCVModel).where(CandidateCVModel.is_active).limit(1)
    cv_res = await db.execute(cv_stmt)
    active_cv = cv_res.scalars().first()

    cv_text = (
        active_cv.anonymized_text or active_cv.raw_text
        if active_cv
        else "Candidate Resume"
    )
    skills = active_cv.extracted_skills if active_cv else []

    exp_str = None
    if active_cv and active_cv.domain_experience:
        exp_list = [
            f"{item.get('domain')} ({item.get('years')} yrs)"
            for item in active_cv.domain_experience
            if item.get("is_active", True)
        ]
        if exp_list:
            exp_str = ", ".join(exp_list)

    return await generate_cover_letter_chain(
        db=db,
        company_name=company_name,
        job_title=position,
        job_description=jd_text,
        candidate_cv=cv_text,
        candidate_skills=skills,
        candidate_experience=exp_str,
        custom_instructions=custom_instructions,
        tone=tone,
    )
