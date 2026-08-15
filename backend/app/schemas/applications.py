from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

# --- Nested Response Schemas ---

class CompanySummary(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EventSummary(BaseModel):
    id: int
    email_event_type: str
    email_subject: Optional[str] = None
    email_action_required: bool
    email_action: Optional[str] = None
    email_received_at: Optional[datetime] = None
    raw_payload: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


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
    nearest_due_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobPostingDetail(BaseModel):
    id: int
    title: Optional[str] = None
    description_markdown: Optional[str] = None
    location: Optional[str] = None
    work_model: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = "USD"
    required_skills: Optional[List[str]] = []
    source_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ActionItemDetail(BaseModel):
    id: int
    title: str
    status: str
    urgency: Optional[str] = "MEDIUM"
    due_date: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    raw_payload: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    events: List[ApplicationEventDetail] = []
    job_posting: Optional[JobPostingDetail] = None
    action_items: List[ActionItemDetail] = []


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


class AllowedApplicationStatus(str, Enum):
    ASSESSMENT = "ASSESSMENT"
    APPLIED = "APPLIED"
    ONLINE_ASSESSMENT = "ONLINE_ASSESSMENT"
    TECHNICAL_INTERVIEW = "TECHNICAL_INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"


class ApplicationByStatusResult(BaseModel):
    application_id: int
    company: str
    position: Optional[str] = None
    status: str
    application_updated: datetime
    event_count: int
    latest_email: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationTransitionRequest(BaseModel):
    status: AllowedApplicationStatus = Field(..., description="Target pipeline status")
    interview_stage: Optional[str] = Field(None, description="Specific interview phase e.g. Screening, Take-Home, System Design, Final Round")
    scheduled_at: Optional[datetime] = Field(None, description="Interview scheduled date & time")
    offered_salary: Optional[float] = Field(None, description="Offered compensation")
    currency: Optional[str] = Field("USD", description="Currency code for offered compensation")
    offer_received_date: Optional[date] = Field(None, description="Date offer package was received")
    decision_deadline: Optional[date] = Field(None, description="Decision deadline date to respond/accept offer")
    rejection_date: Optional[date] = Field(None, description="Date rejection notice was received")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")
    notes: Optional[str] = Field(None, description="Additional notes or context for transition")


class ApplicationUpdate(BaseModel):
    position: Optional[str] = Field(None, description="Updated job title/position name")
    status: Optional[str] = Field(None, description="Updated status, e.g., APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED")
    job_url: Optional[str] = Field(None, description="URL to the job posting")
    external_job_id: Optional[str] = Field(None, description="External reference ID for the listing")
    company_id: Optional[int] = Field(None, description="Reassign to another company ID if needed")
    interview_stage: Optional[str] = Field(None, description="Interview sub-stage")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled interview time")
    offered_salary: Optional[float] = Field(None, description="Offered compensation")
    currency: Optional[str] = Field("USD", description="Currency code")
    offer_received_date: Optional[date] = Field(None, description="Date offer received")
    decision_deadline: Optional[date] = Field(None, description="Decision deadline")
    rejection_date: Optional[date] = Field(None, description="Rejection date")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    notes: Optional[str] = Field(None, description="Transition notes")