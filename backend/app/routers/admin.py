import logging
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    OtherEventModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Deletion Operations"])

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
                "TRUNCATE TABLE email_companies, email_applications, "
                "email_application_events, email_application_embeddings, "
                "email_other_events RESTART IDENTITY CASCADE;"
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
    
    is_latest_event = (latest_event_id == event_id)

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
            logger.info(f"Latest event deleted for App {app_id}. Triggering re-indexing.")
            embedding_reindexed = True
        else:
            # If NO events remain for this application, drop its vector embedding
            await db.execute(
                text("DELETE FROM email_application_embeddings WHERE email_application_id = :app_id"),
                {"app_id": app_id}
            )
            await db.commit()
            logger.info(f"No events remaining for App {app_id}. Deleted embedding record.")

    return {
        "status": "success",
        "message": f"Event {event_id} deleted.",
        "embedding_resynced": embedding_reindexed,
    }