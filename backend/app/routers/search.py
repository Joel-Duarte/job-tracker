from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.embeddings import generate_query_embedding
from app.models.applications import (
    ApplicationEmbeddingModel,
    ApplicationModel,
    CompanyModel,
)
from app.schemas.search import SemanticSearchResult, CompanySearchResult

router = APIRouter(tags=["Search"])


@router.get(
    "/companies",
    response_model=List[CompanySearchResult],
    summary="Search or list companies",
)
async def search_companies(
    q: Optional[str] = Query(None, description="Fuzzy match company name"),
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
    "/semantic",
    response_model=List[SemanticSearchResult],
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
    query_vector = await generate_query_embedding(q)

    # Replicating (embedding <=> $1::vector)
    distance_expr = ApplicationEmbeddingModel.embedding.cosine_distance(query_vector)

    stmt = (
        select(
            ApplicationEmbeddingModel,
            ApplicationModel,
            CompanyModel,
            distance_expr.label("distance"),
        )
        .join(
            ApplicationModel,
            ApplicationEmbeddingModel.email_application_id == ApplicationModel.id,
        )
        .join(CompanyModel, ApplicationModel.company_id == CompanyModel.id)
        # Matches n8n: WHERE (embedding <=> $1::vector) < 0.60
        .where(distance_expr < max_distance)
        # Matches n8n: ORDER BY similarity ASC
        .order_by(distance_expr.asc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    results = []

    for emb, app, company, distance in result.all():
        dist_val = float(distance) if distance is not None else 0.0
        # Expose true similarity score (1 - distance) for the API response
        similarity_score = round(1.0 - dist_val, 6)

        results.append(
            SemanticSearchResult(
                id=app.id,
                application_id=app.id,
                company_name=company.name,
                position=app.position,
                email_subject=app.position,
                email_summary=emb.content,
                similarity_score=similarity_score,
                received_at=app.last_activity_at,
            )
        )

    return results