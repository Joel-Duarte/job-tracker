import json
import logging
from typing import Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.services.agent_tools import create_agent_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent Chat Assistant"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text")


class AgentChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1)


class AgentChatResponse(BaseModel):
    reply: str
    actions_performed: List[dict[str, Any]] = Field(default_factory=list)


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentChatResponse:
    """
    Conversational Agent Chat equipped with native semantic vector search and database query/mutation tools.
    """
    system_prompt = await get_prompt_template(db, "agent_system")
    chat_model = await get_task_chat_model(db, task_type="AGENT_REASONING")

    tools = create_agent_tools(db)
    tool_map = {t.name: t for t in tools}

    try:
        model_with_tools = chat_model.bind_tools(tools)
    except Exception as bind_err:
        logger.warning("Native tool binding not available, using raw model: %s", bind_err)
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
                reply_content = response.content if isinstance(response.content, str) else str(response.content)
                break

            for tc in tool_calls:
                tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                tool_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
                tool_id = tc.get("id", f"call_{turn}") if isinstance(tc, dict) else getattr(tc, "id", f"call_{turn}")

                selected_tool = tool_map.get(tool_name)
                if selected_tool:
                    try:
                        tool_result = await selected_tool.ainvoke(tool_args)
                        parsed_res = tool_result
                        if isinstance(tool_result, str) and (tool_result.strip().startswith("{") or tool_result.strip().startswith("[")):
                            try:
                                parsed_res = json.loads(tool_result)
                            except Exception:
                                parsed_res = tool_result

                        actions_performed.append({
                            "action": tool_name,
                            "args": tool_args,
                            "result": parsed_res,
                        })
                    except Exception as err:
                        logger.error("Error executing tool %s: %s", tool_name, err)
                        tool_result = json.dumps({"error": str(err)})
                else:
                    tool_result = json.dumps({"error": f"Tool '{tool_name}' not available."})

                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

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
