from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.email_fetcher import fetch_emails_from_folder
from app.services.intake import process_email_batch

router = APIRouter(prefix="/api/v1/intake", tags=["Intake"])


class SyncFolderRequest(BaseModel):
    folder: str = "INBOX"
    since_date: Optional[datetime] = None


@router.post("/sync-folder")
async def sync_email_folder(
    payload: SyncFolderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetches emails directly from the specified mail folder and date range, 
    then processes and updates application tracking records in the database.
    """
    # 1. Fetch raw emails from provider internally using our service tool
    raw_emails = await fetch_emails_from_folder(
        folder_name=payload.folder,
        since_date=payload.since_date,
    )

    # 2. Process batch through LLM and persist records
    summary = await process_email_batch(db, raw_emails)

    return summary