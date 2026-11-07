import difflib
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.applications import ApplicationModel, CompanyModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.companies import (
    CompanyCreate,
    CompanyDirectoryStats,
    CompanyMergeRequest,
    CompanyPaginationResponse,
    CompanyRead,
    CompanyUpdate,
)
from app.services.company_resolver import GENERIC_ATS_HOSTS, resolve_or_create_company
from app.services.domain_resolver import (
    clean_domain,
    extract_domain_from_url,
    is_ats_vendor_match,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["Companies"])

ACTIVE_STATUSES = ("APPLIED", "ONLINE_ASSESSMENT", "TECHNICAL_INTERVIEW", "OFFER")


@router.get("", response_model=CompanyPaginationResponse)
async def list_companies(
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    q: str | None = Query(
        None, description="Search query by name, domain, notes, or research"
    ),
    sort_by: str = Query(
        "applications", description="Sort by: applications, recent, or name"
    ),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    without_research: bool = Query(
        False, description="Filter for companies without web intelligence"
    ),
    duplicate_ids: str | None = Query(
        None, description="Comma-separated IDs to filter potential duplicates"
    ),
    db: AsyncSession = Depends(get_db),
) -> CompanyPaginationResponse:
    """Lists companies with pagination, database-level sorting, search, and global directory statistics."""
    limit_val = limit if isinstance(limit, int) else 50
    offset_val = offset if isinstance(offset, int) else 0
    q_val = q if isinstance(q, str) else None
    sort_by_val = sort_by if isinstance(sort_by, str) else "applications"
    sort_order_val = sort_order if isinstance(sort_order, str) else "desc"
    without_research_val = (
        bool(without_research) if isinstance(without_research, bool) else False
    )
    duplicate_ids_val = duplicate_ids if isinstance(duplicate_ids, str) else None

    base_query = select(CompanyModel)
    count_query = select(func.count()).select_from(CompanyModel)

    conditions = []

    if q_val and q_val.strip():
        term = f"%{q_val.strip().lower()}%"
        conditions.append(
            or_(
                CompanyModel.name_normalized.ilike(term),
                CompanyModel.name.ilike(term),
                CompanyModel.domain.ilike(term),
                CompanyModel.notes.ilike(term),
                cast(CompanyModel.company_research, String).ilike(term),
            )
        )

    if without_research_val:
        conditions.append(
            or_(
                CompanyModel.company_research.is_(None),
                cast(CompanyModel.company_research["summary"], String).is_(None),
                cast(CompanyModel.company_research["summary"], String).in_(
                    ["null", '""', ""]
                ),
            )
        )

    if duplicate_ids_val and duplicate_ids_val.strip():
        try:
            parsed_ids = [
                int(i.strip())
                for i in duplicate_ids_val.split(",")
                if i.strip().isdigit()
            ]
            if parsed_ids:
                conditions.append(CompanyModel.id.in_(parsed_ids))
        except Exception:
            pass

    if conditions:
        base_query = base_query.where(*conditions)
        count_query = count_query.where(*conditions)

    # 1. Total count of filtered matches
    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    # 2. Database-level sorting
    is_asc = sort_order_val.lower() == "asc"
    if sort_by_val == "name":
        if is_asc:
            base_query = base_query.order_by(
                CompanyModel.name_normalized.asc(), CompanyModel.id.asc()
            )
        else:
            base_query = base_query.order_by(
                CompanyModel.name_normalized.desc(), CompanyModel.id.desc()
            )
    elif sort_by_val == "recent":
        recent_sub = (
            select(
                func.max(
                    func.coalesce(
                        ApplicationModel.application_date, ApplicationModel.created_at
                    )
                )
            )
            .where(ApplicationModel.company_id == CompanyModel.id)
            .scalar_subquery()
        )
        if is_asc:
            base_query = base_query.order_by(
                recent_sub.asc().nulls_first(), CompanyModel.name_normalized.asc()
            )
        else:
            base_query = base_query.order_by(
                recent_sub.desc().nulls_last(), CompanyModel.name_normalized.asc()
            )
    else:
        # Default: 'applications'
        app_count_sub = (
            select(func.count(ApplicationModel.id))
            .where(ApplicationModel.company_id == CompanyModel.id)
            .scalar_subquery()
        )
        if is_asc:
            base_query = base_query.order_by(
                app_count_sub.asc(), CompanyModel.name_normalized.asc()
            )
        else:
            base_query = base_query.order_by(
                app_count_sub.desc(), CompanyModel.name_normalized.asc()
            )

    # 3. Limit & Offset pagination with eager loading
    stmt = (
        base_query.limit(limit_val)
        .offset(offset_val)
        .options(
            selectinload(CompanyModel.applications).selectinload(
                ApplicationModel.events
            )
        )
    )
    res = await db.execute(stmt)
    companies = res.scalars().all()

    # 4. Active research tasks query to avoid stale QUEUED status
    active_stmt = select(
        IntakeEvaluationTaskModel.raw_text, IntakeEvaluationTaskModel.status
    ).where(
        IntakeEvaluationTaskModel.task_type == "COMPANY_RESEARCH",
        IntakeEvaluationTaskModel.status.in_(["QUEUED", "IN_PROGRESS"]),
    )
    active_res = await db.execute(active_stmt)
    active_task_map = {
        int(r[0]): r[1] for r in active_res.all() if r[0] and str(r[0]).isdigit()
    }

    result: list[CompanyRead] = []
    for c in companies:
        apps = list(c.applications or [])
        active_count = sum(1 for a in apps if a.status in ACTIVE_STATUSES)
        latest_date = None
        for a in apps:
            d = a.application_date or a.created_at
            if d and (latest_date is None or d > latest_date):
                latest_date = d

        # Truthful research status check
        if c.id in active_task_map:
            effective_status = active_task_map[c.id]
        elif c.company_research and c.company_research.get("summary"):
            effective_status = "COMPLETED"
        elif c.research_status == "FAILED":
            effective_status = "FAILED"
        else:
            effective_status = "NONE"

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
                research_status=effective_status,
                about_url=c.about_url,
                applications_count=len(apps),
                active_applications_count=active_count,
                last_applied_at=latest_date,
                applications=app_items,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    # 5. Global directory statistics
    stats_stmt = select(
        select(func.count()).select_from(CompanyModel).scalar_subquery(),
        select(func.count(func.distinct(ApplicationModel.company_id)))
        .where(ApplicationModel.status.in_(ACTIVE_STATUSES))
        .scalar_subquery(),
        select(func.count())
        .select_from(CompanyModel)
        .where(CompanyModel.research_status == "COMPLETED")
        .scalar_subquery(),
        select(func.count()).select_from(ApplicationModel).scalar_subquery(),
    )
    stats_res = await db.execute(stats_stmt)
    stats_row = stats_res.first()
    if stats_row:
        t = stats_row[0] or 0
        w = stats_row[1] or 0
        r = stats_row[2] or 0
        a = stats_row[3] or 0
    else:
        t = w = r = a = 0

    stats_obj = CompanyDirectoryStats(
        total=t,
        with_active=w,
        researched_count=r,
        total_applications=a,
        unresearched_count=max(0, t - r),
    )

    return CompanyPaginationResponse(
        items=result,
        total=total,
        limit=limit_val,
        offset=offset_val,
        stats=stats_obj,
    )


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Creates a new company record, cleans its domain/URL, and optionally queues AI web research."""
    from app.models.intake_tasks import IntakeEvaluationTaskModel
    from app.services.evaluation_worker import process_evaluation_task

    raw_name = payload.name.strip()
    if not raw_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name cannot be empty.",
        )

    # Sanitize and extract canonical domain if URL was provided
    parsed_domain = None
    if payload.domain:
        raw_dom = payload.domain.strip()
        parsed_domain = extract_domain_from_url(
            raw_dom, company_name=raw_name
        ) or clean_domain(raw_dom)

    # Clean about_url if provided
    parsed_about = payload.about_url.strip() if payload.about_url else None

    # Resolve or create company record
    company, was_created = await resolve_or_create_company(
        db=db,
        company_name=raw_name,
        domain=parsed_domain,
    )

    if parsed_about and not company.about_url:
        company.about_url = parsed_about
        company.updated_at = datetime.now(UTC)

    if payload.queue_research:
        # Check if an active research task already exists
        stmt_check = select(IntakeEvaluationTaskModel).where(
            IntakeEvaluationTaskModel.task_type == "COMPANY_RESEARCH",
            IntakeEvaluationTaskModel.status.in_(["QUEUED", "IN_PROGRESS"]),
            IntakeEvaluationTaskModel.raw_text == str(company.id),
        )
        existing_task = (await db.execute(stmt_check)).scalars().first()
        if not existing_task:
            task = IntakeEvaluationTaskModel(
                task_type="COMPANY_RESEARCH",
                title_hint=company.name,
                job_url=company.domain,
                raw_text=str(company.id),
                status="QUEUED",
                stage="QUEUED",
                result_json={
                    "company_id": company.id,
                    "company_name": company.name,
                    "domain": company.domain,
                    "about_url": company.about_url,
                },
            )
            db.add(task)
            company.research_status = "QUEUED"
            company.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(task)
            background_tasks.add_task(process_evaluation_task, task_id=task.id)
        else:
            await db.commit()
    else:
        await db.commit()

    await db.refresh(company)
    return await get_company(company_id=company.id, db=db)


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
    raw_companies = res.scalars().all()

    companies = [
        {
            "id": c.id,
            "name": c.name,
            "name_normalized": c.name_normalized or "",
            "domain": c.domain,
            "rating": c.rating,
            "applications_count": len(c.applications or [])
            if hasattr(c, "applications")
            else 0,
        }
        for c in raw_companies
    ]

    clusters = []
    visited_ids = set()

    for i, c1 in enumerate(companies):
        if c1["id"] in visited_ids:
            continue
        cluster = [c1]
        name1 = c1["name_normalized"]
        dom1 = c1["domain"]
        len1 = len(name1)

        for c2 in companies[i + 1 :]:
            if c2["id"] in visited_ids:
                continue
            is_dup = False
            name2 = c2["name_normalized"]
            dom2 = c2["domain"]

            # Check 1: Same normalized name
            if name1 and name1 == name2:
                is_dup = True
            # Check 2: Same non-ATS canonical domain
            elif (
                dom1
                and dom2
                and dom1 == dom2
                and (
                    not any(h in dom1 for h in GENERIC_ATS_HOSTS)
                    or is_ats_vendor_match(name1, dom1)
                )
            ):
                is_dup = True
            # Check 3: Fuzzy similarity >= 0.85
            elif name1 and name2:
                len2 = len(name2)
                if abs(len1 - len2) <= max(2, int((len1 + len2) * 0.15)):
                    if name1[0] == name2[0] or (
                        len1 >= 2 and len2 >= 2 and name1[:2] == name2[:2]
                    ):
                        if difflib.SequenceMatcher(None, name1, name2).ratio() >= 0.85:
                            is_dup = True

            if is_dup:
                cluster.append(c2)

        if len(cluster) > 1:
            for c in cluster:
                visited_ids.add(c["id"])
            clusters.append(
                [
                    {
                        "id": c["id"],
                        "name": c["name"],
                        "domain": c["domain"],
                        "applications_count": c["applications_count"],
                        "rating": c["rating"],
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

    # Active research task check for this company
    active_stmt = select(IntakeEvaluationTaskModel.status).where(
        IntakeEvaluationTaskModel.task_type == "COMPANY_RESEARCH",
        IntakeEvaluationTaskModel.status.in_(["QUEUED", "IN_PROGRESS"]),
        IntakeEvaluationTaskModel.raw_text == str(c.id),
    )
    active_task_status = (await db.execute(active_stmt)).scalars().first()

    if active_task_status:
        effective_status = active_task_status
    elif c.company_research and c.company_research.get("summary"):
        effective_status = "COMPLETED"
    elif c.research_status == "FAILED":
        effective_status = "FAILED"
    else:
        effective_status = "NONE"

    if c.research_status != effective_status:
        c.research_status = effective_status
        await db.commit()

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
        research_status=effective_status,
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
    if new_domain:
        new_domain = clean_domain(new_domain) or new_domain

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )

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

    # Duplicate prevention: check if an active research task already exists
    stmt_check = select(IntakeEvaluationTaskModel).where(
        IntakeEvaluationTaskModel.task_type == "COMPANY_RESEARCH",
        IntakeEvaluationTaskModel.status.in_(["QUEUED", "IN_PROGRESS"]),
        IntakeEvaluationTaskModel.raw_text == str(c.id),
    )
    existing_task = (await db.execute(stmt_check)).scalars().first()
    if existing_task:
        return {
            "status": "already_queued",
            "company_id": c.id,
            "task_id": existing_task.id,
            "message": f"Company research for '{c.name}' is already active in AI Queue.",
        }

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
    Enqueues individual COMPANY_RESEARCH evaluation tasks in the central AI Queue.
    Supports mode="missing" (default) or mode="all".
    Includes duplicate prevention to skip companies with active tasks already in-flight.
    """
    from app.models.intake_tasks import IntakeEvaluationTaskModel
    from app.services.evaluation_worker import process_evaluation_task

    company_ids = payload.get("company_ids") if payload else None
    mode = (payload.get("mode") or "missing").lower() if payload else "missing"

    if company_ids:
        stmt = select(CompanyModel).where(CompanyModel.id.in_(company_ids))
    else:
        stmt = select(CompanyModel)

    res = await db.execute(stmt)
    all_companies = list(res.scalars().all())

    # Mode filtering: "missing" filters for companies lacking research summary
    if mode == "missing" and not company_ids:
        target_companies = [
            c
            for c in all_companies
            if not c.company_research or not c.company_research.get("summary")
        ]
    else:
        target_companies = all_companies

    # Duplicate prevention: find companies already queued or in progress
    active_stmt = select(IntakeEvaluationTaskModel.raw_text).where(
        IntakeEvaluationTaskModel.task_type == "COMPANY_RESEARCH",
        IntakeEvaluationTaskModel.status.in_(["QUEUED", "IN_PROGRESS"]),
    )
    active_res = await db.execute(active_stmt)
    active_ids = {int(r) for r in active_res.scalars().all() if r and str(r).isdigit()}

    companies_to_queue = [c for c in target_companies if c.id not in active_ids]
    skipped_count = len(target_companies) - len(companies_to_queue)

    enqueued_tasks = []
    for c in companies_to_queue:
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
        "skipped_count": skipped_count,
        "task_ids": task_ids,
        "message": f"Successfully enqueued {len(task_ids)} company research tasks in AI Queue ({skipped_count} skipped as already active).",
    }
