from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.applications import ApplicationModel, CompanyModel
from app.schemas.search import (
    ApplicationKeywordSearchResult,
    CompanySearchResult,
    SemanticSearchResult,
)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "/companies",
    response_model=list[CompanySearchResult],
    summary="Search or list companies",
)
async def search_companies(
    q: str | None = Query(None, description="Fuzzy match company name"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Returns matching companies alongside total tracked application count."""
    stmt = (
        select(
            CompanyModel.id,
            CompanyModel.name,
            CompanyModel.domain,
            func.count(ApplicationModel.id).label("applications_count"),
        )
        .outerjoin(ApplicationModel, CompanyModel.id == ApplicationModel.company_id)
        .group_by(CompanyModel.id)
    )

    if q:
        stmt = stmt.where(CompanyModel.name.ilike(f"%{q}%"))

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)

    return [
        CompanySearchResult(
            id=row.id,
            name=row.name,
            domain=row.domain,
            applications_count=row.applications_count,
        )
        for row in result.all()
    ]


@router.get(
    "/applications",
    response_model=list[ApplicationKeywordSearchResult],
    summary="Search applications by keyword",
)
async def search_applications(
    q: str = Query(..., min_length=2, description="Company, role, or status keywords"),
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search tracked applications with PostgreSQL text matching."""
    terms = [term for term in q.split() if len(term) > 1]
    stmt = (
        select(
            ApplicationModel.id.label("application_id"),
            CompanyModel.name.label("company_name"),
            ApplicationModel.position,
            ApplicationModel.status,
        )
        .join(CompanyModel, CompanyModel.id == ApplicationModel.company_id)
        .order_by(ApplicationModel.updated_at.desc())
        .limit(limit)
    )
    if terms:
        stmt = stmt.where(
            or_(
                *[
                    or_(
                        CompanyModel.name.ilike(f"%{term}%"),
                        ApplicationModel.position.ilike(f"%{term}%"),
                        ApplicationModel.status.ilike(f"%{term}%"),
                    )
                    for term in terms
                ]
            )
        )

    result = await db.execute(stmt)
    return [
        ApplicationKeywordSearchResult.model_validate(row._mapping)
        for row in result.all()
    ]


@router.get(
    "/semantic",
    response_model=list[SemanticSearchResult],
    summary="Semantic vector search across applications",
)
async def semantic_search(
    q: str = Query(..., min_length=2, description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50),
    max_distance: float = Query(
        0.60,
        ge=0.0,
        le=2.0,
        description="Maximum cosine distance threshold (default 0.60, matches n8n)",
    ),
    db: AsyncSession = Depends(get_db),
):
    raise HTTPException(
        status_code=410,
        detail="Semantic vector search is disabled. Use text search instead.",
    )
