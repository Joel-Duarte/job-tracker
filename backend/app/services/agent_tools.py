import logging
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from langchain_core.tools import StructuredTool

from app.models.applications import (
    ApplicationModel,
    CompanyModel,
    ApplicationEventModel,
    ActionItemModel,
    ApplicationEmbeddingModel,
)
from app.services.llm import generate_embedding, generate_and_save_application_embedding

logger = logging.getLogger(__name__)


class SemanticSearchInput(BaseModel):
    query: str = Field(description="Semantic search query describing the company, role, email content, or recruiter communication.")
    limit: int = Field(default=5, ge=1, le=10, description="Max number of matching documents to return.")


class ListApplicationsInput(BaseModel):
    status: Optional[str] = Field(default=None, description="Filter by status: APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT.")
    action_required_only: bool = Field(default=False, description="If true, only returns applications with pending tasks or deadlines.")
    limit: int = Field(default=20, ge=1, le=50, description="Max records to return.")


class ApplicationDetailsInput(BaseModel):
    company_or_id: str = Field(description="Company name (e.g. 'Stripe') or numeric Application ID (e.g. '12').")


class UpdateStatusInput(BaseModel):
    company_name: str = Field(description="Name of the company whose application status to update.")
    new_status: str = Field(description="New status: APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, or ASSESSMENT.")
    notes: Optional[str] = Field(default=None, description="Optional explanation or reason for the status change.")


class ActionItemsInput(BaseModel):
    urgency: Optional[str] = Field(default=None, description="Optional urgency filter: HIGH, MEDIUM, or LOW.")


async def execute_semantic_vector_search(db: AsyncSession, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Performs semantic vector search across pgvector application embeddings."""
    query_vector = await generate_embedding(db, query)
    distance_expr = ApplicationEmbeddingModel.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(ApplicationEmbeddingModel, distance_expr)
        .join(ApplicationModel, ApplicationEmbeddingModel.email_application_id == ApplicationModel.id)
        .options(selectinload(ApplicationEmbeddingModel.application).selectinload(ApplicationModel.company))
        .order_by(distance_expr.asc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    hits = res.all()
    results = []
    for emb, dist in hits:
        app = emb.application
        comp_name = app.company.name if (app and app.company) else "Unknown"
        sim_pct = round(max(0.0, min(100.0, (1.0 - float(dist)) * 100.0)), 1)
        results.append({
            "application_id": app.id if app else None,
            "company": comp_name,
            "position": app.position if app else "Unknown",
            "status": app.status if app else "APPLIED",
            "similarity_score": f"{sim_pct}%",
            "document_content": emb.content,
            "metadata": emb.metadata_,
        })
    return results


async def execute_list_applications(
    db: AsyncSession,
    status: Optional[str] = None,
    action_required_only: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Lists applications directly from the database."""
    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.action_items),
        )
        .order_by(ApplicationModel.updated_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(ApplicationModel.status == status.upper())
    res = await db.execute(stmt)
    apps = res.scalars().all()
    out = []
    for a in apps:
        has_action = any(e.email_action_required for e in (a.events or [])) or any(i.status == "PENDING" for i in (a.action_items or []))
        if action_required_only and not has_action:
            continue
        out.append({
            "id": a.id,
            "company": a.company.name if a.company else "Unknown",
            "position": a.position,
            "status": a.status,
            "has_action_required": has_action,
            "application_date": a.application_date.isoformat() if a.application_date else None,
            "last_activity_at": a.last_activity_at.isoformat() if a.last_activity_at else None,
        })
    return out


async def execute_get_application_details(db: AsyncSession, company_or_id: str) -> dict[str, Any]:
    """Fetches complete timeline and event history for a specific application."""
    stmt = (
        select(ApplicationModel)
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.events),
            selectinload(ApplicationModel.job_posting),
            selectinload(ApplicationModel.action_items),
        )
    )
    if company_or_id.isdigit():
        stmt = stmt.where(ApplicationModel.id == int(company_or_id))
    else:
        stmt = stmt.join(CompanyModel).where(CompanyModel.name_normalized.ilike(f"%{company_or_id.strip().lower()}%"))

    res = await db.execute(stmt)
    app = res.scalars().first()
    if not app:
        return {"error": f"No application found matching '{company_or_id}'."}

    events_out = []
    for e in (app.events or []):
        events_out.append({
            "event_type": e.email_event_type,
            "subject": e.email_subject,
            "summary": e.email_summary,
            "received_at": e.email_received_at.isoformat() if e.email_received_at else None,
            "action_required": e.email_action_required,
            "action": e.email_action,
        })

    actions_out = []
    for a in (app.action_items or []):
        actions_out.append({
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "urgency": a.urgency,
        })

    return {
        "id": app.id,
        "company": app.company.name if app.company else "Unknown",
        "position": app.position,
        "status": app.status,
        "job_url": app.job_url,
        "events": events_out,
        "action_items": actions_out,
    }


async def execute_update_application_status(
    db: AsyncSession,
    company_name: str,
    new_status: str,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Updates an application status in the database and updates vector embeddings."""
    valid_statuses = ["APPLIED", "TECHNICAL_INTERVIEW", "OFFER", "REJECTED", "ASSESSMENT"]
    status_norm = new_status.upper()
    if status_norm not in valid_statuses:
        return {"error": f"Invalid status '{new_status}'. Allowed: {valid_statuses}"}

    comp_stmt = select(CompanyModel).where(CompanyModel.name_normalized.ilike(f"%{company_name.strip().lower()}%"))
    comp_res = await db.execute(comp_stmt)
    comp = comp_res.scalars().first()
    if not comp:
        return {"error": f"Company '{company_name}' not found in database."}

    app_stmt = select(ApplicationModel).where(ApplicationModel.company_id == comp.id)
    app_res = await db.execute(app_stmt)
    app = app_res.scalars().first()
    if not app:
        return {"error": f"No application found for company '{company_name}'."}

    old_status = app.status
    app.status = status_norm

    event = ApplicationEventModel(
        email_application_id=app.id,
        email_event_type="STATUS_CHANGE",
        email_status_after_event=status_norm,
        email_summary=notes or f"Status transitioned from {old_status} to {status_norm} via AI Agent assistant.",
        source_channel="AGENT",
    )
    db.add(event)
    await db.commit()
    await db.refresh(app)

    # Update vector embeddings
    if status_norm != "ASSESSMENT":
        try:
            await generate_and_save_application_embedding(db, app.id, skip_llm_summary=True)
        except Exception as err:
            logger.warning("Embedding update deferred: %s", err)

    return {
        "success": True,
        "application_id": app.id,
        "company": comp.name,
        "old_status": old_status,
        "new_status": status_norm,
        "message": f"Successfully transitioned {comp.name} application from {old_status} to {status_norm}.",
    }


async def execute_get_action_items(db: AsyncSession, urgency: Optional[str] = None) -> list[dict[str, Any]]:
    """Fetches pending action items and deadlines."""
    stmt = (
        select(ActionItemModel)
        .options(joinedload(ActionItemModel.application).joinedload(ApplicationModel.company))
        .where(ActionItemModel.status == "PENDING")
    )
    if urgency:
        stmt = stmt.where(ActionItemModel.urgency == urgency.upper())
    stmt = stmt.order_by(ActionItemModel.due_date.asc().nulls_last())
    res = await db.execute(stmt)
    items = res.scalars().all()
    out = []
    for item in items:
        comp_name = item.application.company.name if (item.application and item.application.company) else "General"
        out.append({
            "id": item.id,
            "company": comp_name,
            "title": item.title,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "urgency": item.urgency,
            "status": item.status,
        })
    return out


def create_agent_tools(db: AsyncSession) -> list[StructuredTool]:
    """Factory creating bound LangChain tools for the active async database session."""
    
    async def _vector_search(query: str, limit: int = 5) -> str:
        res = await execute_semantic_vector_search(db, query, limit)
        return json.dumps(res, indent=2)

    async def _list_apps(status: Optional[str] = None, action_required_only: bool = False, limit: int = 20) -> str:
        res = await execute_list_applications(db, status, action_required_only, limit)
        return json.dumps(res, indent=2)

    async def _app_details(company_or_id: str) -> str:
        res = await execute_get_application_details(db, company_or_id)
        return json.dumps(res, indent=2)

    async def _update_status(company_name: str, new_status: str, notes: Optional[str] = None) -> str:
        res = await execute_update_application_status(db, company_name, new_status, notes)
        return json.dumps(res, indent=2)

    async def _action_items(urgency: Optional[str] = None) -> str:
        res = await execute_get_action_items(db, urgency)
        return json.dumps(res, indent=2)

    return [
        StructuredTool.from_function(
            coroutine=_vector_search,
            name="semantic_vector_search",
            description="Searches the vector database for relevant job applications, recruiter emails, and timeline updates using semantic cosine similarity. Use this tool FIRST for queries asking about company progress, status updates, or communication history.",
            args_schema=SemanticSearchInput,
        ),
        StructuredTool.from_function(
            coroutine=_list_apps,
            name="list_applications",
            description="Lists applications directly from the database with optional status filtering (e.g. APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT) or action required filtering.",
            args_schema=ListApplicationsInput,
        ),
        StructuredTool.from_function(
            coroutine=_app_details,
            name="get_application_details",
            description="Retrieves the detailed chronological event timeline, recruiter emails, and action items for a specific company or application ID.",
            args_schema=ApplicationDetailsInput,
        ),
        StructuredTool.from_function(
            coroutine=_update_status,
            name="update_application_status",
            description="Updates an application's pipeline status in the database (e.g. transitions to APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT) and automatically updates vector embeddings.",
            args_schema=UpdateStatusInput,
        ),
        StructuredTool.from_function(
            coroutine=_action_items,
            name="get_action_items",
            description="Fetches pending high-urgency action items, upcoming interview deadlines, and tasks that require candidate response.",
            args_schema=ActionItemsInput,
        ),
    ]
