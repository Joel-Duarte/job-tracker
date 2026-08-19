import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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


def prune_and_sanitize_tool_output(tool_result: Any, max_array_len: int = 5) -> str:
    """
    Sanitizes and prunes tool outputs before appending ToolMessage to context history:
    - Strips redundant vector metadata (e.g. 'metadata' dict keys)
    - Limits array length returns to prevent exponential token growth
    - Serializes using compact JSON formatting
    """
    if isinstance(tool_result, str):
        cleaned_str = tool_result.strip()
        if (cleaned_str.startswith("{") and cleaned_str.endswith("}")) or (
            cleaned_str.startswith("[") and cleaned_str.endswith("]")
        ):
            try:
                data = json.loads(cleaned_str)
            except Exception:
                return tool_result
        else:
            return tool_result
    else:
        data = tool_result

    def _prune(obj: Any) -> Any:
        if isinstance(obj, dict):
            pruned_dict = {}
            for k, v in obj.items():
                if k == "metadata":
                    continue
                pruned_dict[k] = _prune(v)
            return pruned_dict
        elif isinstance(obj, list):
            bounded_list = obj[:max_array_len]
            return [_prune(item) for item in bounded_list]
        return obj

    pruned_data = _prune(data)
    try:
        return json.dumps(pruned_data, separators=(",", ":"))
    except Exception:
        return str(pruned_data)


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
                messages.append(
                    ToolMessage(
                        content=m_data.get("content", ""),
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
                        tool_result = await selected_tool.ainvoke(
                            tool_args,
                            config={"callbacks": [PostgresTracer()]},
                        )
                    except Exception as err:
                        logger.error("Error executing tool %s: %s", tool_name, err)
                        tool_result = json.dumps({"error": str(err)})
                else:
                    tool_result = json.dumps(
                        {"error": f"Tool '{tool_name}' not available."}
                    )

                pruned_str = prune_and_sanitize_tool_output(tool_result)
                try:
                    parsed_res = json.loads(pruned_str)
                except Exception:
                    parsed_res = pruned_str

                actions_performed.append(
                    {
                        "action": tool_name,
                        "args": tool_args,
                        "result": parsed_res,
                    }
                )

                messages.append(ToolMessage(content=pruned_str, tool_call_id=tool_id))

        except Exception as err:
            logger.error("Agent chat generation error on turn %d: %s", turn, err)
            reply_content = f"I encountered an issue processing your request: {err}"
            break

    if not reply_content and messages:
        last_msg = messages[-1]
        reply_content = getattr(last_msg, "content", "Processing completed.")

    # Save to DB
    db_messages = []
    for m in messages[1:]:  # Skip system prompt
        if isinstance(m, HumanMessage):
            db_messages.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            db_messages.append({"role": "assistant", "content": m.content})
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


@router.post("/chat/stream")
async def chat_with_agent_stream(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Streaming Conversational Agent Chat endpoint returning Server-Sent Events (SSE).
    Streams model response tokens and tool execution notifications in real time.
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

    # Assemble conversation history
    messages: list[Any] = [SystemMessage(content=system_prompt)]

    chat_record = None
    if payload.chat_id:
        stmt = select(AgentChatModel).where(AgentChatModel.id == payload.chat_id)
        res = await db.execute(stmt)
        chat_record = res.scalar_one_or_none()

    if chat_record:
        for m_data in chat_record.messages:
            if m_data.get("role") == "user":
                messages.append(HumanMessage(content=m_data.get("content", "")))
            elif m_data.get("role") == "assistant":
                messages.append(AIMessage(content=m_data.get("content", "")))
            elif m_data.get("role") == "tool":
                messages.append(
                    ToolMessage(
                        content=m_data.get("content", ""),
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

    async def event_generator():
        nonlocal chat_record
        actions_performed: list[dict[str, Any]] = []
        reply_content = ""
        max_turns = 4

        for turn in range(max_turns):
            try:
                accumulated_response = None
                async for chunk in model_with_tools.astream(
                    messages,
                    config={"callbacks": [PostgresTracer()]},
                ):
                    if accumulated_response is None:
                        accumulated_response = chunk
                    else:
                        accumulated_response = accumulated_response + chunk

                    content_delta = (
                        chunk.content
                        if isinstance(chunk.content, str)
                        else str(chunk.content)
                    )
                    if content_delta:
                        yield f"data: {json.dumps({'type': 'token', 'content': content_delta})}\n\n"

                if accumulated_response is None:
                    response = AIMessage(content="")
                else:
                    response = accumulated_response

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

                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name, 'args': tool_args})}\n\n"

                    selected_tool = tool_map.get(tool_name)
                    if selected_tool:
                        try:
                            tool_result = await selected_tool.ainvoke(
                                tool_args,
                                config={"callbacks": [PostgresTracer()]},
                            )
                        except Exception as err:
                            logger.error("Error executing tool %s: %s", tool_name, err)
                            tool_result = json.dumps({"error": str(err)})
                    else:
                        tool_result = json.dumps(
                            {"error": f"Tool '{tool_name}' not available."}
                        )

                    pruned_str = prune_and_sanitize_tool_output(tool_result)
                    try:
                        parsed_res = json.loads(pruned_str)
                    except Exception:
                        parsed_res = pruned_str

                    actions_performed.append(
                        {
                            "action": tool_name,
                            "args": tool_args,
                            "result": parsed_res,
                        }
                    )

                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': tool_name, 'result': parsed_res})}\n\n"

                    messages.append(
                        ToolMessage(content=pruned_str, tool_call_id=tool_id)
                    )

            except Exception as err:
                logger.error("Agent chat streaming error on turn %d: %s", turn, err)
                reply_content = f"I encountered an issue processing your request: {err}"
                yield f"data: {json.dumps({'type': 'error', 'message': str(err)})}\n\n"
                break

        if not reply_content and messages:
            last_msg = messages[-1]
            reply_content = getattr(last_msg, "content", "Processing completed.")

        # Save conversation to DB
        db_messages = []
        for m in messages[1:]:  # Skip system prompt
            if isinstance(m, HumanMessage):
                db_messages.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage):
                db_messages.append({"role": "assistant", "content": m.content})
            elif isinstance(m, ToolMessage):
                db_messages.append(
                    {
                        "role": "tool",
                        "content": m.content,
                        "tool_call_id": m.tool_call_id,
                    }
                )

        if not chat_record:
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

        yield f"data: {json.dumps({'type': 'done', 'chat_id': chat_record.id, 'reply': str(reply_content).strip(), 'actions_performed': actions_performed})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
