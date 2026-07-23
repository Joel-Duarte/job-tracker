from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# --- Nested Response Schemas ---

class CompanySummary(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    id: int
    email_event_type: str
    email_subject: Optional[str] = None
    email_action_required: bool
    email_action: Optional[str] = None
    email_received_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Main Application Response Schemas ---

class ApplicationListItem(BaseModel):
    id: int
    company: CompanySummary
    position: Optional[str] = None
    status: str
    application_date: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    has_action_required: bool = False
    latest_event: Optional[EventSummary] = None

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    items: List[ApplicationListItem]
    total: int
    limit: int
    offset: int


class ApplicationDetailResponse(ApplicationListItem):
    external_job_id: Optional[str] = None
    job_url: Optional[str] = None
    application_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StatusHistoryItem(BaseModel):
    id: int
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True


# --- Query Filter Schema ---

class ApplicationFilterParams(BaseModel):
    q: Optional[str] = Field(None, description="Search term for position or company name")
    status: Optional[str] = Field(None, description="Filter by application status (e.g., APPLIED, INTERVIEW)")
    action_required: Optional[bool] = Field(None, description="Filter applications with pending action items")
    company_id: Optional[int] = Field(None, description="Filter by specific company ID")
    sort_by: str = Field("last_activity_at", description="Sort field: last_activity_at, application_date, status")
    order: str = Field("desc", description="Sort order: asc or desc")
    limit: int = Field(20, ge=1, le=100, description="Pagination limit")
    offset: int = Field(0, ge=0, description="Pagination offset")

class ApplicationEventDetail(BaseModel):
    id: int
    email_message_id: Optional[str] = None
    email_conversation_id: Optional[str] = None
    email_sender: Optional[str] = None
    email_sender_name: Optional[str] = None
    email_subject: Optional[str] = None
    email_received_at: Optional[datetime] = None
    email_event_type: str
    email_status_after_event: Optional[str] = None
    email_summary: Optional[str] = None
    email_action_required: bool = False
    email_action: Optional[str] = None
    email_raw_body: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True