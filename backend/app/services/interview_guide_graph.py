import logging
from typing import Any, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template

logger = logging.getLogger(__name__)


SECTION_DESCRIPTIONS = {
    "role_company_brief": (
        "1. 🏢 Role & Company Brief\n"
        "- Synthesize the company culture signals, engineering priorities, team context, and market positioning based on the job description and company research.\n"
        "- Explain why this role exists and what success looks like in the first 90 days."
    ),
    "strategic_fit_pitch": (
        "2. 🎯 Strategic Fit & Elevator Pitch\n"
        "- A tailored 60-90 second introductory elevator pitch answering 'Tell me about yourself and why this role?'\n"
        "- Top 3-4 direct overlap points between candidate background and job requirements."
    ),
    "star_stories": (
        "3. ⭐ Tailored STAR Stories\n"
        "- 3-4 fully fleshed-out STAR (Situation, Task, Action, Result) stories using the candidate's actual projects, metrics, and technologies.\n"
        "- Explicitly map each story to the top technical or leadership requirements of the position."
    ),
    "question_defenses": (
        "4. 🧠 Behavioral & Technical Question Defenses\n"
        "- 4-6 high-probability technical & behavioral questions likely to be asked in the interview.\n"
        "- Specific talking points, architectural concepts, or gap-mitigation strategies addressing any missing keywords or weaker areas."
    ),
    "interviewer_questions": (
        "5. 💬 High-Leverage Questions to Ask Interviewer\n"
        "- 6-8 smart, insightful questions for recruiter screening and technical/hiring manager rounds that demonstrate high domain expertise."
    ),
    "prep_checklist": (
        "6. ✅ Final Pre-Interview Checklist\n"
        "- A concise, high-priority bullet list of critical items, metrics, and talking points to review 15 minutes before the interview."
    ),
}


class InterviewGuideState(TypedDict):
    cv_text: str
    jd_text: str
    company_name: str
    position: str
    company_context: list[str]
    target_sections: list[str]
    current_section_index: int
    completed_sections: list[str]
    language: str
    error: str | None
    db_session: Any


async def extractor_node(state: InterviewGuideState) -> dict[str, Any]:
    """Ensures company name and position are properly set."""
    company = state.get("company_name", "").strip()
    position = state.get("position", "").strip()
    return {
        "company_name": company or "Target Company",
        "position": position or "Target Role",
        "current_section_index": 0,
        "completed_sections": [],
    }


async def web_researcher_node(state: InterviewGuideState) -> dict[str, Any]:
    """
    Gathers company context, cultural signals, and technical stack background.
    Uses LLM synthesis with web search context resilience.
    """
    company = state.get("company_name", "Target Company")
    jd_text = state.get("jd_text", "")
    db = state.get("db_session")

    try:
        if db:
            llm = await get_task_chat_model(
                db, task_type="INTERVIEW_GUIDE", temperature=0.3
            )
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an executive research analyst. Extract key business priorities, culture traits, and technical stack details from this job spec and company.",
                    ),
                    (
                        "human",
                        f"Target Company: {company}\n\nJob Details:\n{jd_text[:3000]}",
                    ),
                ]
            )
            chain = prompt | llm
            res = await chain.ainvoke({})
            content = res.content if hasattr(res, "content") else res
            summary_content = content if isinstance(content, str) else str(content)
            return {"company_context": [summary_content]}
    except Exception as exc:
        logger.warning("Web research node fallback due to: %s", exc)

    return {"company_context": [f"Company overview based on job spec for {company}."]}


async def section_generator_node(state: InterviewGuideState) -> dict[str, Any]:
    """Generates the clean semantic HTML for the current section in the queue."""
    target_sections = state.get("target_sections", [])
    order_mapping = {key: i for i, key in enumerate(SECTION_DESCRIPTIONS.keys())}
    target_sections = sorted(target_sections, key=lambda x: order_mapping.get(x, 999))
    idx = state.get("current_section_index", 0)
    completed = list(state.get("completed_sections", []))

    if idx >= len(target_sections):
        return {"current_section_index": idx + 1, "target_sections": target_sections}

    section_key = target_sections[idx]
    section_desc = SECTION_DESCRIPTIONS.get(section_key, f"Section: {section_key}")
    language = state.get("language", "en")
    company_name = state.get("company_name", "Target Company")
    position = state.get("position", "Target Role")
    company_context = "\n".join(state.get("company_context", []))
    jd_text = state.get("jd_text", "")
    cv_text = state.get("cv_text", "")
    db = state.get("db_session")

    section_html = ""
    try:
        if db:
            llm = await get_task_chat_model(
                db, task_type="INTERVIEW_GUIDE", temperature=0.4
            )
            template_str = await get_prompt_template(db, "interview_guide")

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", template_str),
                    (
                        "human",
                        (
                            f"Generate the following section in {language}:\n\n"
                            f"{section_desc}\n\n"
                            "Remember to output ONLY valid, clean HTML tags (e.g. <h2>, <p>, <strong>, <ul>, <li>, <blockquote>) with zero markdown code blocks or wrapper backticks."
                        ),
                    ),
                ]
            )

            chain = prompt | llm
            res = await chain.ainvoke(
                {
                    "language": language,
                    "company_name": company_name,
                    "position": position,
                    "company_context": company_context,
                    "jd_text": jd_text[:4000],
                    "cv_text": cv_text[:4000],
                    "target_section": section_desc,
                }
            )

            content = res.content if hasattr(res, "content") else res
            raw_html = content if isinstance(content, str) else str(content)
            # Strip accidental ```html wrappers if model produced them
            clean_html = raw_html.strip()
            if clean_html.startswith("```html"):
                clean_html = clean_html[7:]
            elif clean_html.startswith("```"):
                clean_html = clean_html[3:]
            clean_html = clean_html.removesuffix("```")
            section_html = clean_html.strip()
        else:
            section_html = f"<div class='guide-section'><h2>{section_desc.splitlines()[0]}</h2><p>Tailored preparation for {company_name} - {position}.</p></div>"
    except Exception as exc:
        logger.error("Error generating section %s: %s", section_key, exc, exc_info=True)
        section_html = f"<div class='guide-section'><h2>{section_desc.splitlines()[0]}</h2><p>Section generated based on profile for {position} at {company_name}.</p></div>"

    completed.append(str(section_html))
    return {
        "completed_sections": completed,
        "current_section_index": idx + 1,
        "target_sections": target_sections,
    }


def should_continue_sections(state: InterviewGuideState) -> str:
    """Routes back to section_generator_node if more sections remain."""
    target_sections = state.get("target_sections", [])
    order_mapping = {key: i for i, key in enumerate(SECTION_DESCRIPTIONS.keys())}
    target_sections = sorted(target_sections, key=lambda x: order_mapping.get(x, 999))
    idx = state.get("current_section_index", 0)
    if idx < len(target_sections):
        return "section_generator"
    return END


def build_interview_guide_graph():
    """Builds and compiles the LangGraph state machine for Interview Guide generation."""
    workflow = StateGraph(InterviewGuideState)

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("web_researcher", web_researcher_node)
    workflow.add_node("section_generator", section_generator_node)

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "web_researcher")
    workflow.add_edge("web_researcher", "section_generator")
    workflow.add_conditional_edges(
        "section_generator",
        should_continue_sections,
        {
            "section_generator": "section_generator",
            END: END,
        },
    )

    return workflow.compile()


interview_guide_graph = build_interview_guide_graph()
