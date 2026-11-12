import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from rapidfuzz import fuzz
from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

# Adjust imports based on your database session setup
from app.core.database import get_db
from app.core.url_utils import normalize_job_url
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    JobPostingModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel
from app.schemas.staging import (
    StagingBulkDismissRequest,
    StagingBulkDismissResponse,
    StagingCandidateAppItem,
    StagingCandidateAppsResponse,
    StagingCandidateCompanySummary,
    StagingDetectedSignals,
    StagingItemRead,
    StagingItemResolve,
    StagingPaginationResponse,
)
from app.services.company_resolver import resolve_or_create_company
from app.services.domain_resolver import (
    clean_company_name,
    clean_domain,
    extract_email_identity_signals,
    extract_organization_from_ats_url,
)
from app.services.evaluation_worker import process_evaluation_task
from app.services.llm import async_enqueue_application_embedding
from app.services.skill_normalizer import normalize_skills_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staging", tags=["staging"])

_ACTIVE_APP_STATUSES = {
    "APPLIED",
    "ONLINE_ASSESSMENT",
    "TECHNICAL_INTERVIEW",
    "OFFER",
    "RECRUITER_CONTACT",
    "PHONE_SCREEN",
    "BEHAVIORAL_INTERVIEW",
    "ONSITE_INTERVIEW",
    "FINAL_INTERVIEW",
    "INTERVIEW",
    "SCREENING",
    "IN_PROGRESS",
}


def _enrich_staging_item_signals(item: StagingItemModel) -> StagingItemRead:
    """Computes deterministic URL/domain/ATS-slug signals on read so existing staged items expose them."""
    validated = StagingItemRead.model_validate(item)
    ext = (
        dict(validated.extracted_data)
        if isinstance(validated.extracted_data, dict)
        else validated.extracted_data.model_dump()
    )
    signals = extract_email_identity_signals(
        raw_body=item.email_raw_body,
        sender=item.email_sender,
        subject=item.email_subject,
        extracted_data=ext,
    )
    for k, v in signals.items():
        if v and not ext.get(k):
            ext[k] = v
    if not ext.get("job_url") and signals.get("detected_job_url"):
        ext["job_url"] = signals["detected_job_url"]
    validated.extracted_data = ext
    return validated


@router.get("", response_model=StagingPaginationResponse)
async def list_staging_items(
    status_filter: str | None = Query(default="PENDING", alias="status"),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="received_at", pattern="^(received_at|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Extract safe values for direct Python test calls and FastAPI queries
    status_filter_val = (
        status_filter
        if isinstance(status_filter, str) or status_filter is None
        else "PENDING"
    )
    search_val = search if isinstance(search, str) else None
    sort_by_val = sort_by if isinstance(sort_by, str) else "received_at"
    sort_order_val = sort_order if isinstance(sort_order, str) else "desc"
    limit_val = limit if isinstance(limit, int) else 50
    offset_val = offset if isinstance(offset, int) else 0

    query = select(StagingItemModel)
    count_query = select(func.count()).select_from(StagingItemModel)

    if status_filter_val:
        query = query.where(StagingItemModel.status == status_filter_val)
        count_query = count_query.where(StagingItemModel.status == status_filter_val)

    if search_val and search_val.strip():
        search_term = f"%{search_val.strip()}%"
        search_filter = or_(
            StagingItemModel.email_sender.ilike(search_term),
            StagingItemModel.email_sender_name.ilike(search_term),
            StagingItemModel.email_subject.ilike(search_term),
            StagingItemModel.match_reason.ilike(search_term),
            cast(StagingItemModel.extracted_data, String).ilike(search_term),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

    # Dynamic SQL Sorting
    is_asc = sort_order_val.lower() == "asc"
    if sort_by_val == "received_at":
        sort_col = func.coalesce(
            StagingItemModel.email_received_at, StagingItemModel.created_at
        )
        if is_asc:
            query = query.order_by(sort_col.asc(), StagingItemModel.id.asc())
        else:
            query = query.order_by(sort_col.desc(), StagingItemModel.id.desc())
    else:
        if is_asc:
            query = query.order_by(
                StagingItemModel.created_at.asc(), StagingItemModel.id.asc()
            )
        else:
            query = query.order_by(
                StagingItemModel.created_at.desc(), StagingItemModel.id.desc()
            )

    query = query.offset(offset_val).limit(limit_val)
    result = await db.execute(query)
    db_items = result.scalars().all()

    # Convert ORM models explicitly to StagingItemRead Pydantic instances with enriched signals
    items = [_enrich_staging_item_signals(item) for item in db_items]

    return StagingPaginationResponse(total=total, items=items)


def _score_app_for_staging(
    app: ApplicationModel,
    signals: dict | None,
    q: str | None,
    default_company_query: str | None = None,
) -> tuple[float, float, str | None]:
    """Returns (effective_score, signal_score, match_reason_label) for a candidate application."""
    comp = app.company
    comp_name = (comp.name if comp else "") or ""
    comp_norm = (comp.name_normalized if comp else "") or comp_name.lower()
    comp_clean = clean_company_name(comp_name).lower()
    comp_dom = (
        clean_domain(comp.domain if comp else None) or clean_domain(comp_norm) or ""
    )
    comp_dom_root = comp_dom.split(".")[0].lower() if comp_dom else ""
    pos_norm = (app.position_normalized or app.position or "").lower()
    app_url = normalize_job_url(app.job_url) or normalize_job_url(
        app.job_posting.job_url if app.job_posting else None
    )

    sig_score = 0.0
    sig_reason: str | None = None

    if signals:
        cand_urls = signals.get("candidate_job_urls") or []
        det_domains = signals.get("detected_domains") or []
        sender_dom = signals.get("sender_domain")
        ats_slugs = [s.lower() for s in (signals.get("ats_slugs") or []) if s]
        sig_comp = (signals.get("cleaned_company") or "").lower()

        # Tier 1: Exact Job URL
        if app_url and app_url in cand_urls:
            sig_score = 1.0
            sig_reason = "Matched Job URL"
        # Tier 2: Domain / Sender Domain
        elif comp_dom and comp_dom in det_domains:
            sig_score = 0.96
            sig_reason = (
                f"Matched sender @{comp_dom}"
                if sender_dom == comp_dom
                else f"Matched domain {comp_dom}"
            )
        elif (
            comp_clean
            and len(comp_clean) >= 2
            and any(d.split(".")[0].lower() == comp_clean for d in det_domains)
        ):
            matched_d = next(
                d for d in det_domains if d.split(".")[0].lower() == comp_clean
            )
            sig_score = 0.94
            sig_reason = f"Matched domain {matched_d}"
        # Tier 3: ATS Org Slug
        elif ats_slugs and (
            (comp_clean and comp_clean in ats_slugs)
            or (comp_dom_root and comp_dom_root in ats_slugs)
        ):
            matched_slug = comp_clean if comp_clean in ats_slugs else comp_dom_root
            sig_score = 0.92
            sig_reason = f"Matched ATS '{matched_slug}'"
        # Tier 4: Cleaned Company Name
        elif sig_comp:
            if sig_comp == comp_clean or (comp_dom_root and sig_comp == comp_dom_root):
                sig_score = 0.90
                sig_reason = "Matched company"
            else:
                ratio = (
                    max(
                        fuzz.ratio(sig_comp, comp_clean),
                        fuzz.ratio(sig_comp, comp_norm),
                    )
                    / 100.0
                )
                if ratio >= 0.75:
                    sig_score = ratio * 0.88
                    sig_reason = "Similar company"

    q_raw = (q or "").strip().lower()
    if q_raw in {"unknown company", "unknown"}:
        q_raw = ""

    if not q_raw:
        return sig_score, sig_score, sig_reason

    q_clean = clean_company_name(q_raw).lower()
    q_dom = clean_domain(q_raw)
    q_slug = extract_organization_from_ats_url(q_raw)

    q_score = 0.0
    q_reason: str | None = None

    if app_url and q_raw in app_url.lower():
        q_score = 0.98
        q_reason = "Matched Job URL"
    elif q_dom and (
        comp_dom == q_dom
        or (comp_dom_root and comp_dom_root == q_dom.split(".")[0].lower())
        or (comp_clean and comp_clean == q_dom.split(".")[0].lower())
    ):
        q_score = 0.96
        q_reason = f"Matched domain {comp_dom or q_dom}"
    elif q_slug and (comp_clean == q_slug or comp_dom_root == q_slug):
        q_score = 0.94
        q_reason = f"Matched ATS '{q_slug}'"
    elif q_clean and (
        comp_clean == q_clean
        or comp_norm == q_raw
        or (comp_dom_root and comp_dom_root == q_clean)
    ):
        q_score = 0.95
        q_reason = f"Matched {comp_dom}" if comp_dom else "Matched company"
    elif (
        q_clean
        and len(q_clean) >= 2
        and (
            q_clean in comp_clean
            or comp_clean in q_clean
            or q_raw in comp_norm
            or (comp_dom and q_raw in comp_dom)
        )
    ):
        q_score = 0.86
        q_reason = "Company match"
    elif q_raw in pos_norm:
        q_score = 0.82
        q_reason = "Role match"
    else:
        combined = f"{comp_clean} {comp_norm} {pos_norm} {comp_dom}"
        best_fuzz = (
            max(
                fuzz.ratio(q_clean or q_raw, comp_clean),
                fuzz.ratio(q_raw, comp_norm),
                fuzz.ratio(q_raw, pos_norm),
                fuzz.token_set_ratio(q_raw, combined) * 0.9,
            )
            / 100.0
        )
        if best_fuzz >= 0.55:
            q_score = best_fuzz * 0.8
            q_reason = "Fuzzy match"

    is_default_query = bool(
        default_company_query
        and q_clean == clean_company_name(default_company_query).lower()
    )
    if is_default_query and sig_score > q_score:
        return sig_score, sig_score, sig_reason

    return (
        q_score,
        sig_score,
        (sig_reason if sig_score >= 0.9 else (q_reason or sig_reason)),
    )


@router.get("/candidate-applications", response_model=StagingCandidateAppsResponse)
async def get_staging_candidate_applications(
    staging_item_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Queries PostgreSQL for non-assessment applications ranked by the 4-tier email signal cascade and search query."""
    staging_id_val = staging_item_id if isinstance(staging_item_id, int) else None
    q_val = q.strip() if isinstance(q, str) and q.strip() else None
    limit_val = limit if isinstance(limit, int) else 30

    staged_item: StagingItemModel | None = None
    signals_dict: dict | None = None
    default_comp_query: str | None = None

    if staging_id_val is not None:
        staged_res = await db.execute(
            select(StagingItemModel).where(StagingItemModel.id == staging_id_val)
        )
        staged_item = staged_res.scalar_one_or_none()
        if staged_item:
            ext = (
                staged_item.extracted_data
                if isinstance(staged_item.extracted_data, dict)
                else {}
            )
            signals_dict = extract_email_identity_signals(
                raw_body=staged_item.email_raw_body,
                sender=staged_item.email_sender,
                subject=staged_item.email_subject,
                extracted_data=ext,
            )
            default_comp_query = (
                ext.get("company")
                or ext.get("company_name")
                or signals_dict.get("cleaned_company")
            )

    stmt = (
        select(ApplicationModel)
        .join(ApplicationModel.company)
        .outerjoin(
            JobPostingModel,
            ApplicationModel.id == JobPostingModel.application_id,
        )
        .options(
            joinedload(ApplicationModel.company),
            selectinload(ApplicationModel.job_posting),
        )
        .where(ApplicationModel.status != "ASSESSMENT")
    )
    res = await db.execute(stmt)
    all_apps = res.scalars().unique().all()

    scored_candidates: list[tuple[float, int, float, StagingCandidateAppItem]] = []
    signal_matches: list[tuple[float, int, float, StagingCandidateAppItem]] = []

    for app in all_apps:
        if not app.company:
            continue
        eff_score, sig_score, reason_label = _score_app_for_staging(
            app=app,
            signals=signals_dict,
            q=q_val,
            default_company_query=default_comp_query,
        )
        is_active = (app.status or "").upper() in _ACTIVE_APP_STATUSES
        activity_dt = app.last_activity_at or app.updated_at or app.created_at
        activity_ts = activity_dt.timestamp() if activity_dt else 0.0

        item_schema = StagingCandidateAppItem(
            id=app.id,
            company_id=app.company.id,
            company=StagingCandidateCompanySummary(
                id=app.company.id,
                name=app.company.name,
                domain=app.company.domain,
            ),
            position=app.position,
            status=app.status,
            job_url=app.job_url
            or (app.job_posting.job_url if app.job_posting else None),
            application_date=app.application_date,
            last_activity_at=activity_dt,
            match_score=round(eff_score, 3),
            match_reason_label=reason_label,
            is_active_stage=is_active,
        )

        if sig_score >= 0.72:
            sig_item = item_schema.model_copy(
                update={"match_score": round(sig_score, 3)}
            )
            signal_matches.append(
                (sig_score, 1 if is_active else 0, activity_ts, sig_item)
            )

        if q_val and q_val.lower() not in {"unknown company", "unknown"}:
            if eff_score >= 0.35:
                # Active stage receives +0.02 tie-breaker boost within same match tier
                rank_score = eff_score + (0.02 if is_active else 0.0)
                scored_candidates.append(
                    (rank_score, 1 if is_active else 0, activity_ts, item_schema)
                )
        else:
            rank_score = (
                (eff_score + (0.02 if is_active else 0.0))
                if eff_score > 0
                else (0.1 if is_active else 0.0)
            )
            scored_candidates.append(
                (rank_score, 1 if is_active else 0, activity_ts, item_schema)
            )

    scored_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    top_items = [entry[3] for entry in scored_candidates[:limit_val]]

    # Smart suggestion based on staged item's signals
    smart_suggestion: StagingCandidateAppItem | None = None
    if signal_matches:
        if (
            staged_item
            and staged_item.match_reason == "REAPPLICATION_PREVIOUSLY_CONCLUDED"
        ):
            concluded = [m for m in signal_matches if m[1] == 0]
            if concluded:
                concluded.sort(key=lambda x: (x[0], x[2]), reverse=True)
                smart_suggestion = concluded[0][3]
        if not smart_suggestion:
            signal_matches.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            smart_suggestion = signal_matches[0][3]

    return StagingCandidateAppsResponse(
        items=top_items,
        detected_signals=(
            StagingDetectedSignals(**signals_dict) if signals_dict else None
        ),
        smart_suggestion=smart_suggestion,
    )


@router.post("/bulk-dismiss", response_model=StagingBulkDismissResponse)
async def bulk_dismiss_staging_items(
    payload: StagingBulkDismissRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk dismisses specific staging items or all pending staging items matching filters."""
    if payload.dismiss_all_pending:
        del_query = delete(StagingItemModel)
        if payload.status_filter:
            del_query = del_query.where(
                StagingItemModel.status == payload.status_filter
            )
        if payload.search and payload.search.strip():
            search_term = f"%{payload.search.strip()}%"
            search_filter = or_(
                StagingItemModel.email_sender.ilike(search_term),
                StagingItemModel.email_sender_name.ilike(search_term),
                StagingItemModel.email_subject.ilike(search_term),
                StagingItemModel.match_reason.ilike(search_term),
                cast(StagingItemModel.extracted_data, String).ilike(search_term),
            )
            del_query = del_query.where(search_filter)

        res = await db.execute(del_query)
        await db.commit()
        count = res.rowcount
        return StagingBulkDismissResponse(
            dismissed_count=count,
            message=f"Successfully dismissed {count} staging item{'s' if count != 1 else ''}.",
        )

    if not payload.item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either item_ids or dismiss_all_pending=true must be provided.",
        )

    del_stmt = delete(StagingItemModel).where(StagingItemModel.id.in_(payload.item_ids))
    res = await db.execute(del_stmt)
    await db.commit()
    count = res.rowcount

    return StagingBulkDismissResponse(
        dismissed_count=count,
        message=f"Successfully dismissed {count} staging item{'s' if count != 1 else ''}.",
    )


@router.get("/{item_id}", response_model=StagingItemRead)
async def get_staging_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetches full details for a single staged item."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    return _enrich_staging_item_signals(item)


@router.post("/{item_id}/resolve", response_model=dict)
async def resolve_staging_item(
    item_id: int,
    payload: StagingItemResolve,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Accepts user fixes, applies them to DB records, and marks the staged item PROCESSED."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    staged_item = res.scalar_one_or_none()

    if not staged_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    if staged_item.status == "PROCESSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item has already been processed.",
        )

    try:
        application = None
        effective_company = (
            payload.company_name or payload.company or "Unknown Company"
        ).strip()
        position_norm = payload.position.strip().lower()
        clean_job_url = normalize_job_url(payload.job_url)

        # Option A: User provided explicit application_id
        if payload.application_id and not payload.create_new:
            app_stmt = select(ApplicationModel).where(
                ApplicationModel.id == payload.application_id
            )
            app_res = await db.execute(app_stmt)
            application = app_res.scalar_one_or_none()

            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target Application ID {payload.application_id} not found.",
                )

        # Option B: Match or create company and application
        if not application:
            company, _ = await resolve_or_create_company(
                db=db,
                company_name=effective_company,
            )

            if not payload.create_new:
                app_stmt = select(ApplicationModel).where(
                    ApplicationModel.company_id == company.id,
                    ApplicationModel.position_normalized == position_norm,
                )
                app_res = await db.execute(app_stmt)
                application = app_res.scalar_one_or_none()

            if not application:
                application = ApplicationModel(
                    company_id=company.id,
                    position=payload.position.strip(),
                    position_normalized=position_norm,
                    external_job_id=payload.external_job_id,
                    job_url=clean_job_url,
                    status=payload.status or "APPLIED",
                    application_date=(
                        staged_item.email_received_at.date()
                        if staged_item.email_received_at
                        else datetime.now(UTC).date()
                    ),
                    last_activity_at=staged_item.email_received_at or datetime.now(UTC),
                )
                db.add(application)
                await db.flush()
            elif staged_item.email_received_at:
                application.last_activity_at = staged_item.email_received_at

        # Update application status if modified
        if payload.status:
            application.status = payload.status
        if clean_job_url and not application.job_url:
            application.job_url = clean_job_url

        # Extract specs from payload or staged item
        extracted = (
            staged_item.extracted_data
            if isinstance(staged_item.extracted_data, dict)
            else (
                staged_item.extracted_data.model_dump()
                if hasattr(staged_item.extracted_data, "model_dump")
                else {}
            )
        )

        desc_md = (
            payload.description_markdown.strip()
            if payload.description_markdown and payload.description_markdown.strip()
            else None
        )
        salary_min = (
            payload.salary_min
            if payload.salary_min is not None
            else extracted.get("salary_min")
        )
        salary_max = (
            payload.salary_max
            if payload.salary_max is not None
            else extracted.get("salary_max")
        )
        currency = payload.currency or extracted.get("currency", "USD")
        location = payload.location or extracted.get("location")
        work_model = payload.work_model or extracted.get("work_model")
        raw_skills = (
            payload.required_skills
            or extracted.get("required_skills")
            or list(
                dict.fromkeys(
                    (extracted.get("matching_skills") or [])
                    + (extracted.get("missing_skills") or [])
                )
            )
        )
        skills = normalize_skills_list(raw_skills)

        has_posting_data = any(
            [
                clean_job_url,
                desc_md,
                salary_min is not None,
                salary_max is not None,
                location,
                work_model,
                bool(skills),
            ]
        )

        # Upsert JobPostingModel only if job posting information is provided or already exists
        jp_stmt = select(JobPostingModel).where(
            JobPostingModel.application_id == application.id
        )
        jp_res = await db.execute(jp_stmt)
        job_posting = jp_res.scalar_one_or_none()

        if not job_posting and has_posting_data:
            job_posting = JobPostingModel(
                application_id=application.id,
                job_url=clean_job_url or f"lead-{application.id}",
                description_markdown=desc_md,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                location=location,
                work_model=work_model,
                required_skills=skills,
            )
            db.add(job_posting)
        elif job_posting:
            if desc_md is not None:
                job_posting.description_markdown = desc_md
            if clean_job_url:
                job_posting.job_url = clean_job_url
            if salary_min is not None:
                job_posting.salary_min = salary_min
            if salary_max is not None:
                job_posting.salary_max = salary_max
            if location:
                job_posting.location = location
            if work_model:
                job_posting.work_model = work_model
            if skills:
                job_posting.required_skills = skills

        # Create Timeline Event
        summary_val = (
            payload.summary
            or extracted.get("summary")
            or staged_item.email_subject
            or f"Staged item resolved for {payload.position} at {effective_company}."
        )
        event_time = staged_item.email_received_at or datetime.now(UTC)
        application.last_activity_at = event_time
        application.updated_at = datetime.now(UTC)

        # Prepare raw_payload preserving scheduled_at and interview_stage for Application badges
        event_raw_payload = dict(extracted) if isinstance(extracted, dict) else {}
        if payload.due_date:
            from app.core.config_manager import get_system_settings_model
            from app.services.email_normalization import normalize_instant

            zone = (await get_system_settings_model(db)).display_timezone or "UTC"
            payload.due_date = normalize_instant(payload.due_date, zone)
            if payload.due_date is None:
                raise HTTPException(
                    status_code=422, detail="Ambiguous or invalid deadline"
                )
            event_raw_payload["temporal"] = {
                "version": 2,
                "deadline": {
                    "at": payload.due_date.isoformat(),
                    "precision": "instant",
                },
            }
        if (
            application.status in {"TECHNICAL_INTERVIEW", "ONLINE_ASSESSMENT"}
            and payload.event_type
        ):
            event_raw_payload["interview_stage"] = payload.event_type

        event = ApplicationEventModel(
            email_application_id=application.id,
            email_message_id=staged_item.email_message_id,
            email_conversation_id=staged_item.email_conversation_id
            or f"stage-conv-{staged_item.id}",
            email_sender=staged_item.email_sender,
            email_sender_name=staged_item.email_sender_name,
            email_subject=staged_item.email_subject,
            email_received_at=event_time,
            email_event_type=payload.event_type or "PRE_APPLICATION_ASSESSMENT",
            email_status_after_event=application.status,
            email_summary=summary_val,
            email_action_required=payload.action_required,
            email_action=payload.action,
            email_raw_body=staged_item.email_raw_body,
            raw_payload=event_raw_payload or None,
            source_channel="STAGING",
        )
        db.add(event)
        await db.flush()

        # Check if Action Item should be generated
        action_text = (
            payload.action
            or extracted.get("action_text")
            or (staged_item.email_subject if payload.action_required else None)
        )
        if (
            payload.action_required or extracted.get("action_required")
        ) and action_text:
            parsed_due = (
                payload.due_date.replace(tzinfo=None).replace(tzinfo=UTC)
                if payload.due_date
                else None
            )
            if parsed_due:
                now_utc = datetime.now(UTC)
                diff = (parsed_due - now_utc).total_seconds()
                if diff <= 48 * 3600:
                    urgency_val = "HIGH"
                elif diff <= 7 * 24 * 3600:
                    urgency_val = "MEDIUM"
                else:
                    urgency_val = "LOW"
            elif any(
                w in str(action_text).lower()
                for w in [
                    "urgent",
                    "deadline",
                    "schedule",
                    "interview",
                    "asap",
                    "offer",
                    "expir",
                ]
            ):
                urgency_val = "HIGH"
            else:
                urgency_val = "MEDIUM"

            existing_acts_res = await db.execute(
                select(ActionItemModel)
                .where(ActionItemModel.application_id == application.id)
                .order_by(ActionItemModel.created_at.desc())
            )
            existing_acts = existing_acts_res.scalars().all()
            action_norm = str(action_text)[:250].strip().lower()

            skip_completed_dup = False
            matched_pending: ActionItemModel | None = None
            for ex_act in existing_acts:
                ex_norm = (ex_act.title or "").strip().lower()
                if not ex_norm:
                    continue
                sim = fuzz.token_sort_ratio(action_norm, ex_norm)
                if ex_act.status in ("COMPLETED", "DISMISSED") and sim >= 85:
                    skip_completed_dup = True
                    break
                if ex_act.status == "PENDING" and sim >= 80 and matched_pending is None:
                    matched_pending = ex_act

            if not skip_completed_dup:
                if matched_pending is not None:
                    matched_pending.event_id = event.id
                    matched_pending.urgency = urgency_val
                    if parsed_due:
                        matched_pending.due_date = parsed_due
                else:
                    action_item = ActionItemModel(
                        application_id=application.id,
                        event_id=event.id,
                        title=str(action_text)[:250],
                        status="PENDING",
                        urgency=urgency_val,
                        due_date=parsed_due,
                    )
                    db.add(action_item)

        # Save IDs to variables before committing so we don't access expired ORM attributes
        target_app_id = application.id

        # Mark item as PROCESSED and save records to DB
        staged_item.status = "PROCESSED"
        await db.flush()
        target_event_id = event.id
        await db.commit()

        # Enqueue background AI job evaluation task if URL or description was provided
        if clean_job_url or desc_md:
            try:
                comp_display = effective_company
                pos_display = payload.position
                eval_task = IntakeEvaluationTaskModel(
                    task_type="JOB_EVALUATION",
                    job_url=clean_job_url,
                    raw_text=desc_md,
                    title_hint=f"Job Spec Analysis: {comp_display} - {pos_display}",
                    status="QUEUED",
                    stage="QUEUED",
                    result_json={
                        "target_application_id": target_app_id,
                        "skip_cover_letter": True,
                        "company": comp_display,
                        "position": pos_display,
                    },
                )
                db.add(eval_task)
                await db.commit()
                await db.refresh(eval_task)

                import asyncio

                asyncio.create_task(process_evaluation_task(task_id=eval_task.id))
            except Exception as eval_err:
                logger.warning(
                    "Failed to enqueue background evaluation task for App %d: %s",
                    target_app_id,
                    eval_err,
                )

    except Exception as e:
        logger.error("Failed to resolve staging item %d: %s", item_id, e, exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve staging item: {e!s}",
        )

    # Enqueue non-blocking background embedding generation (only if embeddings enabled)
    from app.core.config_manager import get_setting

    if await get_setting("ENABLE_EMBEDDINGS", False, db=db):
        background_tasks.add_task(
            async_enqueue_application_embedding, target_app_id, skip_llm_summary=True
        )

    return {
        "status": "success",
        "message": "Staged item resolved and committed to database.",
        "application_id": target_app_id,
        "event_id": target_event_id,
    }


@router.delete("/resolved", response_model=dict)
async def clear_resolved_staging_items(
    days_older_than: int | None = Query(default=None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Purges PROCESSED staging items, optionally older than a given number of days."""
    stmt = delete(StagingItemModel).where(StagingItemModel.status == "PROCESSED")
    if isinstance(days_older_than, int) and days_older_than > 0:
        cutoff = datetime.now(UTC) - timedelta(days=days_older_than)
        stmt = stmt.where(StagingItemModel.created_at <= cutoff)

    result = await db.execute(stmt)
    await db.commit()
    deleted_count = result.rowcount

    return {
        "status": "success",
        "message": f"Successfully deleted {deleted_count} resolved staging item(s).",
        "deleted_count": deleted_count,
    }


@router.delete("/{item_id}", response_model=dict)
async def reject_staging_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Marks a staged item as REJECTED if it is a false positive or non-job email."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    staged_item = res.scalar_one_or_none()

    if not staged_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    staged_item.status = "REJECTED"
    await db.commit()

    return {
        "status": "success",
        "message": f"Staging item {item_id} marked as REJECTED.",
    }


@router.post("/{item_id}/reopen", response_model=StagingItemRead)
async def reopen_staging_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Reopens a PROCESSED or REJECTED staging item back to PENDING for re-triaging."""
    stmt = select(StagingItemModel).where(StagingItemModel.id == item_id)
    res = await db.execute(stmt)
    staged_item = res.scalar_one_or_none()

    if not staged_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staging item with ID {item_id} not found.",
        )

    staged_item.status = "PENDING"
    staged_item.match_reason = "REOPENED_FOR_TRIAGE"
    await db.commit()
    await db.refresh(staged_item)

    return StagingItemRead.model_validate(staged_item)
