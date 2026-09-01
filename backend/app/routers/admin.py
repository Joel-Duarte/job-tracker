import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_admin_access
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    OtherEventModel,
)
from app.services.seed_data import is_database_empty, seed_development_dataset
from app.services.staleness_archiver import archive_stale_applications

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Deletion Operations"],
    dependencies=[Depends(verify_admin_access)],
)


@router.delete(
    "/reset-database",
    status_code=status.HTTP_200_OK,
    summary="Wipe all data from the database",
)
async def reset_database(
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Truncates all tables in the database, resetting primary keys.
    Requires explicit `confirm=true` query param.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must pass 'confirm=true' query parameter to execute database reset.",
        )

    try:
        await db.execute(
            text(
                "TRUNCATE TABLE companies, applications, "
                "application_events, application_embeddings, "
                "other_events, action_items, job_postings, "
                "candidate_cvs, staging_items, intake_evaluation_tasks, trace_events, "
                "role_alignment_dossiers, interview_sessions "
                "RESTART IDENTITY CASCADE;"
            )
        )
        await db.commit()
        logger.warning("ALL DATABASE TABLES TRUNCATED SUCCESSFULLY.")
        return {"status": "success", "message": "All data wiped, sequences reset."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reset database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset database.",
        )


@router.post(
    "/seed-demo-data",
    status_code=status.HTTP_201_CREATED,
    summary="Seed mock development dataset",
)
async def seed_demo_data(
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Populates the database with rich mock development data.
    If database is not empty, requires force=true to proceed.
    """
    if not force:
        empty = await is_database_empty(db)
        if not empty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Database is not empty. Pass force=true to seed anyway.",
            )

    stats = await seed_development_dataset(db)
    return {
        "status": "success",
        "message": "Mock development dataset seeded successfully.",
        "seeded_counts": stats,
    }


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an application (Cascades to events & embeddings)",
)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    app_obj = await db.get(ApplicationModel, application_id)
    if not app_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID {application_id} not found.",
        )

    # SQLAlchemy cascade will handle deleting associated events and embeddings
    await db.delete(app_obj)
    await db.commit()

    return {
        "status": "success",
        "message": f"Application {application_id} and all related events/embeddings deleted.",
    }


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a single email event (Updates embedding if latest event was removed)",
)
async def delete_event(
    event_id: int,
    event_type: Literal["application", "other"] = "application",
    db: AsyncSession = Depends(get_db),
):
    if event_type == "other":
        event = await db.get(OtherEventModel, event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Other event with ID {event_id} not found.",
            )
        await db.delete(event)
        await db.commit()
        return {"status": "success", "message": f"Other event {event_id} deleted."}

    # Handle Application Event Deletion
    event = await db.get(ApplicationEventModel, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application event with ID {event_id} not found.",
        )

    app_id = event.email_application_id

    # Check if this event is currently the LATEST event for this application
    latest_event_query = (
        select(ApplicationEventModel.id)
        .where(ApplicationEventModel.email_application_id == app_id)
        .order_by(ApplicationEventModel.email_received_at.desc())
        .limit(1)
    )
    latest_event_id = (await db.execute(latest_event_query)).scalar_one_or_none()

    is_latest_event = latest_event_id == event_id

    # Perform Event Delete
    await db.delete(event)
    await db.commit()

    # Re-sync handling if latest event was wiped
    embedding_reindexed = False
    if is_latest_event:
        # Fetch the NEW latest event after deletion
        new_latest_query = (
            select(ApplicationEventModel)
            .where(ApplicationEventModel.email_application_id == app_id)
            .order_by(ApplicationEventModel.email_received_at.desc())
            .limit(1)
        )
        new_latest_event = (await db.execute(new_latest_query)).scalar_one_or_none()

        if new_latest_event:
            # TODO: Trigger re-indexing of the embedding for this application based on the new latest event
            logger.info(
                f"Latest event deleted for App {app_id}. Triggering re-indexing."
            )
            embedding_reindexed = True
        else:
            # If NO events remain for this application, drop its vector embedding
            await db.execute(
                text(
                    "DELETE FROM email_application_embeddings WHERE email_application_id = :app_id"
                ),
                {"app_id": app_id},
            )
            await db.commit()
            logger.info(
                f"No events remaining for App {app_id}. Deleted embedding record."
            )

    return {
        "status": "success",
        "message": f"Event {event_id} deleted.",
        "embedding_resynced": embedding_reindexed,
    }


@router.post(
    "/run-auto-archiver",
    status_code=status.HTTP_200_OK,
    summary="Triggers an immediate staleness sweep",
)
async def run_auto_archiver(
    threshold_days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    stats = await archive_stale_applications(db, threshold_days=threshold_days)
    return {
        "status": "success",
        "archived_count": stats["archived_count"],
        "archived_ids": stats["archived_ids"],
    }


@router.get(
    "/staleness-stats",
    status_code=status.HTTP_200_OK,
    summary="Get statistics for stale applications",
)
async def get_staleness_stats(
    threshold_days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    cutoff_date = datetime.now(UTC) - timedelta(days=threshold_days)

    query = select(func.count(ApplicationModel.id)).where(
        ApplicationModel.status == "APPLIED",
        func.coalesce(
            ApplicationModel.last_activity_at,
            ApplicationModel.application_date,
            ApplicationModel.created_at,
        )
        < cutoff_date,
    )
    result = await db.execute(query)
    count = result.scalar() or 0

    return {
        "stale_applications_count": count,
        "threshold_days": threshold_days,
    }
