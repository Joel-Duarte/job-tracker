from datetime import datetime, timezone
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import EmailBatchIntakeRequest, DirectEmailIntakeRequest, EmailPayload
from app.services.email_fetcher import fetch_emails_from_account
from app.services.intake import process_email_batch_sequential
from app.services.task_tracker import task_tracker

router = APIRouter(prefix="/intake", tags=["Intake"])


class SyncFolderRequest(BaseModel):
    account_id: int = Field(description="ID of the configured EmailAccountModel to sync")
    folder: Optional[str] = Field(default=None)
    since_date: Optional[datetime] = Field(default=None)


class TaskResponse(BaseModel):
    task_id: str
    message: str


async def _run_background_intake(account_id: int, folder: Optional[str], since_date: Optional[datetime], task_id: str):
    """Background runner worker that handles its own DB session."""
    async with AsyncSessionLocal() as db:
        stmt = select(EmailAccountModel).where(EmailAccountModel.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        if not account or not account.is_active:
            task_tracker.fail_task(task_id, "Account not found or inactive.")
            return

        if folder:
            account.folder = folder

        try:
            raw_emails = await fetch_emails_from_account(account, since_date=since_date)
        except Exception as e:
            task_tracker.fail_task(task_id, f"IMAP connection error: {str(e)}")
            return

        if not raw_emails:
            task_tracker.complete_task(task_id)
            return

        # Execute processing queue
        await process_email_batch_sequential(db, raw_emails, task_id)

        # Update last_synced_at
        account.last_synced_at = datetime.now(timezone.utc)
        await db.commit()


@router.post("/sync-account", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def sync_email_account(
    payload: SyncFolderRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Triggers asynchronous email sync in the background and returns a task tracking ID immediately."""
    stmt = select(EmailAccountModel).where(EmailAccountModel.id == payload.account_id)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email account ID {payload.account_id} not found.",
        )

    # Initial quick fetch to initialize total_emails in tracker
    raw_emails = await fetch_emails_from_account(account, since_date=payload.since_date)
    task_id = task_tracker.create_task(total_emails=len(raw_emails), account_id=payload.account_id)

    if len(raw_emails) == 0:
        task_tracker.complete_task(task_id)
        return TaskResponse(task_id=task_id, message="No new emails found to process.")

    # Hand off long-running processing to background execution
    background_tasks.add_task(
        process_email_batch_sequential,
        db=db,
        emails=raw_emails,
        task_id=task_id,
    )

    return TaskResponse(
        task_id=task_id,
        message=f"Sync started in background for {len(raw_emails)} emails. Track status using GET /api/v1/intake/tasks/{task_id}",
    )


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Retrieves live progress for an ongoing or completed email intake task."""
    task_info = task_tracker.get_task(task_id)
    if not task_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found.",
        )
    return task_info

@router.post("/test-direct", status_code=status.HTTP_200_OK)
async def intake_direct_raw_email(
    payload: DirectEmailIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Directly ingests a raw email payload for immediate testing.
    Runs extraction, deduplication, fuzzy matching, and staging/embedding logic synchronously.
    """
    # Fallback default values for test payloads
    now = datetime.now(timezone.utc)
    conv_id = payload.conversation_id or f"test-conv-{uuid.uuid4().hex[:8]}"
    msg_id = payload.message_id or f"test-msg-{uuid.uuid4().hex[:8]}"
    received_at = payload.received_at or now

    # Construct standard EmailPayload
    email_item = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=received_at,
        subject=payload.subject,
        body=payload.body,
    )

    # Initialize a temporary tracking task
    task_id = task_tracker.create_task(total_emails=1)

    # Execute processing pipeline directly
    await process_email_batch_sequential(
        db=db,
        emails=[email_item],
        task_id=task_id,
    )

    # Fetch processing status details
    task_summary = task_tracker.get_task(task_id)

    return {
        "status": "success",
        "message": "Direct email processed successfully.",
        "task_id": task_id,
        "details": task_summary,
    }