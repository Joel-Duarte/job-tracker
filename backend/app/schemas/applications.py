from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    has_cover_letter: bool = False
    cover_letter_status: str | None = None
    match_score: int | None = None
    match_analysis_payload: dict[str, Any] | None = None
    latest_event: EventSummary | None = None
    nearest_due_date: datetime | None = None
    scheduled_interview_at: datetime | None = None
    location: str | None = None
    work_model: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = "USD"

    model_config = ConfigDict(from_attributes=True)


class JobPostingDetail(BaseModel):
    id: int
    title: str | None = None
    description_markdown: str | None = None
    location: str | None = None
    work_model: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = "USD"
    required_skills: list[str] | None = []
    source_url: str | None = None
    structured_spec: dict[str, Any] | None = None

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
    cover_letter_text: str | None = None
    cover_letter_status: str | None = None
    cover_letter_generated_at: datetime | None = None
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
    HIRED = "HIRED"
    ARCHIVED = "ARCHIVED"
    WITHDRAWN = "WITHDRAWN"


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

    @field_validator(
        "offer_received_date", "decision_deadline", "rejection_date", mode="before"
    )
    @classmethod
    def coerce_date(cls, v: Any) -> date | None:
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            if "T" in v:
                v = v.split("T")[0]
            try:
                return date.fromisoformat(v)
            except ValueError:
                pass
        return v


class ApplicationUpdate(BaseModel):
    position: str | None = Field(None, description="Updated job title/position name")
    company_name: str | None = Field(None, description="Updated company name")
    company_domain: str | None = Field(
        None, description="Updated company website or domain"
    )
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
    salary_min: float | None = Field(None, description="Minimum compensation/salary")
    salary_max: float | None = Field(None, description="Maximum compensation/salary")
    currency: str | None = Field(None, description="Currency code")
    location: str | None = Field(None, description="Job location (city/country/remote)")
    work_model: str | None = Field(
        None, description="Work model (e.g. Remote, Hybrid, On-site)"
    )
    offer_received_date: date | None = Field(None, description="Date offer received")
    decision_deadline: date | None = Field(None, description="Decision deadline")
    rejection_date: date | None = Field(None, description="Rejection date")
    rejection_reason: str | None = Field(None, description="Rejection reason")
    notes: str | None = Field(None, description="Transition notes")


class BulkTransitionRequest(BaseModel):
    target_status: AllowedApplicationStatus = Field(
        ..., description="Status to set on matched applications"
    )
    from_statuses: list[AllowedApplicationStatus] = Field(
        ...,
        description="Only transition applications currently in one of these statuses",
    )
    exclude_ids: list[int] = Field(
        default_factory=list,
        description="Application IDs to skip even if they match from_statuses",
    )
    notes: str | None = Field(None, description="Note appended to each timeline event")


class BulkTransitionResult(BaseModel):
    updated_count: int
    updated_ids: list[int]


# --- Cover Letter Schemas ---


class CoverLetterResponse(BaseModel):
    application_id: int
    cover_letter_text: str | None = None
    cover_letter_status: str | None = None
    cover_letter_generated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CoverLetterUpdateRequest(BaseModel):
    cover_letter_text: str | None = Field(
        None, description="Updated cover letter content"
    )
    cover_letter_status: str | None = Field(
        None, description="Updated cover letter status e.g. DRAFTED, GENERATED"
    )


class GenerateCoverLetterRequest(BaseModel):
    tone: str | None = Field(
        "professional",
        description="Desired tone e.g. professional, enthusiastic, concise, executive, technical",
    )
    length: str | None = Field(
        "standard",
        description="Desired length constraint e.g. concise (~150 words), standard (~300 words), detailed (~450 words)",
    )
    custom_instructions: str | None = Field(
        None, description="Optional custom instructions to guide cover letter drafting"
    )
