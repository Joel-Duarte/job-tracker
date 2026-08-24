import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust imports based on your database session setup
from app.core.database import get_db
from app.core.url_utils import normalize_job_url
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel
from app.schemas.staging import (
    StagingItemRead,
    StagingItemResolve,
    StagingPaginationResponse,
)
from app.services.evaluation_worker import process_evaluation_task
from app.services.llm import generate_and_save_application_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staging", tags=["staging"])


@router.get("", response_model=StagingPaginationResponse)
async def list_staging_items(
    status_filter: str | None = Query(default="PENDING", alias="status"),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(StagingItemModel)
    count_query = select(func.count()).select_from(StagingItemModel)

    if status_filter:
        query = query.where(StagingItemModel.status == status_filter)
        count_query = count_query.where(StagingItemModel.status == status_filter)

    if search and isinstance(search, str) and search.strip():
        search_term = f"%{search.strip()}%"
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

    query = (
        query.order_by(StagingItemModel.created_at.desc()).offset(offset).limit(limit)
    )
    result = await db.execute(query)
    db_items = result.scalars().all()

    # Convert ORM models explicitly to StagingItemRead Pydantic instances
    items = [StagingItemRead.model_validate(item) for item in db_items]

    return StagingPaginationResponse(total=total, items=items)


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

    return item


@router.post("/{item_id}/resolve", response_model=dict)
async def resolve_staging_item(
    item_id: int,
    payload: StagingItemResolve,
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
        company_norm = effective_company.lower()
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
            comp_stmt = select(CompanyModel).where(
                CompanyModel.name_normalized == company_norm
            )
            comp_res = await db.execute(comp_stmt)
            company = comp_res.scalar_one_or_none()

            if not company:
                company = CompanyModel(
                    name=effective_company,
                    name_normalized=company_norm,
                )
                db.add(company)
                await db.flush()

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
                    status=payload.status or "ASSESSMENT",
                )
                db.add(application)
                await db.flush()

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
        skills = (
            payload.required_skills
            or extracted.get("required_skills")
            or list(
                dict.fromkeys(
                    (extracted.get("matching_skills") or [])
                    + (extracted.get("missing_skills") or [])
                )
            )
        )

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
        event = ApplicationEventModel(
            email_application_id=application.id,
            email_message_id=staged_item.email_message_id,
            email_conversation_id=staged_item.email_conversation_id
            or f"stage-conv-{staged_item.id}",
            email_sender=staged_item.email_sender,
            email_sender_name=staged_item.email_sender_name,
            email_subject=staged_item.email_subject,
            email_received_at=staged_item.email_received_at or datetime.now(UTC),
            email_event_type=payload.event_type or "PRE_APPLICATION_ASSESSMENT",
            email_status_after_event=application.status,
            email_summary=summary_val,
            email_action_required=payload.action_required,
            email_action=payload.action,
            email_raw_body=staged_item.email_raw_body,
            raw_payload=extracted if isinstance(extracted, dict) else None,
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
            if payload.due_date:
                now_utc = datetime.now(UTC)
                due_dt = (
                    payload.due_date
                    if payload.due_date.tzinfo
                    else payload.due_date.replace(tzinfo=UTC)
                )
                diff = (due_dt - now_utc).total_seconds()
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

            action_item = ActionItemModel(
                application_id=application.id,
                event_id=event.id,
                title=str(action_text)[:250],
                status="PENDING",
                urgency=urgency_val,
                due_date=payload.due_date,
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

    # Isolated embedding block after successful commit
    try:
        await generate_and_save_application_embedding(db, target_app_id)
    except Exception as e:
        logger.warning(
            "Failed to generate embedding for Application ID %d: %s", target_app_id, e
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
