from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# --- Nested Response Schemas ---


class CompanySummary(BaseModel):
    id: int
    name: str
    domain: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EventSummary(BaseModel):
    id: int
    email_event_type: str
    email_subject: str | None = None
    email_action_required: bool
    email_action: str | None = None
    email_received_at: datetime | None = None
    raw_payload: dict | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Main Application Response Schemas ---


class ApplicationListItem(BaseModel):
    id: int
    company: CompanySummary
    position: str | None = None
    status: str
    application_date: datetime | None = None
    last_activity_at: datetime | None = None
    has_action_required: bool = False
    has_interview_guide: bool = False
    match_score: int | None = None
    match_analysis_payload: dict[str, Any] | None = None
    latest_event: EventSummary | None = None
    nearest_due_date: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class JobPostingDetail(BaseModel):
    id: int
    title: str | None = None
    description_markdown: str | None = None
    location: str | None = None
    work_model: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = "USD"
    required_skills: list[str] | None = []
    source_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ActionItemDetail(BaseModel):
    id: int
    title: str
    status: str
    urgency: str | None = "MEDIUM"
    due_date: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationEventDetail(BaseModel):
    id: int
    email_message_id: str | None = None
    email_conversation_id: str | None = None
    email_sender: str | None = None
    email_sender_name: str | None = None
    email_subject: str | None = None
    email_received_at: datetime | None = None
    email_event_type: str
    email_status_after_event: str | None = None
    email_summary: str | None = None
    email_action_required: bool = False
    email_action: str | None = None
    email_raw_body: str | None = None
    raw_payload: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    items: list[ApplicationListItem]
    total: int
    limit: int
    offset: int


class ApplicationDetailResponse(ApplicationListItem):
    external_job_id: str | None = None
    job_url: str | None = None
    application_key: str | None = None
    interview_guide_html: str | None = None
    interview_guide_language: str | None = "en"
    interview_guide_generated_at: datetime | None = None
    interview_guide_preferences: dict | None = None
    created_at: datetime
    updated_at: datetime
    events: list[ApplicationEventDetail] = []
    job_posting: JobPostingDetail | None = None
    action_items: list[ActionItemDetail] = []


class GenerateInterviewGuideRequest(BaseModel):
    language: str = Field(
        "en", description="Output language code e.g. en, pt, es, de, fr, it, nl"
    )
    selected_sections: list[str] = Field(
        default_factory=lambda: [
            "role_company_brief",
            "strategic_fit_pitch",
            "star_stories",
            "question_defenses",
            "interviewer_questions",
            "prep_checklist",
            "culture_tech_brief",
        ],
        description="Target sections to generate in the guide",
    )
    recursion_limit: int = Field(
        25, ge=5, le=100, description="LangGraph execution recursion limit"
    )


# --- Query Filter Schema ---


class ApplicationFilterParams(BaseModel):
    q: str | None = Field(None, description="Search term for position or company name")
    status: str | None = Field(
        None, description="Filter by application status (e.g., APPLIED, INTERVIEW)"
    )
    action_required: bool | None = Field(
        None, description="Filter applications with pending action items"
    )
    company_id: int | None = Field(None, description="Filter by specific company ID")
    sort_by: str = Field(
        "last_activity_at",
        description="Sort field: last_activity_at, application_date, status",
    )
    order: str = Field("desc", description="Sort order: asc or desc")
    limit: int = Field(20, ge=1, le=100, description="Pagination limit")
    offset: int = Field(0, ge=0, description="Pagination offset")


class AllowedApplicationStatus(StrEnum):
    ASSESSMENT = "ASSESSMENT"
    APPLIED = "APPLIED"
    ONLINE_ASSESSMENT = "ONLINE_ASSESSMENT"
    TECHNICAL_INTERVIEW = "TECHNICAL_INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"


class ApplicationByStatusResult(BaseModel):
    application_id: int
    company: str
    position: str | None = None
    status: str
    application_updated: datetime
    event_count: int
    latest_email: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationTransitionRequest(BaseModel):
    status: AllowedApplicationStatus = Field(..., description="Target pipeline status")
    interview_stage: str | None = Field(
        None,
        description="Specific interview phase e.g. Screening, Take-Home, System Design, Final Round",
    )
    scheduled_at: datetime | None = Field(
        None, description="Interview scheduled date & time"
    )
    offered_salary: float | None = Field(None, description="Offered compensation")
    currency: str | None = Field(
        "USD", description="Currency code for offered compensation"
    )
    offer_received_date: date | None = Field(
        None, description="Date offer package was received"
    )
    decision_deadline: date | None = Field(
        None, description="Decision deadline date to respond/accept offer"
    )
    rejection_date: date | None = Field(
        None, description="Date rejection notice was received"
    )
    rejection_reason: str | None = Field(None, description="Reason for rejection")
    notes: str | None = Field(
        None, description="Additional notes or context for transition"
    )


class ApplicationUpdate(BaseModel):
    position: str | None = Field(None, description="Updated job title/position name")
    status: str | None = Field(
        None,
        description="Updated status, e.g., APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED",
    )
    job_url: str | None = Field(None, description="URL to the job posting")
    external_job_id: str | None = Field(
        None, description="External reference ID for the listing"
    )
    company_id: int | None = Field(
        None, description="Reassign to another company ID if needed"
    )
    interview_stage: str | None = Field(None, description="Interview sub-stage")
    scheduled_at: datetime | None = Field(None, description="Scheduled interview time")
    offered_salary: float | None = Field(None, description="Offered compensation")
    currency: str | None = Field("USD", description="Currency code")
    offer_received_date: date | None = Field(None, description="Date offer received")
    decision_deadline: date | None = Field(None, description="Decision deadline")
    rejection_date: date | None = Field(None, description="Rejection date")
    rejection_reason: str | None = Field(None, description="Rejection reason")
    notes: str | None = Field(None, description="Transition notes")
