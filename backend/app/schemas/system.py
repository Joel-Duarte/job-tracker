from datetime import datetime
from pydantic import BaseModel, Field


class BadgeCountsResponse(BaseModel):
    staging_count: int = Field(
        default=0,
        description="Number of unresolved items in the staging queue",
    )
    pending_action_items_count: int = Field(
        default=0,
        description="Number of pending action items requiring candidate attention",
    )
    active_queue_tasks_count: int = Field(
        default=0,
        description="Number of actively running background intake/evaluation tasks",
    )
    total_applications_count: int = Field(
        default=0,
        description="Total number of applications in the system",
    )
    latest_activity_at: datetime | None = Field(
        default=None,
        description="Timestamp of the most recent application activity for cache invalidation",
    )
