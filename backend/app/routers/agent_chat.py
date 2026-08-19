import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
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
    """Stream agent response tokens as server-sent events."""
    system_prompt = await get_prompt_template(db, "agent_system")
    chat_model = await get_task_chat_model(db, task_type="AGENT_REASONING")
    tools = create_agent_tools(db)

    try:
        model_with_tools = chat_model.bind_tools(tools)
    except Exception as bind_err:
        logger.warning("Native tool binding not available: %s", bind_err)
        model_with_tools = chat_model

    messages: list[Any] = [SystemMessage(content=system_prompt)]
    for message in payload.messages:
        if message.role == "user":
            messages.append(HumanMessage(content=message.content))
        elif message.role == "assistant":
            messages.append(AIMessage(content=message.content))

    async def event_generator():
        content_parts: list[str] = []
        try:
            async for chunk in model_with_tools.astream(
                messages,
                config={"callbacks": [PostgresTracer()]},
            ):
                content = (
                    chunk.content
                    if isinstance(chunk.content, str)
                    else str(chunk.content)
                )
                if content:
                    content_parts.append(content)
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
        except Exception as err:
            logger.error("Agent chat streaming error: %s", err)
            yield f"data: {json.dumps({'type': 'error', 'message': str(err)})}\n\n"
            return

        chat_record = AgentChatModel(
            title=payload.messages[-1].content[:30],
            messages=[
                {"role": "user", "content": payload.messages[-1].content},
                {"role": "assistant", "content": "".join(content_parts)},
            ],
        )
        db.add(chat_record)
        await db.commit()
        await db.refresh(chat_record)
        yield f"data: {json.dumps({'type': 'done', 'chat_id': chat_record.id, 'reply': ''.join(content_parts), 'actions_performed': []})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
