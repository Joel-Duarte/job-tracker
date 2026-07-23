from fastapi import APIRouter, status

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.post("/process/folder", status_code=status.HTTP_202_ACCEPTED)
async def process_folder_emails():
    """Triggers background processing of emails from a configured folder/directory."""
    pass


@router.post("/process/direct", status_code=status.HTTP_202_ACCEPTED)
async def process_direct_email():
    """Directly ingests and processes a single email payload."""
    pass


@router.get("/process/jobs/{job_id}")
async def get_processing_job_status(job_id: str):
    """Retrieves status of a background email processing job."""
    pass