import asyncio
import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.models.agent_chat import AgentChatModel
from app.services.agent_tools import create_agent_tools
from app.services.postgres_tracer import PostgresTracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent Chat Assistant"])


def sanitize_mock_question_reply(content: str, actions: list[dict[str, Any]]) -> str:
    """
    Backend Safety Guardrail:
    1. If a mock question was generated, strips accidentally duplicated inline options
       (e.g., A) ..., B) ..., 1. ...) from the assistant text content.
    2. If evaluating an answer (i.e. generate_mock_interview_question was NOT called in this turn),
       strips any accidental trailing follow-up/next question lines or transition headers.
    """
    if not content:
        return content

    has_mock_question = any(
        act.get("action") == "generate_mock_interview_question" for act in (actions or [])
    )

    if has_mock_question:
        # Strip option lines
        lines = content.split("\n")
        cleaned_lines = []
        option_line_pattern = re.compile(
            r"^\s*([A-Da-d1-4])[\.\)\:]\s+.*", re.IGNORECASE
        )
        for line in lines:
            if option_line_pattern.match(line):
                continue
            cleaned_lines.append(line)
        cleaned = "\n".join(cleaned_lines).strip()
        return cleaned if cleaned else content
    else:
        # Truncation fallback when evaluating an answer:
        # If the text contains accidental trailing question sections like 'Next question:',
        # 'Follow-up question:', 'Ready for the next question?', or trailing lines ending with '?', strip them.
        trailing_question_headers = re.compile(
            r"(?i)\n+\s*(next question|follow-?up question|ready for the next question|question \d+)[\:\?].*",
            re.DOTALL,
        )
        cleaned_content = trailing_question_headers.sub("", content).strip()

        # If a trailing sentence ends with '?' at the very end of feedback, strip that trailing question
        lines = [line for line in cleaned_content.split("\n") if line.strip()]
        if lines:
            last_line = lines[-1].strip()
            if last_line.endswith("?") and ("question" in last_line.lower() or "what" in last_line.lower() or "how" in last_line.lower() or "can you" in last_line.lower()):
                lines.pop()
                cleaned_content = "\n".join(lines).strip()

        return cleaned_content if cleaned_content else content


def prune_and_sanitize_tool_output(content: Any, max_array_length: int = 5) -> str:
    """
    Sanitizes and prunes tool execution output payloads:
    - Parses string payloads as JSON where applicable.
    - Strips redundant metadata fields (e.g., 'metadata', 'raw_response').
    - Bounds array lengths to at most `max_array_length` items.
    - Returns a compact JSON string representation (separators=(',', ':')).
    """
    if content is None:
        return ""

    parsed = content
    if isinstance(content, str):
        trimmed = content.strip()
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (
            trimmed.startswith("[") and trimmed.endswith("]")
        ):
            try:
                parsed = json.loads(trimmed)
            except Exception:
                parsed = content
        else:
            return content

    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            new_dict = {}
            for k, v in obj.items():
                if k in ("metadata", "raw_response"):
                    continue
                new_dict[k] = _sanitize(v)
            return new_dict
        elif isinstance(obj, list):
            trimmed_list = obj[:max_array_length]
            return [_sanitize(item) for item in trimmed_list]
        return obj

    sanitized = _sanitize(parsed)
    if isinstance(sanitized, (dict, list)):
        return json.dumps(sanitized, separators=(",", ":"))
    return str(sanitized)


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text")


class AgentChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    chat_id: int | None = None


class AgentChatResponse(BaseModel):
    chat_id: int
    reply: str
    actions_performed: list[dict[str, Any]] = Field(default_factory=list)


class AgentChatRead(BaseModel):
    id: int
    title: str
    messages: list[dict[str, Any]]
    created_at: Any
    updated_at: Any


@router.get("/chats", response_model=list[AgentChatRead])
async def list_chats(db: AsyncSession = Depends(get_db)):
    stmt = select(AgentChatModel).order_by(desc(AgentChatModel.updated_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/chats/{chat_id}", response_model=AgentChatRead)
async def get_chat(chat_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(AgentChatModel).where(AgentChatModel.id == chat_id)
    res = await db.execute(stmt)
    chat = res.scalar_one_or_none()
    if not chat:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: int, db: AsyncSession = Depends(get_db)):
    stmt = delete(AgentChatModel).where(AgentChatModel.id == chat_id)
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}


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
        logger.warning(
            "Native tool binding not available, using raw model: %s", bind_err
        )
        model_with_tools = chat_model

    last_user_msg = payload.messages[-1].content.strip()
    actions_performed: list[dict[str, Any]] = []

    # Assemble conversation history
    messages: list[Any] = [SystemMessage(content=system_prompt)]

    chat_record = None
    if payload.chat_id:
        stmt = select(AgentChatModel).where(AgentChatModel.id == payload.chat_id)
        res = await db.execute(stmt)
        chat_record = res.scalar_one_or_none()

    if chat_record:
        # Load from DB history
        for m_data in chat_record.messages:
            if m_data.get("role") == "user":
                messages.append(HumanMessage(content=m_data.get("content", "")))
            elif m_data.get("role") == "assistant":
                messages.append(AIMessage(content=m_data.get("content", "")))
            elif m_data.get("role") == "tool":
                sanitized_content = prune_and_sanitize_tool_output(
                    m_data.get("content", "")
                )
                messages.append(
                    ToolMessage(
                        content=sanitized_content,
                        tool_call_id=m_data.get("tool_call_id", ""),
                    )
                )
    else:
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
            response = await model_with_tools.ainvoke(
                messages,
                config={"callbacks": [PostgresTracer()]},
            )
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                reply_content = (
                    response.content
                    if isinstance(response.content, str)
                    else str(response.content)
                )
                break

            async def execute_tool(
                tc: Any, current_turn: int = turn
            ) -> tuple[str, str, dict[str, Any] | None]:
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
                    tc.get("id", f"call_{current_turn}")
                    if isinstance(tc, dict)
                    else getattr(tc, "id", f"call_{current_turn}")
                )

                selected_tool = tool_map.get(tool_name)
                if selected_tool:
                    try:
                        tool_result = await selected_tool.ainvoke(
                            tool_args,
                            config={"callbacks": [PostgresTracer()]},
                        )
                        parsed_res = tool_result
                        if isinstance(tool_result, str) and (
                            tool_result.strip().startswith("{")
                            or tool_result.strip().startswith("[")
                        ):
                            try:
                                parsed_res = json.loads(tool_result)
                            except Exception:
                                parsed_res = tool_result

                        action_data = {
                            "action": tool_name,
                            "args": tool_args,
                            "result": parsed_res,
                        }
                        return tool_id, str(tool_result), action_data
                    except Exception as err:
                        logger.error("Error executing tool %s: %s", tool_name, err)
                        tool_result = json.dumps({"error": str(err)})
                        return tool_id, tool_result, None
                else:
                    tool_result = json.dumps(
                        {"error": f"Tool '{tool_name}' not available."}
                    )
                    return tool_id, tool_result, None

            tool_results = await asyncio.gather(
                *(execute_tool(tc) for tc in tool_calls),
                return_exceptions=True,
            )

            for res in tool_results:
                if isinstance(res, Exception):
                    logger.error("Error during parallel tool execution: %s", res)
                    continue
                tool_id, tool_result_str, action_data = res
                if action_data:
                    actions_performed.append(action_data)

                sanitized_res = prune_and_sanitize_tool_output(tool_result_str)
                messages.append(
                    ToolMessage(content=sanitized_res, tool_call_id=tool_id)
                )

        except Exception as err:
            logger.error("Agent chat generation error on turn %d: %s", turn, err)
            reply_content = f"I encountered an issue processing your request: {err}"
            break

    if not reply_content and messages:
        last_msg = messages[-1]
        reply_content = getattr(last_msg, "content", "Processing completed.")

    # Apply backend safety guardrail sanitization if mock question was generated
    reply_content = sanitize_mock_question_reply(str(reply_content), actions_performed)

    # Save to DB
    db_messages = []
    for m in messages[1:]:  # Skip system prompt
        if isinstance(m, HumanMessage):
            db_messages.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            msg_dict: dict[str, Any] = {"role": "assistant", "content": m.content}
            if actions_performed:
                msg_dict["actions"] = actions_performed
            db_messages.append(msg_dict)
        elif isinstance(m, ToolMessage):
            db_messages.append(
                {"role": "tool", "content": m.content, "tool_call_id": m.tool_call_id}
            )

    if not chat_record:
        # Create new
        title_text = (
            last_user_msg[:30] + "..." if len(last_user_msg) > 30 else last_user_msg
        )
        chat_record = AgentChatModel(title=title_text, messages=db_messages)
        db.add(chat_record)
        await db.commit()
        await db.refresh(chat_record)
    else:
        chat_record.messages = db_messages
        db.add(chat_record)
        await db.commit()

    return AgentChatResponse(
        chat_id=chat_record.id,
        reply=str(reply_content).strip(),
        actions_performed=actions_performed,
    )
