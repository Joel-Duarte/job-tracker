from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractedEmailInfo(BaseModel):
    """Structured extraction format returned by the LLM service."""

    company: str | None = Field(
        default=None,
        description="Name of the company (e.g., 'Stripe', 'Google'). None if not a job email.",
    )
    position: str | None = Field(
        default=None,
        description="Job title/role (e.g., 'Senior Backend Engineer'). None if not present.",
    )
    status: str | None = Field(
        default=None,
        description="Normalized application status: 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED'.",
    )
    event_type: str | None = Field(
        default=None,
        description="Specific email event: 'APPLICATION_CONFIRMATION', 'INTERVIEW_INVITE', 'REJECTION', 'OFFER_LETTER'.",
    )
    email_type: str | None = Field(
        default="OTHER",
        description="Category if not a specific job update (e.g., 'NEWSLETTER', 'JOB_ALERT', 'OTHER').",
    )
    external_job_id: str | None = Field(
        default=None,
        description="Job posting reference ID or req number if mentioned in email.",
    )
    job_url: str | None = Field(
        default=None,
        description="Link to job description or application portal if found.",
    )
    summary: str = Field(
        default="", description="1-2 sentence summary of what the email is about."
    )
    action_required: bool = Field(
        default=False,
        description="True if user needs to take action (e.g., schedule interview, fill out form).",
    )
    action: str | None = Field(
        default=None,
        description="Description of required action if action_required is True.",
    )


class EmailPayload(BaseModel):
    conversation_id: str = Field(description="Unique email thread or conversation ID")
    message_id: str | None = Field(default=None, description="Unique email message ID")
    received_at: datetime = Field(description="ISO timestamp of email receipt")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full text body of the email")


class EmailBatchIntakeRequest(BaseModel):
    emails: list[EmailPayload] = Field(
        ..., min_length=1, description="List of emails to parse and process"
    )


class EmailProcessingSummary(BaseModel):
    total_received: int
    applications_updated: int
    other_events_logged: int
    failed_count: int
    errors: list[str] = Field(default_factory=list)


class DirectEmailIntakeRequest(BaseModel):
    subject: str = Field(..., description="Subject line of the email")
    body: str = Field(..., description="Raw text or HTML body of the email")
    sender: str | None = Field(default=None, description="Sender email address")
    sender_name: str | None = Field(default=None, description="Sender display name")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID; if omitted, a mock UUID will be generated.",
    )
    message_id: str | None = Field(
        default=None,
        description="Optional unique message ID; if omitted, a mock UUID will be generated.",
    )
    received_at: datetime | None = Field(
        default=None,
        description="Timestamp of receipt; defaults to current time if omitted.",
    )


class PasteIntakeRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, description="Raw pasted email text, thread, or job message"
    )
    subject: str | None = Field(
        default=None, description="Optional subject line override"
    )
    sender: str | None = Field(
        default=None, description="Optional sender email or name"
    )
    received_at: datetime | None = Field(
        default=None, description="Timestamp of receipt"
    )
    conversation_id: str | None = Field(
        default=None, description="Optional thread/conversation ID"
    )
    message_id: str | None = Field(default=None, description="Optional message ID")


class AssessJobRequest(BaseModel):
    text: str | None = Field(
        default=None, description="Job description or requirements text"
    )
    url: str | None = Field(default=None, description="Job posting URL")
    raw_html: str | None = Field(
        default=None, description="Optional raw HTML DOM captured by browser extension"
    )


class ConfirmAssessmentRequest(BaseModel):
    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Position or title")
    status: str = Field(
        default="ASSESSMENT",
        description="Initial pipeline status: ASSESSMENT or APPLIED",
    )
    job_url: str | None = Field(default=None, description="Job URL")
    application_id: int | None = Field(
        default=None, description="Optional target Application ID to update"
    )
    force_new: bool | None = Field(
        default=False, description="If True, creates a fresh Application record"
    )
    description_markdown: str | None = Field(
        default=None, description="Job description or AI assessment"
    )
    salary_min: float | None = Field(default=None)
    salary_max: float | None = Field(default=None)
    currency: str | None = Field(default="USD")
    location: str | None = Field(default=None)
    work_model: str | None = Field(default=None)
    required_skills: list[str] = Field(default_factory=list)
    match_analysis_payload: dict[str, Any] | None = Field(default=None)


class IntakeResultResponse(BaseModel):
    status: str = Field(
        description="Status of the ingestion e.g. success, skipped, staged, error"
    )
    route: str = Field(
        description="Pipeline route taken: commit, staging, other_event, skip"
    )
    is_application: bool = Field(default=False)
    is_duplicate: bool = Field(default=False)
    company: str | None = None
    position: str | None = None
    application_id: int | None = None
    staging_item_id: int | None = None
    event_id: int | None = None
    message: str = Field(default="")
    extracted_data: dict[str, Any] | None = None


class EnqueueAssessmentRequest(BaseModel):
    url: str | None = Field(default=None, description="Job URL")
    text: str | None = Field(default=None, description="Pasted job description text")
    title_hint: str | None = Field(
        default=None, description="Optional title or company hint"
    )


class IntakeEvaluationTaskResponse(BaseModel):
    id: int
    task_type: str = "JOB_ASSESSMENT"
    job_url: str | None = None
    raw_text: str | None = None
    title_hint: str
    status: str
    stage: str
    error_message: str | None = None
    result_json: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
