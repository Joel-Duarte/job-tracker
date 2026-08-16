from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ActionItemCreate(BaseModel):
    application_id: Optional[int] = Field(None, description="Associated job application ID")
    title: str = Field(..., min_length=1, max_length=500, description="Task title / action description")
    due_date: Optional[datetime] = Field(None, description="Due date and time for the task")
    urgency: Optional[str] = Field("MEDIUM", description="Urgency level: HIGH, MEDIUM, LOW")
    status: Optional[str] = Field("PENDING", description="Task status: PENDING, COMPLETED, DISMISSED")
    action_url: Optional[str] = Field(None, description="Optional direct link related to the task")


class ActionItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    due_date: Optional[datetime] = None
    urgency: Optional[str] = Field(None, description="HIGH, MEDIUM, LOW")
    status: Optional[str] = Field(None, description="PENDING, COMPLETED, DISMISSED")
    action_url: Optional[str] = None


class UrgencyOverrideUpdate(BaseModel):
    manual_urgency: Optional[str] = Field(None, description="HIGH, MEDIUM, LOW, or null to reset to auto")


class ActionItemResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    event_id: Optional[int] = None
    title: str
    due_date: Optional[datetime] = None
    status: str
    action_url: Optional[str] = None
    urgency: str
    manual_urgency_override: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Joined application metadata
    company_name: Optional[str] = None
    position: Optional[str] = None
    application_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActionItemListResponse(BaseModel):
    items: List[ActionItemResponse]
    total: int
    pending_count: int
    high_urgency_count: int
    completed_count: int
