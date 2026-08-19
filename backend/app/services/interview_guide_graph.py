import logging
import operator
from typing import Annotated, Any, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.services.postgres_tracer import PostgresTracer

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
    section_results: Annotated[list[dict[str, Any]], operator.add]
    completed_sections: list[str]
    language: str
    error: str | None


class SectionWorkerState(TypedDict):
    section_key: str
    section_index: int
    section_desc: str
    language: str
    company_name: str
    position: str
    company_context: str
    jd_text: str
    cv_text: str


async def extractor_node(state: InterviewGuideState) -> dict[str, Any]:
    """Ensures company name and position are properly set."""
    company = state.get("company_name", "").strip()
    position = state.get("position", "").strip()
    return {
        "company_name": company or "Target Company",
        "position": position or "Target Role",
        "section_results": [],
        "completed_sections": [],
    }


async def web_researcher_node(
    state: InterviewGuideState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """
    Gathers company context, cultural signals, and technical stack background.
    Uses LLM synthesis with web search context resilience.
    """
    company = state.get("company_name", "Target Company")
    jd_text = state.get("jd_text", "")
    db = (
        config.get("configurable", {}).get("db")
        if config and "configurable" in config
        else None
    )

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
            res = await chain.ainvoke(
                {},
                config={"callbacks": [PostgresTracer()]},
            )
            content = res.content if hasattr(res, "content") else res
            summary_content = content if isinstance(content, str) else str(content)
            return {"company_context": [summary_content]}
    except Exception as exc:
        logger.warning("Web research node fallback due to: %s", exc)

    return {"company_context": [f"Company overview based on job spec for {company}."]}


def continue_to_sections(state: InterviewGuideState) -> list[Send] | str:
    """Fans out target_sections concurrently into parallel section_generator workers."""
    target_sections = state.get("target_sections", [])
    order_mapping = {key: i for i, key in enumerate(SECTION_DESCRIPTIONS.keys())}
    sorted_sections = sorted(target_sections, key=lambda x: order_mapping.get(x, 999))

    if not sorted_sections:
        return "consolidate"

    company_name = state.get("company_name", "Target Company")
    position = state.get("position", "Target Role")
    company_context = "\n".join(state.get("company_context", []))
    jd_text = state.get("jd_text", "")
    cv_text = state.get("cv_text", "")
    language = state.get("language", "en")

    sends = []
    for idx, sec_key in enumerate(sorted_sections):
        sec_desc = SECTION_DESCRIPTIONS.get(sec_key, f"Section: {sec_key}")
        worker_state: SectionWorkerState = {
            "section_key": sec_key,
            "section_index": idx,
            "section_desc": sec_desc,
            "language": language,
            "company_name": company_name,
            "position": position,
            "company_context": company_context,
            "jd_text": jd_text,
            "cv_text": cv_text,
        }
        sends.append(Send("section_generator", worker_state))

    return sends


async def section_generator_node(
    state: SectionWorkerState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Generates the clean semantic HTML for a single section independently in parallel."""
    section_key = state.get("section_key", "")
    section_index = state.get("section_index", 0)
    section_desc = state.get("section_desc", "")
    language = state.get("language", "en")
    company_name = state.get("company_name", "Target Company")
    position = state.get("position", "Target Role")
    company_context = state.get("company_context", "")
    jd_text = state.get("jd_text", "")
    cv_text = state.get("cv_text", "")
    db = (
        config.get("configurable", {}).get("db")
        if config and "configurable" in config
        else None
    )

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
                },
                config={"callbacks": [PostgresTracer()]},
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

    return {
        "section_results": [
            {
                "key": section_key,
                "index": section_index,
                "html": section_html,
            }
        ]
    }


async def consolidate_node(state: InterviewGuideState) -> dict[str, Any]:
    """Aggregates all completed parallel section results in canonical order."""
    results = state.get("section_results", [])
    sorted_results = sorted(results, key=lambda x: x.get("index", 0))
    completed_htmls = [item["html"] for item in sorted_results]
    return {"completed_sections": completed_htmls}


def build_interview_guide_graph():
    """Builds and compiles the LangGraph state machine for Interview Guide generation."""
    workflow = StateGraph(InterviewGuideState)

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("web_researcher", web_researcher_node)
    workflow.add_node("section_generator", section_generator_node)
    workflow.add_node("consolidate", consolidate_node)

    workflow.add_edge(START, "extractor")
    workflow.add_edge("extractor", "web_researcher")
    workflow.add_conditional_edges(
        "web_researcher",
        continue_to_sections,
        ["section_generator", "consolidate"],
    )
    workflow.add_edge("section_generator", "consolidate")
    workflow.add_edge("consolidate", END)

    from app.core.database import postgres_saver

    return workflow.compile(checkpointer=postgres_saver)


interview_guide_graph = build_interview_guide_graph()
