from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailBatchIntakeRequest, EmailProcessingSummary
from app.services.email_fetcher import fetch_emails_from_account
from app.services.intake import process_email_batch

router = APIRouter(prefix="/api/v1/intake", tags=["Intake"])


class SyncFolderRequest(BaseModel):
    account_id: int = Field(description="ID of the configured EmailAccountModel to sync")
    folder: Optional[str] = Field(
        default=None, 
        description="Override account folder (e.g., 'INBOX', 'Jobs'). Defaults to account settings."
    )
    since_date: Optional[datetime] = Field(
        default=None, 
        description="Fetch emails received after this ISO date. Leave blank for all."
    )


@router.post(
    "/sync-account",
    response_model=EmailProcessingSummary,
    status_code=status.HTTP_200_OK,
)
async def sync_email_account(
    payload: SyncFolderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Fetches emails directly from a configured provider via IMAP and parses them through the LLM pipeline."""
    # 1. Fetch account details from DB
    stmt = select(EmailAccountModel).where(EmailAccountModel.id == payload.account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account with ID {payload.account_id} not found.",
        )

    if not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email account '{account.name}' is disabled.",
        )

    # 2. Allow request-level folder override if provided
    if payload.folder:
        account.folder = payload.folder

    # 3. Fetch emails directly from the provider via IMAP
    try:
        raw_emails = await fetch_emails_from_account(account, since_date=payload.since_date)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect or fetch emails from IMAP server: {str(e)}",
        )

    if not raw_emails:
        return EmailProcessingSummary(
            total_received=0,
            applications_updated=0,
            other_events_logged=0,
            failed_count=0,
            errors=[],
        )

    # 4. Process fetched emails through LLM extraction & DB persistence
    summary = await process_email_batch(db, raw_emails)

    # 5. Update last_synced_at timestamp on account
    account.last_synced_at = datetime.now(timezone.utc)
    await db.commit()

    return summary


@router.post(
    "/process-batch",
    response_model=EmailProcessingSummary,
    status_code=status.HTTP_200_OK,
)
async def process_raw_email_batch(
    payload: EmailBatchIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Direct webhook endpoint to process a pre-fetched list of raw emails (e.g., from n8n or external scripts)."""
    summary = await process_email_batch(db, payload.emails)
    return summary