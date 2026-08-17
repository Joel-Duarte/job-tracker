import json
import logging
from typing import Annotated, Any

from langchain_core.messages import AnyMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph, add_messages
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing_extensions import TypedDict

from app.core.database import postgres_saver
from app.core.llm_factory import get_task_chat_model
from app.models.applications import ApplicationModel

logger = logging.getLogger(__name__)


class MockInterviewState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    interview_type: str
    application_id: int
    job_context: str
    required_skills: list[str]
    evaluations: list[dict[str, Any]]


class PresentMultipleChoiceQuestion(BaseModel):
    """Present a multiple choice question to the user."""

    question: str = Field(description="The question to ask.")
    options: list[str] = Field(description="The options to choose from.")


class PresentOpenEndedQuestion(BaseModel):
    """Present an open ended question to the user."""

    question: str = Field(description="The question to ask.")


class SubmitEvaluation(BaseModel):
    """Submit the evaluation of the user's answers and end the mock interview."""

    score: int = Field(description="The score of the user's answers (0-100).")
    feedback: str = Field(description="Constructive feedback for the user.")


async def init_node(
    state: MockInterviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Loads the job posting context for the mock interview."""
    db = config.get("configurable", {}).get("db") if config else None
    if not db:
        raise ValueError("Database session 'db' must be provided in config.")

    app_id = state.get("application_id")
    if not app_id:
        return {
            "job_context": "General software engineering role.",
            "required_skills": [],
        }

    stmt = (
        select(ApplicationModel)
        .options(joinedload(ApplicationModel.job_posting))
        .where(ApplicationModel.id == app_id)
    )
    res = await db.execute(stmt)
    app = res.scalar_one_or_none()

    if not app or not app.job_posting:
        return {
            "job_context": "General software engineering role.",
            "required_skills": [],
        }

    context = f"Company: {app.company.name if app.company else 'Unknown'}\nPosition: {app.position}\n"
    if app.job_posting.description_markdown:
        context += f"Description: {app.job_posting.description_markdown[:1500]}\n"

    return {
        "job_context": context,
        "required_skills": app.job_posting.required_skills or [],
    }


async def generator_node(
    state: MockInterviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Generates the next question or submits evaluation based on the interview type."""
    db = config.get("configurable", {}).get("db") if config else None
    if not db:
        raise ValueError("Database session 'db' must be provided in config.")

    llm = await get_task_chat_model(db, task_type="AGENT_REASONING")

    interview_type = state.get("interview_type", "Rapid Technical Screen")
    if interview_type == "Rapid Technical Screen":
        tools = [PresentMultipleChoiceQuestion, SubmitEvaluation]
    else:
        tools = [PresentOpenEndedQuestion, SubmitEvaluation]

    model_with_tools = llm.bind_tools(tools)

    system_prompt = (
        "You are a strict technical hiring manager conducting a {interview_type} mock interview.\n"
        "Here is the context of the job the candidate is interviewing for:\n{job_context}\n"
        "Your job is to either ask a relevant question using the provided tools, or if enough questions have been asked (at least 2), submit the final evaluation.\n"
        "Do not ask generic questions; tailor them specifically to the required skills."
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("placeholder", "{messages}")]
    )

    chain = prompt | model_with_tools
    response = await chain.ainvoke(
        {
            "interview_type": interview_type,
            "job_context": state.get("job_context", ""),
            "messages": state["messages"],
        }
    )

    return {"messages": [response]}


class QuestionReview(BaseModel):
    is_approved: bool = Field(
        description="True if the question is good and accurate, False otherwise."
    )
    feedback: str = Field(description="Feedback on why the question was rejected.")


async def reviewer_node(
    state: MockInterviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Reviews the generated question for accuracy and distractors."""
    db = config.get("configurable", {}).get("db") if config else None
    if not db:
        raise ValueError("Database session 'db' must be provided in config.")

    messages = state["messages"]
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {}  # Should not happen if generator is constrained to tools

    tool_call = last_message.tool_calls[0]

    if tool_call["name"] == "SubmitEvaluation":
        return {}  # Don't review evaluations

    llm = await get_task_chat_model(db, task_type="AGENT_REASONING")
    structured_llm = llm.with_structured_output(QuestionReview)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a technical reviewer evaluating a proposed interview question.\n"
                    "Review the question for accuracy, appropriate difficulty, and lack of obvious distractors.\n"
                    "If the question is factually incorrect, has obvious distractors (for multiple choice), or is too easy, reject it.\n"
                    "Context: {job_context}\n"
                ),
            ),
            ("human", "Question details: {tool_call}"),
        ]
    )

    chain = prompt | structured_llm
    review: QuestionReview = await chain.ainvoke(
        {
            "job_context": state.get("job_context", ""),
            "tool_call": json.dumps(tool_call["args"]),
        }
    )

    if review.is_approved:
        return {}

    logger.info(f"Question rejected by reviewer: {review.feedback}")

    # Route back to generator with feedback
    rejection_msg = ToolMessage(
        content=f"Your question was rejected by the reviewer: {review.feedback}. Please generate a new, better question.",
        tool_call_id=tool_call["id"],
    )
    return {"messages": [rejection_msg]}


def route_after_reviewer(state: MockInterviewState) -> str:
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # It was approved (reviewer returned {})
        if last_message.tool_calls[0]["name"] == "SubmitEvaluation":
            return END
        return END
    else:
        # Rejection ToolMessage was appended by reviewer
        return "generator"


def entry_router(state: MockInterviewState) -> str:
    messages = state["messages"]
    if len(messages) < 2:
        return "generator"

    last_message = messages[-1]
    prev_message = messages[-2]

    if (
        getattr(last_message, "type", "") == "human"
        and getattr(prev_message, "type", "") == "ai"
        and hasattr(prev_message, "tool_calls")
        and prev_message.tool_calls
    ):
        tc = prev_message.tool_calls[0]
        if tc["name"] in ("PresentMultipleChoiceQuestion", "PresentOpenEndedQuestion"):
            return "evaluator"

    return "generator"


def route_after_generator(state: MockInterviewState) -> str:
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        if last_message.tool_calls[0]["name"] == "SubmitEvaluation":
            return END
        return "reviewer"
    return "reviewer"  # Fallback


class AnswerEvaluation(BaseModel):
    is_correct: bool = Field(description="Whether the answer is correct or acceptable.")
    score: int = Field(description="Score for this specific answer (0-100).")
    feedback: str = Field(
        description="Constructive feedback for the user on this answer."
    )


async def evaluator_node(
    state: MockInterviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Evaluates the user's answer and appends it to evaluations state."""
    db = config.get("configurable", {}).get("db") if config else None
    if not db:
        raise ValueError("Database session 'db' must be provided in config.")

    messages = state["messages"]
    if len(messages) < 2:
        return {}

    last_message = messages[-1]
    if last_message.type != "human":
        # We only evaluate human responses
        return {}

    previous_message = messages[-2]
    if not hasattr(previous_message, "tool_calls") or not previous_message.tool_calls:
        return {}

    tool_call = previous_message.tool_calls[0]
    question_details = tool_call["args"]
    user_answer = last_message.content

    llm = await get_task_chat_model(db, task_type="AGENT_REASONING")
    structured_llm = llm.with_structured_output(AnswerEvaluation)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a strict technical evaluator. Grade the user's answer to the following question.\n"
                    "Grade strictly against the required skills: {required_skills}\n"
                    "Question details: {question_details}\n"
                ),
            ),
            ("human", "User answer: {answer}"),
        ]
    )

    chain = prompt | structured_llm
    evaluation: AnswerEvaluation = await chain.ainvoke(
        {
            "required_skills": ", ".join(state.get("required_skills", [])),
            "question_details": json.dumps(question_details),
            "answer": user_answer,
        }
    )

    evaluations = list(state.get("evaluations", []))
    eval_dict = evaluation.dict()
    eval_dict["question"] = question_details.get("question", "Unknown question")
    eval_dict["answer"] = user_answer
    evaluations.append(eval_dict)

    from langchain_core.messages import ToolMessage

    # We must satisfy the LLM API requirement by transforming the user's human answer
    # into the formal ToolMessage response to the tool_call.
    # The generator node will read this tool message which includes the user's answer + evaluation.
    eval_msg = ToolMessage(
        content=f"Candidate Answer: {user_answer}\n\nEvaluation Score: {evaluation.score}. Feedback: {evaluation.feedback}",
        tool_call_id=tool_call["id"],
    )

    return {
        "evaluations": evaluations,
        "messages": [RemoveMessage(id=last_message.id), eval_msg],
    }


def build_mock_interview_graph():
    """Builds and compiles the LangGraph state machine for Mock Interviews."""
    workflow = StateGraph(MockInterviewState)

    workflow.add_node("init", init_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("evaluator", evaluator_node)

    workflow.add_edge(START, "init")
    workflow.add_conditional_edges(
        "init", entry_router, {"evaluator": "evaluator", "generator": "generator"}
    )

    workflow.add_conditional_edges(
        "generator",
        route_after_generator,
        {"reviewer": "reviewer", END: END},
    )

    workflow.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {"generator": "generator", END: END},
    )

    # After evaluator runs, it's the generator's turn again
    workflow.add_edge("evaluator", "generator")

    return workflow.compile(checkpointer=postgres_saver)


mock_interview_graph = build_mock_interview_graph()
