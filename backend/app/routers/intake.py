from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Optional
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.models.email_accounts import EmailAccountModel
from app.schemas.intake import (
    DirectEmailIntakeRequest,
    EmailBatchIntakeRequest,
    EmailPayload,
    IntakeResultResponse,
    PasteIntakeRequest,
)
from app.services.email_fetcher import fetch_emails_from_account
from app.services.file_parser import parse_uploaded_file
from app.services.intake import process_email_batch_sequential, process_single_email_graph
from app.services.task_tracker import task_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["Intake"])


class SyncFolderRequest(BaseModel):
    account_id: int = Field(description="ID of the configured EmailAccountModel to sync")
    folder: Optional[str] = Field(default=None)
    since_date: Optional[datetime] = Field(default=None)


class TaskResponse(BaseModel):
    task_id: str
    message: str


def _format_graph_result(result: dict[str, Any]) -> IntakeResultResponse:
    if result.get("is_duplicate"):
        return IntakeResultResponse(
            status="skipped",
            route="skip",
            is_duplicate=True,
            message="Email was already ingested previously (duplicate skipped).",
        )
    if result.get("staging_item_id"):
        return IntakeResultResponse(
            status="staged",
            route="staging",
            is_application=False,
            company=result.get("company_name"),
            position=result.get("position_name"),
            staging_item_id=result.get("staging_item_id"),
            extracted_data=result.get("extracted_data"),
            message="Email routed to human-in-the-loop staging queue for review.",
        )
    if result.get("is_application"):
        return IntakeResultResponse(
            status="success",
            route="commit",
            is_application=True,
            company=result.get("company_name"),
            position=result.get("position_name"),
            application_id=result.get("application_id"),
            event_id=result.get("event_id"),
            extracted_data=result.get("extracted_data"),
            message="Job application and timeline event committed successfully.",
        )
    return IntakeResultResponse(
        status="success",
        route="other_event",
        is_application=False,
        event_id=result.get("event_id"),
        extracted_data=result.get("extracted_data"),
        message="Non-application email event logged successfully.",
    )


@router.post("/paste", response_model=IntakeResultResponse, status_code=status.HTTP_200_OK)
async def intake_pasted_text(
    payload: PasteIntakeRequest,
    db: AsyncSession = Depends(get_db),
) -> IntakeResultResponse:
    """Ingests raw pasted email text, thread, or job communication directly."""
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pasted text content cannot be empty.",
        )

    # Derive subject from first non-empty line if not provided
    subject = payload.subject
    if not subject:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        subject = lines[0][:100] if lines else "Pasted Job Update"

    content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    msg_id = payload.message_id or f"paste-{content_hash}"
    conv_id = payload.conversation_id or f"conv-{content_hash}"
    received_at = payload.received_at or datetime.now(timezone.utc)

    email_payload = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=received_at,
        subject=subject,
        body=raw_text,
    )

    result = await process_single_email_graph(db, email_payload)
    return _format_graph_result(result)


@router.post("/upload", response_model=list[IntakeResultResponse], status_code=status.HTTP_200_OK)
async def intake_uploaded_files(
    files: list[UploadFile] = File(..., description="Uploaded .eml, .msg, or .txt files"),
    db: AsyncSession = Depends(get_db),
) -> list[IntakeResultResponse]:
    """Ingests drag-and-drop uploaded email files (.eml, .msg, .txt)."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload.",
        )

    results: list[IntakeResultResponse] = []

    for file in files:
        filename = file.filename or "uploaded_file.txt"
        try:
            content = await file.read()
            if not content:
                continue

            email_payload = parse_uploaded_file(filename, content)
            graph_res = await process_single_email_graph(db, email_payload)
            results.append(_format_graph_result(graph_res))
        except Exception as err:
            logger.error("Failed processing uploaded file '%s': %s", filename, err, exc_info=True)
            results.append(
                IntakeResultResponse(
                    status="error",
                    route="error",
                    message=f"Failed to parse file '{filename}': {str(err)}",
                )
            )

    return results


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
    raw_emails, next_cursor = await fetch_emails_from_account(account, since_date=payload.since_date)
    task_id = task_tracker.create_task(total_emails=len(raw_emails), account_id=payload.account_id)

    if next_cursor:
        account.sync_cursor = next_cursor
        account.last_synced_at = datetime.now(timezone.utc)
        await db.commit()

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
    now = datetime.now(timezone.utc)
    conv_id = payload.conversation_id or f"test-conv-{uuid.uuid4().hex[:8]}"
    msg_id = payload.message_id or f"test-msg-{uuid.uuid4().hex[:8]}"
    received_at = payload.received_at or now

    email_item = EmailPayload(
        conversation_id=conv_id,
        message_id=msg_id,
        received_at=received_at,
        subject=payload.subject,
        body=payload.body,
    )

    task_id = task_tracker.create_task(total_emails=1)

    await process_email_batch_sequential(
        db=db,
        emails=[email_item],
        task_id=task_id,
    )

    task_summary = task_tracker.get_task(task_id)

    return {
        "status": "success",
        "message": "Direct email processed successfully.",
        "task_id": task_id,
        "details": task_summary,
    }