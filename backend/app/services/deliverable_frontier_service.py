"""Builds self-contained Markdown prompts for external Frontier models (Claude, ChatGPT, Gemini)."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.prompts import DEFAULT_PROMPTS, get_prompt_template
from app.models.applications import ApplicationModel
from app.models.candidate_profile import CandidateCVModel
from app.schemas.applications import (
    GenerateApplicationQuestionsRequest,
    GenerateCoverLetterRequest,
    GenerateInterviewGuideRequest,
)
from app.services.interview_guide_graph import (
    LANGUAGE_DISPLAY_NAMES,
    SECTION_DESCRIPTIONS,
)
from app.services.llm import (
    build_application_company_context,
    truncate_text_semantically,
)

_COVER_LETTER_LENGTH_LABELS = {
    "concise": "concise (120-180 words, 2-3 tight paragraphs)",
    "standard": "standard (250-320 words, 3-4 balanced paragraphs)",
    "detailed": "detailed (380-450 words, 4-5 comprehensive paragraphs)",
}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "application").lower()).strip("-")
    return slug[:48] or "application"


async def _load_application_frontier_context(
    db: AsyncSession,
    application_id: int,
    *,
    include_company_research: bool = True,
    custom_company_research: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stmt = (
        select(ApplicationModel)
        .where(ApplicationModel.id == application_id)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.events),
        )
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise ValueError("Application not found")

    company_name = app.company.name if app.company else "Target Company"
    position = app.position or "Target Role"

    cv_row = (await db.execute(select(CandidateCVModel).limit(1))).scalars().first()
    if cv_row:
        raw_cv = cv_row.anonymized_text or cv_row.raw_text or ""
        skills_line = ", ".join(cv_row.extracted_skills or [])
        cv_text = "\n".join(
            part
            for part in (
                f"Core Technical Skills: {skills_line}" if skills_line else "",
                truncate_text_semantically(raw_cv) if raw_cv else "",
            )
            if part
        )
    else:
        cv_text = "No candidate CV currently saved."

    if app.job_posting and app.job_posting.description_markdown:
        jd_text = truncate_text_semantically(app.job_posting.description_markdown)
    else:
        notes = " | ".join(e.email_summary for e in app.events if e.email_summary)
        jd_text = notes or f"Role: {position} at {company_name}."

    cr = None
    if include_company_research:
        cr = custom_company_research or (
            app.company.company_research if app.company else None
        )
    company_research_str = build_application_company_context(cr)

    return {
        "app": app,
        "company_name": company_name,
        "position": position,
        "cv_text": cv_text,
        "jd_text": jd_text,
        "company_research_str": company_research_str,
        "slug": _slugify(f"{company_name}-{position}"),
    }


def _safe_format(template: str, variables: dict[str, Any]) -> str:
    rendered = template
    for k, v in variables.items():
        rendered = rendered.replace("{" + k + "}", str(v))
    return rendered.replace("{{", "{").replace("}}", "}")


async def build_cover_letter_frontier_prompt(
    db: AsyncSession,
    application_id: int,
    payload: GenerateCoverLetterRequest | None = None,
) -> dict[str, str]:
    ctx = await _load_application_frontier_context(
        db,
        application_id,
        include_company_research=(
            payload.include_company_research
            if payload and payload.include_company_research is not None
            else True
        ),
        custom_company_research=payload.company_research if payload else None,
    )
    tone = ((payload.tone if payload else None) or "professional").strip().lower()
    length_code = ((payload.length if payload else None) or "standard").strip().lower()
    length_str = _COVER_LETTER_LENGTH_LABELS.get(
        length_code, _COVER_LETTER_LENGTH_LABELS["standard"]
    )
    custom_instr = (
        payload.custom_instructions.strip()
        if payload
        and payload.custom_instructions
        and payload.custom_instructions.strip()
        else ""
    )
    instr_block = "\n".join(
        p
        for p in (
            f"Custom User Instructions: {custom_instr}" if custom_instr else "",
            ctx["company_research_str"],
        )
        if p
    )

    tmpl = await get_prompt_template(db, "cover_letter")
    rendered = _safe_format(
        tmpl,
        {
            "company_name": ctx["company_name"],
            "position": ctx["position"],
            "tone": tone,
            "length": length_str,
            "custom_instructions": instr_block,
            "candidate_cv": ctx["cv_text"],
            "job_description": ctx["jd_text"],
        },
    )
    markdown_prompt = (
        f"# Frontier Cover Letter Task — {ctx['company_name']} ({ctx['position']})\n\n"
        "Follow the grounding rules strictly (never invent skills, companies, projects, or metrics absent from the candidate CV). "
        "Return ONLY the finished cover letter text ready to paste back into Job Tracker (no meta commentary).\n\n"
        f"{rendered}"
    )
    return {
        "markdown_prompt": markdown_prompt,
        "filename": f"cover-letter-prompt-{ctx['slug']}.md",
        "company_name": ctx["company_name"],
        "position": ctx["position"],
    }


async def build_questions_frontier_prompt(
    db: AsyncSession,
    application_id: int,
    payload: GenerateApplicationQuestionsRequest,
) -> dict[str, str]:
    ctx = await _load_application_frontier_context(
        db,
        application_id,
        include_company_research=payload.include_company_research,
        custom_company_research=payload.company_research,
    )
    q_list = []
    for q in payload.questions:
        item: dict[str, Any] = {"id": q.id, "question": q.question}
        if q.word_limit:
            item["word_limit"] = q.word_limit
        q_list.append(item)

    tone = (payload.tone or "professional").strip().lower()
    custom_instr = (
        f"\nCustom User Instructions: {payload.custom_instructions.strip()}"
        if payload.custom_instructions and payload.custom_instructions.strip()
        else ""
    )

    tmpl = await get_prompt_template(db, "application_qa")
    rendered = _safe_format(
        tmpl,
        {
            "company_name": ctx["company_name"],
            "position": ctx["position"],
            "tone": tone,
            "custom_instructions": custom_instr,
            "company_research_context": ctx["company_research_str"],
            "candidate_cv": ctx["cv_text"],
            "job_description": ctx["jd_text"],
            "questions_json": json.dumps(q_list, indent=2),
        },
    )
    markdown_prompt = (
        f"# Frontier Application Q&A Task — {ctx['company_name']} ({ctx['position']})\n\n"
        "Respond with ONLY a valid JSON array preserving the exact `id` and `question` keys so Job Tracker can import your answers directly.\n\n"
        f"{rendered}"
    )
    return {
        "markdown_prompt": markdown_prompt,
        "filename": f"application-qa-prompt-{ctx['slug']}.md",
        "company_name": ctx["company_name"],
        "position": ctx["position"],
    }


async def build_interview_guide_frontier_prompt(
    db: AsyncSession,
    application_id: int,
    payload: GenerateInterviewGuideRequest,
) -> dict[str, str]:
    ctx = await _load_application_frontier_context(
        db,
        application_id,
        include_company_research=payload.include_company_research,
        custom_company_research=payload.company_research,
    )
    lang_label = LANGUAGE_DISPLAY_NAMES.get(payload.language, "English")
    sec_blocks = [
        SECTION_DESCRIPTIONS[s]
        for s in (payload.selected_sections or list(SECTION_DESCRIPTIONS.keys()))
        if s in SECTION_DESCRIPTIONS
    ]
    if not sec_blocks:
        sec_blocks = list(SECTION_DESCRIPTIONS.values())
    sections_text = "\n\n".join(sec_blocks)

    tmpl = (
        await get_prompt_template(db, "interview_guide")
        or DEFAULT_PROMPTS["interview_guide"]
    )
    rendered = _safe_format(
        tmpl,
        {
            "cv_text": ctx["cv_text"],
            "language": lang_label,
            "company_name": ctx["company_name"],
            "position": ctx["position"],
            "company_context": ctx["company_research_str"]
            or "No additional company research provided.",
            "jd_text": ctx["jd_text"],
            "target_section": sections_text,
        },
    )
    markdown_prompt = (
        f"# Frontier Interview Prep Guide — {ctx['company_name']} ({ctx['position']})\n\n"
        f"Generate ALL requested modules below in **{lang_label}** using clean semantic HTML (`<h2>`, `<h3>`, `<p>`, `<ul>`, `<li>`, `<blockquote>`) or structured Markdown ready to import back into Job Tracker.\n\n"
        f"{rendered}"
    )
    return {
        "markdown_prompt": markdown_prompt,
        "filename": f"interview-guide-prompt-{ctx['slug']}.md",
        "company_name": ctx["company_name"],
        "position": ctx["position"],
    }
