import difflib
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.applications import ApplicationModel, CompanyModel
from app.schemas.companies import CompanyMergeRequest, CompanyRead, CompanyUpdate
from app.services.company_resolver import GENERIC_ATS_HOSTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["Companies"])

ACTIVE_STATUSES = ("APPLIED", "ONLINE_ASSESSMENT", "TECHNICAL_INTERVIEW", "OFFER")


@router.get("", response_model=list[CompanyRead])
async def list_companies(
    db: AsyncSession = Depends(get_db),
) -> list[CompanyRead]:
    """Lists all companies with aggregated application metrics."""
    stmt = (
        select(CompanyModel)
        .options(
            selectinload(CompanyModel.applications).selectinload(
                ApplicationModel.events
            )
        )
        .order_by(CompanyModel.name_normalized.asc())
    )
    res = await db.execute(stmt)
    companies = res.scalars().all()

    result: list[CompanyRead] = []
    for c in companies:
        apps = list(c.applications or [])
        active_count = sum(1 for a in apps if a.status in ACTIVE_STATUSES)
        latest_date = None
        for a in apps:
            d = a.application_date or a.created_at
            if d and (latest_date is None or d > latest_date):
                latest_date = d

        app_items = [
            {
                "id": a.id,
                "position": a.position,
                "status": a.status,
                "applied_at": a.application_date,
                "created_at": a.created_at,
                "job_url": a.job_url,
                "is_assessment": a.is_assessment or False,
                "latest_event_at": (
                    a.events[0].email_received_at or a.events[0].created_at
                    if a.events
                    else a.last_activity_at
                ),
            }
            for a in apps
        ]

        result.append(
            CompanyRead(
                id=c.id,
                name=c.name,
                name_normalized=c.name_normalized,
                domain=c.domain,
                rating=c.rating,
                notes=c.notes,
                pros=c.pros or [],
                red_flags=c.red_flags or [],
                company_research=c.company_research,
                researched_at=c.researched_at,
                research_status=c.research_status or "NONE",
                about_url=c.about_url,
                applications_count=len(apps),
                active_applications_count=active_count,
                last_applied_at=latest_date,
                applications=app_items,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return result


@router.get("/duplicates")
async def get_potential_duplicates(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Scans for potential duplicate companies based on:

    1. Matching canonical domains (non-ATS)
    2. Identical normalized names
    3. Fuzzy similarity >= 0.85
    Returns duplicate clusters and summary metrics.
    """
    stmt = (
        select(CompanyModel)
        .options(selectinload(CompanyModel.applications))
        .order_by(CompanyModel.name.asc())
    )
    res = await db.execute(stmt)
    companies = res.scalars().all()

    clusters = []
    visited_ids = set()

    for i, c1 in enumerate(companies):
        if c1.id in visited_ids:
            continue
        cluster = [c1]
        for c2 in companies[i + 1 :]:
            if c2.id in visited_ids:
                continue
            is_dup = False
            # Check 1: Same normalized name
            if c1.name_normalized and c1.name_normalized == c2.name_normalized:
                is_dup = True
            # Check 2: Same non-ATS canonical domain
            elif (
                c1.domain
                and c2.domain
                and c1.domain == c2.domain
                and not any(h in c1.domain for h in GENERIC_ATS_HOSTS)
            ):
                is_dup = True
            # Check 3: Fuzzy similarity >= 0.85
            elif (
                c1.name_normalized
                and c2.name_normalized
                and difflib.SequenceMatcher(
                    None, c1.name_normalized, c2.name_normalized
                ).ratio()
                >= 0.85
            ):
                is_dup = True

            if is_dup:
                cluster.append(c2)

        if len(cluster) > 1:
            for c in cluster:
                visited_ids.add(c.id)
            clusters.append(
                [
                    {
                        "id": c.id,
                        "name": c.name,
                        "domain": c.domain,
                        "applications_count": len(c.applications or []),
                        "rating": c.rating,
                    }
                    for c in cluster
                ]
            )

    duplicate_company_ids = list(visited_ids)
    return {
        "total_clusters": len(clusters),
        "total_duplicate_companies": len(duplicate_company_ids),
        "duplicate_company_ids": duplicate_company_ids,
        "clusters": clusters,
    }


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Retrieves full details, application history, and research for a specific company."""
    stmt = (
        select(CompanyModel)
        .where(CompanyModel.id == company_id)
        .options(
            selectinload(CompanyModel.applications).selectinload(
                ApplicationModel.events
            )
        )
    )
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )

    apps = list(c.applications or [])
    active_count = sum(1 for a in apps if a.status in ACTIVE_STATUSES)
    latest_date = None
    for a in apps:
        d = a.application_date or a.created_at
        if d and (latest_date is None or d > latest_date):
            latest_date = d

    app_items = [
        {
            "id": a.id,
            "position": a.position,
            "status": a.status,
            "applied_at": a.application_date,
            "created_at": a.created_at,
            "job_url": a.job_url,
            "is_assessment": a.is_assessment or False,
            "latest_event_at": (
                a.events[0].email_received_at or a.events[0].created_at
                if a.events
                else a.last_activity_at
            ),
        }
        for a in apps
    ]

    return CompanyRead(
        id=c.id,
        name=c.name,
        name_normalized=c.name_normalized,
        domain=c.domain,
        rating=c.rating,
        notes=c.notes,
        pros=c.pros or [],
        red_flags=c.red_flags or [],
        company_research=c.company_research,
        researched_at=c.researched_at,
        research_status=c.research_status or "NONE",
        about_url=c.about_url,
        applications_count=len(apps),
        active_applications_count=active_count,
        last_applied_at=latest_date,
        applications=app_items,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Updates candidate star rating, personal notes, pros/cons, and company research.

    If name/domain is updated and matches an existing company, auto-merges into it.
    """
    c = await db.get(CompanyModel, company_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )

    new_name = payload.name.strip() if payload.name is not None else c.name
    new_norm = new_name.lower()
    new_domain = (
        payload.domain.strip().lower() if payload.domain is not None else c.domain
    )
    if new_domain and any(h in new_domain for h in GENERIC_ATS_HOSTS):
        new_domain = None

    # Check if another company already matches new_norm or new_domain
    target_match = None
    if payload.name is not None:
        stmt_name = (
            select(CompanyModel)
            .where(
                CompanyModel.id != company_id,
                CompanyModel.name_normalized == new_norm,
            )
            .limit(1)
        )
        target_match = (await db.execute(stmt_name)).scalars().first()

    if not target_match and new_domain:
        stmt_dom = (
            select(CompanyModel)
            .where(
                CompanyModel.id != company_id,
                CompanyModel.domain == new_domain,
            )
            .limit(1)
        )
        target_match = (await db.execute(stmt_dom)).scalars().first()

    # If target duplicate found, auto-merge c into target_match
    if target_match:
        logger.info(
            "Renaming company %s (%s) matches existing company %s (%s). Auto-merging.",
            c.id,
            c.name,
            target_match.id,
            target_match.name,
        )
        await db.execute(
            update(ApplicationModel)
            .where(ApplicationModel.company_id == c.id)
            .values(company_id=target_match.id)
        )
        # Inherit metadata
        if not target_match.domain and (new_domain or c.domain):
            target_match.domain = new_domain or c.domain
        if not target_match.company_research and (
            payload.company_research or c.company_research
        ):
            target_match.company_research = (
                payload.company_research or c.company_research
            )
            target_match.researched_at = datetime.now(UTC)
        if target_match.rating is None and (
            payload.rating is not None or c.rating is not None
        ):
            target_match.rating = (
                payload.rating if payload.rating is not None else c.rating
            )
        if not target_match.notes and (payload.notes or c.notes):
            target_match.notes = payload.notes or c.notes
        if not target_match.pros and (payload.pros or c.pros):
            target_match.pros = payload.pros or c.pros
        if not target_match.red_flags and (payload.red_flags or c.red_flags):
            target_match.red_flags = payload.red_flags or c.red_flags

        target_match.updated_at = datetime.now(UTC)
        await db.delete(c)
        await db.commit()
        await db.refresh(target_match)
        return await get_company(company_id=target_match.id, db=db)

    # Standard in-place update
    if payload.name is not None:
        c.name = new_name
        c.name_normalized = new_norm
    if payload.domain is not None:
        c.domain = new_domain
    if payload.about_url is not None:
        c.about_url = payload.about_url.strip() or None
    if payload.rating is not None:
        c.rating = payload.rating
    if payload.notes is not None:
        c.notes = payload.notes
    if payload.pros is not None:
        c.pros = payload.pros
    if payload.red_flags is not None:
        c.red_flags = payload.red_flags
    if payload.company_research is not None:
        c.company_research = payload.company_research
        c.researched_at = datetime.now(UTC)
    if payload.research_status is not None:
        c.research_status = payload.research_status

    c.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(c)
    return await get_company(company_id=c.id, db=db)


@router.delete("/{company_id}", status_code=status.HTTP_200_OK)
async def delete_company(
    company_id: int,
    delete_applications: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a company, optionally deleting all of its linked applications."""
    company = await db.get(CompanyModel, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    apps_result = await db.execute(
        select(ApplicationModel).where(ApplicationModel.company_id == company_id)
    )
    applications = list(apps_result.scalars().all())
    if applications and not delete_applications:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company has linked applications. Confirm deletion with delete_applications=true.",
        )
    for application in applications:
        await db.delete(application)
    await db.delete(company)
    await db.commit()
    return {
        "status": "success",
        "deleted_company_id": company_id,
        "deleted_applications": len(applications),
    }


@router.post("/{company_id}/refresh-research")
async def refresh_company_research(
    company_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueues a COMPANY_RESEARCH task in the background AI queue for a single company."""
    from app.models.intake_tasks import IntakeEvaluationTaskModel
    from app.services.evaluation_worker import process_evaluation_task

    c = await db.get(CompanyModel, company_id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )

    task = IntakeEvaluationTaskModel(
        task_type="COMPANY_RESEARCH",
        title_hint=c.name,
        job_url=c.domain,
        raw_text=str(c.id),
        status="QUEUED",
        stage="QUEUED",
        result_json={
            "company_id": c.id,
            "company_name": c.name,
            "domain": c.domain,
            "about_url": c.about_url,
        },
    )
    db.add(task)
    c.research_status = "QUEUED"
    c.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(process_evaluation_task, task_id=task.id)

    return {
        "status": "queued",
        "company_id": c.id,
        "task_id": task.id,
        "message": f"Company research for '{c.name}' queued in AI Queue.",
    }


@router.post("/merge")
async def merge_companies(
    payload: CompanyMergeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Merges duplicate source companies into target company.
    Reassigns all applications to target, inherits metadata, then deletes the sources.
    """
    source_ids = list(payload.source_company_ids or [])
    if payload.source_company_id and payload.source_company_id not in source_ids:
        source_ids.append(payload.source_company_id)

    if not source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please specify at least one source company to merge.",
        )

    if payload.target_company_id in source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot merge a company into itself.",
        )

    target = await db.get(CompanyModel, payload.target_company_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target company {payload.target_company_id} not found",
        )

    merged_names = []
    for s_id in source_ids:
        source = await db.get(CompanyModel, s_id)
        if not source:
            continue
        merged_names.append(source.name)

        # 1. Reassign applications to target
        await db.execute(
            update(ApplicationModel)
            .where(ApplicationModel.company_id == source.id)
            .values(company_id=target.id)
        )

        # 2. Inherit domain/research/notes/pros/red_flags if target was lacking them
        if not target.domain and source.domain:
            target.domain = source.domain
        if not target.company_research and source.company_research:
            target.company_research = source.company_research
            target.researched_at = source.researched_at
        if not target.rating and source.rating:
            target.rating = source.rating
        if not target.notes and source.notes:
            target.notes = source.notes
        if not target.pros and source.pros:
            target.pros = source.pros
        if not target.red_flags and source.red_flags:
            target.red_flags = source.red_flags

        # 3. Delete source company
        await db.delete(source)

    await db.commit()

    return {
        "status": "merged",
        "target_company_id": target.id,
        "source_company_ids": source_ids,
        "message": f"Successfully merged {len(merged_names)} company/companies ({', '.join(merged_names)}) into '{target.name}'.",
    }


@router.post("/bulk-research")
async def bulk_research_companies(
    background_tasks: BackgroundTasks,
    payload: dict | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueues individual COMPANY_RESEARCH evaluation tasks in the central AI Queue
    for companies that do not currently possess a synthesized company intelligence summary.
    If company_ids is provided, enqueues strictly for those IDs.
    Filters in Python (not SQL) to correctly catch companies whose company_research JSONB
    exists but lacks a meaningful 'summary' field.
    """
    from app.models.intake_tasks import IntakeEvaluationTaskModel
    from app.services.evaluation_worker import process_evaluation_task

    company_ids = payload.get("company_ids") if payload else None

    if company_ids:
        stmt = select(CompanyModel).where(CompanyModel.id.in_(company_ids))
    else:
        # Fetch all; filter in Python so we catch non-null but summary-less JSONB dicts
        stmt = select(CompanyModel)

    res = await db.execute(stmt)
    all_companies = res.scalars().all()

    # Mirror the frontend's companiesWithoutInfo logic
    if not company_ids:
        all_companies = [
            c
            for c in all_companies
            if not c.company_research or not c.company_research.get("summary")
        ]

    enqueued_tasks = []
    for c in all_companies:
        task = IntakeEvaluationTaskModel(
            task_type="COMPANY_RESEARCH",
            title_hint=c.name,
            job_url=c.domain,
            raw_text=str(c.id),
            status="QUEUED",
            stage="QUEUED",
            result_json={
                "company_id": c.id,
                "company_name": c.name,
                "domain": c.domain,
                "about_url": c.about_url,
            },
        )
        db.add(task)
        c.research_status = "QUEUED"
        enqueued_tasks.append(task)

    await db.commit()

    task_ids = []
    for task in enqueued_tasks:
        await db.refresh(task)
        task_ids.append(task.id)
        background_tasks.add_task(process_evaluation_task, task_id=task.id)

    return {
        "status": "enqueued",
        "enqueued_count": len(task_ids),
        "task_ids": task_ids,
        "message": f"Successfully enqueued {len(task_ids)} company research tasks in AI Queue.",
    }
