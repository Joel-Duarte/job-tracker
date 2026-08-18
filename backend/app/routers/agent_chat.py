import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.services.agent_tools import create_agent_tools
from app.services.mock_interview_graph import mock_interview_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent Chat Assistant"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text")


class AgentChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    interview_type: str | None = Field(
        default=None, description="E.g., 'Rapid Technical Screen' or 'Deep Dive'"
    )
    application_id: int | None = Field(
        default=None, description="Application ID context for mock interviews"
    )
    thread_id: str | None = Field(
        default=None,
        description="Unique conversation thread ID for LangGraph checkpointing",
    )


class AgentChatResponse(BaseModel):
    reply: str
    actions_performed: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    """
    Conversational Agent Chat equipped with native semantic vector search and database query/mutation tools.
    """
    if payload.interview_type:
        thread_id = payload.thread_id or "default_thread"
        config = {"configurable": {"thread_id": thread_id, "db": db}}

        last_user_msg = payload.messages[-1].content.strip()
        state_input = {
            "messages": [HumanMessage(content=last_user_msg)],
            "interview_type": payload.interview_type,
            "application_id": payload.application_id,
        }

        reply_content = ""
        actions_performed = []

        try:
            async for s in mock_interview_graph.astream(
                state_input, config, stream_mode="values"
            ):
                if "messages" in s and s["messages"]:
                    last_msg = s["messages"][-1]
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        tc = last_msg.tool_calls[0]
                        if tc["name"] in (
                            "PresentMultipleChoiceQuestion",
                            "PresentOpenEndedQuestion",
                        ):
                            reply_content = tc["args"].get("question", "")
                            actions_performed.append(
                                {"action": tc["name"], "args": tc["args"]}
                            )
                        elif tc["name"] == "SubmitEvaluation":
                            score = tc["args"].get("score", 0)
                            feedback = tc["args"].get("feedback", "")
                            reply_content = f"Interview Complete!\nScore: {score}/100\n\nFeedback: {feedback}"
                            actions_performed.append(
                                {"action": tc["name"], "args": tc["args"]}
                            )

            return AgentChatResponse(
                reply=reply_content,
                actions_performed=actions_performed,
            )
        except Exception as err:
            logger.error("Mock interview error: %s", err, exc_info=True)
            return AgentChatResponse(
                reply=f"I encountered an issue running the mock interview: {err}",
                actions_performed=[],
            )

    system_prompt = await get_prompt_template(db, "agent_system")
    chat_model = await get_task_chat_model(db, task_type="AGENT_REASONING")

    tools = create_agent_tools(db)
    tool_map = {t.name: t for t in tools}

    try:
        model_with_tools = chat_model.bind_tools(tools)
    except Exception as bind_err:
        logger.warning(
            "Native tool binding not available, using raw model: %s", bind_err
        )
        model_with_tools = chat_model

    last_user_msg = payload.messages[-1].content.strip()
    actions_performed: list[dict[str, Any]] = []

    # Assemble conversation history
    messages: list[Any] = [SystemMessage(content=system_prompt)]
    for m in payload.messages[:-1]:
        if m.role == "user":
            messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            messages.append(AIMessage(content=m.content))

    messages.append(HumanMessage(content=last_user_msg))

    reply_content = ""
    max_turns = 4

    for turn in range(max_turns):
        try:
            response = await model_with_tools.ainvoke(messages)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                reply_content = (
                    response.content
                    if isinstance(response.content, str)
                    else str(response.content)
                )
                break

            for tc in tool_calls:
                tool_name = (
                    tc.get("name")
                    if isinstance(tc, dict)
                    else getattr(tc, "name", None)
                )
                tool_args = (
                    tc.get("args", {})
                    if isinstance(tc, dict)
                    else getattr(tc, "args", {})
                )
                tool_id = (
                    tc.get("id", f"call_{turn}")
                    if isinstance(tc, dict)
                    else getattr(tc, "id", f"call_{turn}")
                )

                selected_tool = tool_map.get(tool_name)
                if selected_tool:
                    try:
                        tool_result = await selected_tool.ainvoke(tool_args)
                        parsed_res = tool_result
                        if isinstance(tool_result, str) and (
                            tool_result.strip().startswith("{")
                            or tool_result.strip().startswith("[")
                        ):
                            try:
                                parsed_res = json.loads(tool_result)
                            except Exception:
                                parsed_res = tool_result

                        actions_performed.append(
                            {
                                "action": tool_name,
                                "args": tool_args,
                                "result": parsed_res,
                            }
                        )
                    except Exception as err:
                        logger.error("Error executing tool %s: %s", tool_name, err)
                        tool_result = json.dumps({"error": str(err)})
                else:
                    tool_result = json.dumps(
                        {"error": f"Tool '{tool_name}' not available."}
                    )

                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_id)
                )

        except Exception as err:
            logger.error("Agent chat generation error on turn %d: %s", turn, err)
            reply_content = f"I encountered an issue processing your request: {err}"
            break

    if not reply_content and messages:
        last_msg = messages[-1]
        reply_content = getattr(last_msg, "content", "Processing completed.")

    return AgentChatResponse(
        reply=str(reply_content).strip(),
        actions_performed=actions_performed,
    )
