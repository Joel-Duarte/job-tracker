import json
import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.models.applications import ActionItemModel, ApplicationModel, CompanyModel
from app.services.llm import generate_embedding

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
    Conversational Agent Chat equipped with semantic vector search and database query/mutation tools.
    """
    system_prompt = await get_prompt_template(db, "agent_system")
    chat_model = await get_task_chat_model(db, task_type="AGENT_REASONING")

    # 1. Inspect user's last message for intents / context
    last_user_msg = payload.messages[-1].content.strip()
    actions_performed: list[dict[str, Any]] = []

    # Prepare context probe
    context_notes = []

    # Check if query warrants semantic vector search
    try:
        query_vector = await generate_embedding(db, last_user_msg)
        from app.models.applications import ApplicationEmbeddingModel

        distance_expr = ApplicationEmbeddingModel.embedding.cosine_distance(query_vector).label("distance")
        stmt = (
            select(ApplicationEmbeddingModel, distance_expr)
            .join(ApplicationModel, ApplicationEmbeddingModel.email_application_id == ApplicationModel.id)
            .options(selectinload(ApplicationEmbeddingModel.application).selectinload(ApplicationModel.company))
            .order_by(distance_expr.asc())
            .limit(4)
        )
        res = await db.execute(stmt)
        search_hits = res.all()

        if search_hits:
            context_notes.append("Relevant Application Matches from Database:")
            for emb, dist in search_hits:
                app_obj = emb.application
                comp_name = app_obj.company.name if app_obj and app_obj.company else "Unknown"
                sim_pct = max(0.0, min(100.0, (1.0 - float(dist)) * 100.0))
                context_notes.append(
                    f"- Company: {comp_name}, Role: {app_obj.position}, Status: {app_obj.status} (Match: {sim_pct:.1f}%)\n"
                    f"  Summary: {emb.content[:200]}..."
                )
    except Exception as err:
        logger.warning("Agent vector retrieval probe note: %s", err)

    # 2. Check for explicit update command in user message (e.g., "move Stripe to Offer", "set Figma status to Rejected")
    lower_msg = last_user_msg.lower()
    for status_key in ["applied", "assessment", "interview", "technical_interview", "offer", "rejected"]:
        if f"to {status_key}" in lower_msg or f"as {status_key}" in lower_msg:
            # Look for company name mentioned
            companies_res = await db.execute(select(CompanyModel))
            for comp in companies_res.scalars().all():
                if comp.name.lower() in lower_msg:
                    # Update application
                    app_stmt = select(ApplicationModel).where(ApplicationModel.company_id == comp.id)
                    target_app = (await db.execute(app_stmt)).scalar_one_or_none()
                    if target_app:
                        target_app.status = status_key.upper()
                        await db.commit()
                        actions_performed.append({
                            "action": "UPDATE_STATUS",
                            "company": comp.name,
                            "new_status": status_key.upper(),
                        })
                        context_notes.append(f"[SYSTEM ACTION EXECUTED]: Updated {comp.name} status to '{status_key.upper()}'.")

    # 3. Assemble prompt for LangChain chat model
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    langchain_msgs = [SystemMessage(content=system_prompt)]
    if context_notes:
        langchain_msgs.append(SystemMessage(content="\n".join(context_notes)))

    for m in payload.messages[:-1]:
        if m.role == "user":
            langchain_msgs.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            langchain_msgs.append(AIMessage(content=m.content))

    langchain_msgs.append(HumanMessage(content=last_user_msg))

    try:
        response = await chat_model.ainvoke(langchain_msgs)
        reply_content = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as err:
        logger.error("Agent chat generation error: %s", err)
        reply_content = f"I retrieved the relevant records from your pipeline:\n\n" + "\n".join(context_notes)

    return AgentChatResponse(
        reply=reply_content.strip(),
        actions_performed=actions_performed,
    )
