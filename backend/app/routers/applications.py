from fastapi import APIRouter

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("")
async def list_applications():
    """Lists applications with optional filtering, pagination, and sorting."""
    pass


@router.get("/{application_id}")
async def get_application(application_id: int):
    """Retrieves detailed info for a single application."""
    pass


@router.get("/{application_id}/history")
async def get_application_history(application_id: int):
    """Retrieves status history timeline for an application."""
    pass


@router.patch("/{application_id}")
async def update_application(application_id: int):
    """Updates fields on a specific application record."""
    pass