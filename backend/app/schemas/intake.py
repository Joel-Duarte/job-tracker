from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field



class ExtractedEmailInfo(BaseModel):
    """Structured extraction format returned by the LLM service."""
    company: Optional[str] = Field(
        default=None, 
        description="Name of the company (e.g., 'Stripe', 'Google'). None if not a job email."
    )
    position: Optional[str] = Field(
        default=None, 
        description="Job title/role (e.g., 'Senior Backend Engineer'). None if not present."
    )
    status: Optional[str] = Field(
        default=None, 
        description="Normalized application status: 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED'."
    )
    event_type: Optional[str] = Field(
        default=None, 
        description="Specific email event: 'APPLICATION_CONFIRMATION', 'INTERVIEW_INVITE', 'REJECTION', 'OFFER_LETTER'."
    )
    email_type: Optional[str] = Field(
        default="OTHER", 
        description="Category if not a specific job update (e.g., 'NEWSLETTER', 'JOB_ALERT', 'OTHER')."
    )
    external_job_id: Optional[str] = Field(
        default=None, 
        description="Job posting reference ID or req number if mentioned in email."
    )
    job_url: Optional[str] = Field(
        default=None, 
        description="Link to job description or application portal if found."
    )
    summary: str = Field(
        default="", 
        description="1-2 sentence summary of what the email is about."
    )
    action_required: bool = Field(
        default=False, 
        description="True if user needs to take action (e.g., schedule interview, fill out form)."
    )
    action: Optional[str] = Field(
        default=None, 
        description="Description of required action if action_required is True."
    )


class EmailPayload(BaseModel):
    conversation_id: str = Field(description="Unique email thread or conversation ID")
    message_id: Optional[str] = Field(default=None, description="Unique email message ID")
    received_at: datetime = Field(description="ISO timestamp of email receipt")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full text body of the email")


class EmailBatchIntakeRequest(BaseModel):
    emails: List[EmailPayload] = Field(..., min_length=1, description="List of emails to parse and process")


class EmailProcessingSummary(BaseModel):
    total_received: int
    applications_updated: int
    other_events_logged: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)


class DirectEmailIntakeRequest(BaseModel):
    subject: str = Field(..., description="Subject line of the email")
    body: str = Field(..., description="Raw text or HTML body of the email")
    sender: Optional[str] = Field(default=None, description="Sender email address")
    sender_name: Optional[str] = Field(default=None, description="Sender display name")
    conversation_id: Optional[str] = Field(
        default=None, 
        description="Optional conversation ID; if omitted, a mock UUID will be generated."
    )
    message_id: Optional[str] = Field(
        default=None, 
        description="Optional unique message ID; if omitted, a mock UUID will be generated."
    )
    received_at: Optional[datetime] = Field(
        default=None, 
        description="Timestamp of receipt; defaults to current time if omitted."
    )


class PasteIntakeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw pasted email text, thread, or job message")
    subject: Optional[str] = Field(default=None, description="Optional subject line override")
    sender: Optional[str] = Field(default=None, description="Optional sender email or name")
    received_at: Optional[datetime] = Field(default=None, description="Timestamp of receipt")
    conversation_id: Optional[str] = Field(default=None, description="Optional thread/conversation ID")
    message_id: Optional[str] = Field(default=None, description="Optional message ID")


class AssessJobRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Job description or requirements text")
    url: Optional[str] = Field(default=None, description="Job posting URL")
    raw_html: Optional[str] = Field(default=None, description="Optional raw HTML DOM captured by browser extension")


class ConfirmAssessmentRequest(BaseModel):
    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Position or title")
    status: str = Field(default="ASSESSMENT", description="Initial pipeline status: ASSESSMENT or APPLIED")
    job_url: Optional[str] = Field(default=None, description="Job URL")
    application_id: Optional[int] = Field(default=None, description="Optional target Application ID to update")
    force_new: Optional[bool] = Field(default=False, description="If True, creates a fresh Application record")
    description_markdown: Optional[str] = Field(default=None, description="Job description or AI assessment")
    salary_min: Optional[float] = Field(default=None)
    salary_max: Optional[float] = Field(default=None)
    currency: Optional[str] = Field(default="USD")
    location: Optional[str] = Field(default=None)
    work_model: Optional[str] = Field(default=None)
    required_skills: List[str] = Field(default_factory=list)
    match_analysis_payload: Optional[dict[str, Any]] = Field(default=None)


class IntakeResultResponse(BaseModel):
    status: str = Field(description="Status of the ingestion e.g. success, skipped, staged, error")
    route: str = Field(description="Pipeline route taken: commit, staging, other_event, skip")
    is_application: bool = Field(default=False)
    is_duplicate: bool = Field(default=False)
    company: Optional[str] = None
    position: Optional[str] = None
    application_id: Optional[int] = None
    staging_item_id: Optional[int] = None
    event_id: Optional[int] = None
    message: str = Field(default="")
    extracted_data: Optional[dict[str, Any]] = None


class EnqueueAssessmentRequest(BaseModel):
    url: Optional[str] = Field(default=None, description="Job URL")
    text: Optional[str] = Field(default=None, description="Pasted job description text")
    title_hint: Optional[str] = Field(default=None, description="Optional title or company hint")


class IntakeEvaluationTaskResponse(BaseModel):
    id: int
    task_type: str = "JOB_ASSESSMENT"
    job_url: Optional[str] = None
    raw_text: Optional[str] = None
    title_hint: str
    status: str
    stage: str
    error_message: Optional[str] = None
    result_json: Optional[dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)