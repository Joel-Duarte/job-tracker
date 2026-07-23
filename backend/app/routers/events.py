from fastapi import APIRouter

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/applications/{application_id}")
async def list_application_events(application_id: int):
    """Lists all recruitment events tied to a specific application."""
    pass


@router.get("/action-required")
async def list_action_required_events():
    """Lists all pending action items across application events and other events."""
    pass


@router.get("/other")
async def list_other_events():
    """Lists non-application related email events."""
    pass


@router.patch("/{event_id}/action")
async def resolve_event_action(event_id: int):
    """Updates action status on a specific event."""
    pass