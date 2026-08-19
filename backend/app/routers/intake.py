import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_admin_access
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
)
from app.models.email_accounts import EmailAccountModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.processed_email import ProcessedEmailModel
from app.schemas.intake import (
    AssessJobRequest,
    BulkTaskActionRequest,
    BulkTaskActionResult,
    ConfirmAssessmentRequest,
    DirectEmailIntakeRequest,
    EnqueueAssessmentRequest,
    IntakeEvaluationTaskResponse,
    IntakeResultResponse,
    PasteIntakeRequest,
)
from app.schemas.llm import JobAssessmentResult
from app.services.intake_service import IntakeService
from app.services.task_tracker import task_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["Intake"])


@router.get("/extension-config")
async def get_extension_config(request: Request):
    """Programmatically returns the exact exposed backend endpoint URL for browser extensions."""
    if settings.PUBLIC_API_URL:
        base_url = settings.PUBLIC_API_URL.rstrip("/")
    else:
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        forwarded_host = (
            request.headers.get("x-forwarded-host")
            or request.headers.get("host")
            or f"{request.url.hostname}:{request.url.port}"
        )
        base_url = f"{forwarded_proto}://{forwarded_host}"

    return {
        "url_endpoint": f"{base_url}/api/v1/intake/url",
        "jd_endpoint": f"{base_url}/api/v1/intake/jd",
        "extension_ingest_url": f"{base_url}/api/v1/intake/assess-job",
        "api_base_url": f"{base_url}/api/v1",
    }


class ExtensionUrlDirectPayload(BaseModel):
    type: str | None = "URL_DIRECT_SEND"
    url: str
    title: str | None = None
    timestamp: str | None = None


@router.post("/url", status_code=status.HTTP_200_OK)
async def intake_extension_url(
    payload: ExtensionUrlDirectPayload,
    db: AsyncSession = Depends(get_db),
):
    """Receives URL directly from browser extension send-url button and triggers AI assessment with fallback to Staging."""
    return await IntakeService.intake_extension_url(
        url=payload.url, title=payload.title, db=db
    )


@router.post("/jd", response_model=JobAssessmentResult, status_code=status.HTTP_200_OK)
async def intake_extension_jd_elements(
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> JobAssessmentResult:
    """Receives selected DOM elements / group cards from browser extension, extracts text, and triggers AI assessment."""
    from app.routers.extension import _extract_text_from_html

    def _extract_all_text(data) -> list[str]:
        snippets = []
        if isinstance(data, dict):
            if data.get("title") and data.get("title") != "New Group":
                snippets.append(str(data["title"]))
            if data.get("text"):
                snippets.append(str(data["text"]))
            if data.get("html"):
                snippets.append(_extract_text_from_html(str(data["html"])))
            if data.get("children") and isinstance(data["children"], list):
                for child in data["children"]:
                    snippets.extend(_extract_all_text(child))
            if data.get("payload"):
                snippets.extend(_extract_all_text(data["payload"]))
        elif isinstance(data, list):
            for item in data:
                snippets.extend(_extract_all_text(item))
        elif isinstance(data, str):
            snippets.append(data)
        return snippets

    extracted_lines = _extract_all_text(payload)
    combined_text = "\n".join(
        [line.strip() for line in extracted_lines if line.strip()]
    )

    if not combined_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text or HTML content found in the extension selection payload.",
        )

    assess_req = AssessJobRequest(text=combined_text)
    return await IntakeService.assess_job_lead(assess_req, db=db)


class SyncFolderRequest(BaseModel):
    account_id: int = Field(
        description="ID of the configured EmailAccountModel to sync"
    )
    folder: str | None = Field(default=None)
    since_date: str | None = Field(default=None)
    keyword_filter: list[str] = Field(
        default_factory=list,
        description="Extra keywords merged with built-in job keywords for subject/body pre-filter.",
    )


class TaskResponse(BaseModel):
    task_id: str
    message: str
    scanned_count: int = 0
    matched_count: int = 0
    skipped_duplicates: int = 0
    filtered_out_count: int = 0


@router.post(
    "/paste", response_model=IntakeResultResponse, status_code=status.HTTP_200_OK
)
async def intake_pasted_text(
    payload: PasteIntakeRequest,
    db: AsyncSession = Depends(get_db),
) -> IntakeResultResponse:
    """Ingests raw pasted email text, thread, or job communication directly."""
    return await IntakeService.intake_pasted_text(payload=payload, db=db)


@router.post(
    "/upload", response_model=list[IntakeResultResponse], status_code=status.HTTP_200_OK
)
async def intake_uploaded_files(
    files: list[UploadFile] = File(
        ..., description="Uploaded .eml, .msg, or .txt files"
    ),
    db: AsyncSession = Depends(get_db),
) -> list[IntakeResultResponse]:
    """Ingests drag-and-drop uploaded email files (.eml, .msg, .txt)."""
    return await IntakeService.intake_uploaded_files(files=files, db=db)


@router.post(
    "/assess-job", response_model=JobAssessmentResult, status_code=status.HTTP_200_OK
)
async def assess_job_lead(
    payload: AssessJobRequest,
    db: AsyncSession = Depends(get_db),
) -> JobAssessmentResult:
    """Pre-screens a job lead (via URL or pasted JD text) using AI assessment."""
    return await IntakeService.assess_job_lead(payload=payload, db=db)


@router.post(
    "/confirm-assessment",
    response_model=IntakeResultResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_job_assessment(
    payload: ConfirmAssessmentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IntakeResultResponse:
    """Commits an assessed job lead to the application pipeline in ASSESSMENT or APPLIED status."""
    return await IntakeService.confirm_job_assessment(
        payload=payload, background_tasks=background_tasks, db=db
    )


@router.post(
    "/sync-account",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_access)],
)
async def sync_email_account(
    payload: SyncFolderRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Triggers asynchronous email sync for a date window with keyword pre-filtering."""
    res = await IntakeService.sync_email_account(
        account_id=payload.account_id,
        folder=payload.folder,
        since_date=payload.since_date,
        keyword_filter=payload.keyword_filter,
        background_tasks=background_tasks,
        db=db,
    )
    return TaskResponse(**res)


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


@router.post(
    "/test-direct",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_access)],
)
async def intake_direct_raw_email(
    payload: DirectEmailIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Directly ingests a raw email payload for immediate testing."""
    return await IntakeService.intake_direct_raw_email(payload=payload, db=db)


@router.post(
    "/enqueue-assessment",
    response_model=IntakeEvaluationTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_job_assessment(
    payload: EnqueueAssessmentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IntakeEvaluationTaskResponse:
    """Enqueues a job lead evaluation task into PostgreSQL for continuous intake UX."""
    return await IntakeService.enqueue_job_assessment(
        payload=payload, background_tasks=background_tasks, db=db
    )


@router.get(
    "/evaluations",
    response_model=list[IntakeEvaluationTaskResponse],
    status_code=status.HTTP_200_OK,
)
async def list_evaluation_tasks(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[IntakeEvaluationTaskResponse]:
    """Retrieves all queued, processing, and recent evaluation tasks from PostgreSQL."""
    return await IntakeService.list_evaluation_tasks(db=db, limit=limit)


@router.delete(
    "/evaluations/{task_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_access)],
)
async def delete_evaluation_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Cancels an ongoing evaluation or dismisses a completed/failed evaluation task."""
    return await IntakeService.delete_evaluation_task(task_id=task_id, db=db)


@router.post(
    "/evaluations/clear-completed",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_access)],
)
async def clear_completed_evaluations(
    db: AsyncSession = Depends(get_db),
):
    """Clears all completed or failed evaluation tasks from the queue history."""
    return await IntakeService.clear_completed_evaluations(db=db)


@router.post(
    "/evaluations/{task_id}/retry",
    response_model=IntakeEvaluationTaskResponse,
    status_code=status.HTTP_200_OK,
)
async def retry_evaluation_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> IntakeEvaluationTaskResponse:
    """Retries a failed or cancelled evaluation task."""
    return await IntakeService.retry_evaluation_task(
        task_id=task_id, background_tasks=background_tasks, db=db
    )


@router.post(
    "/evaluations/bulk-retry",
    response_model=BulkTaskActionResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_access)],
)
async def bulk_retry_evaluation_tasks(
    payload: BulkTaskActionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BulkTaskActionResult:
    """Bulk retries AI queue evaluation tasks."""
    return await IntakeService.bulk_retry_evaluation_tasks(
        payload=payload, background_tasks=background_tasks, db=db
    )


@router.post(
    "/evaluations/bulk-delete",
    response_model=BulkTaskActionResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_access)],
)
async def bulk_delete_evaluation_tasks(
    payload: BulkTaskActionRequest,
    db: AsyncSession = Depends(get_db),
) -> BulkTaskActionResult:
    """Bulk deletes AI queue evaluation tasks from the database."""
    return await IntakeService.bulk_delete_evaluation_tasks(payload=payload, db=db)
