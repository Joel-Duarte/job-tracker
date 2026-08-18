from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActionItemCreate(BaseModel):
    application_id: int | None = Field(
        None, description="Associated job application ID"
    )
    title: str = Field(
        ..., min_length=1, max_length=500, description="Task title / action description"
    )
    due_date: datetime | None = Field(
        None, description="Due date and time for the task"
    )
    urgency: str | None = Field(
        "MEDIUM", description="Urgency level: HIGH, MEDIUM, LOW"
    )
    status: str | None = Field(
        "PENDING", description="Task status: PENDING, COMPLETED, DISMISSED"
    )
    action_url: str | None = Field(
        None, description="Optional direct link related to the task"
    )


class ActionItemUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    due_date: datetime | None = None
    urgency: str | None = Field(None, description="HIGH, MEDIUM, LOW")
    status: str | None = Field(None, description="PENDING, COMPLETED, DISMISSED")
    action_url: str | None = None
    draft_email: str | None = None


class UrgencyOverrideUpdate(BaseModel):
    manual_urgency: str | None = Field(
        None, description="HIGH, MEDIUM, LOW, or null to reset to auto"
    )


class ActionItemResponse(BaseModel):
    id: int
    application_id: int | None = None
    event_id: int | None = None
    title: str
    due_date: datetime | None = None
    status: str
    action_url: str | None = None
    draft_email: str | None = None
    urgency: str
    manual_urgency_override: str | None = None
    created_at: datetime
    updated_at: datetime
    # Joined application metadata
    company_name: str | None = None
    position: str | None = None
    application_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ActionItemListResponse(BaseModel):
    items: list[ActionItemResponse]
    total: int
    pending_count: int
    high_urgency_count: int
    completed_count: int
