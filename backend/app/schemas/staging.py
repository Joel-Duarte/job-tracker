from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.intake import ExtractedEmailInfo


class StagingItemRead(BaseModel):
    """Schema for displaying an item in the staging queue."""

    id: int
    email_account_id: Optional[int] = None
    email_message_id: Optional[str] = None
    email_internet_message_id: Optional[str] = None
    email_conversation_id: Optional[str] = None
    email_sender: Optional[str] = None
    email_sender_name: Optional[str] = None
    email_subject: Optional[str] = None
    email_received_at: Optional[datetime] = None
    email_raw_body: Optional[str] = None

    extracted_data: Dict[str, Any] | ExtractedEmailInfo = Field(
        ..., description="The structured data extracted by the LLM or pre-screen assessment"
    )
    match_score: Optional[float] = Field(
        default=None, description="Confidence score from fuzzy matching (0.0 to 1.0)"
    )
    match_reason: Optional[str] = Field(
        default=None, description="Reason why the item was flagged/staged"
    )
    status: str = Field(
        default="PENDING",
        description="Current state in staging: 'PENDING', 'APPROVED', 'REJECTED', 'PROCESSED'",
    )

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StagingItemResolve(BaseModel):
    """Payload for user manual resolution/override of a staged email or job lead."""

    application_id: Optional[int] = Field(
        default=None,
        description="Optional ID of an existing application to explicitly link this event to.",
    )
    company_name: Optional[str] = Field(
        default=None, description="Corrected or confirmed company name."
    )
    company: Optional[str] = Field(
        default=None, description="Alternative field for company name."
    )
    position: str = Field(
        ..., description="Corrected or confirmed position title."
    )
    status: Optional[str] = Field(
        default="ASSESSMENT",
        description="Normalized application status: 'ASSESSMENT', 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED'.",
    )
    event_type: Optional[str] = Field(
        default="PRE_APPLICATION_ASSESSMENT",
        description="Specific event type: 'PRE_APPLICATION_ASSESSMENT', 'APPLICATION_CONFIRMATION', 'INTERVIEW_INVITE', 'REJECTION', 'OFFER_LETTER', etc.",
    )
    summary: Optional[str] = Field(
        default=None, description="Updated event summary text."
    )
    action_required: bool = Field(
        default=False, description="Flag indicating if action is required by the user."
    )
    action: Optional[str] = Field(
        default=None, description="Specific action details if required."
    )
    external_job_id: Optional[str] = Field(
        default=None, description="Job reference or requisition ID."
    )
    job_url: Optional[str] = Field(
        default=None, description="Link to application portal or job post."
    )
    create_new: Optional[bool] = Field(
        default=False,
        description="If True, creates a brand new Application record even if an existing application matches the company/position.",
    )
    description_markdown: Optional[str] = Field(default=None)
    salary_min: Optional[float] = Field(default=None)
    salary_max: Optional[float] = Field(default=None)
    currency: Optional[str] = Field(default="USD")
    location: Optional[str] = Field(default=None)
    work_model: Optional[str] = Field(default=None)
    required_skills: Optional[List[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_company_fields(self) -> "StagingItemResolve":
        if not self.company_name and self.company:
            self.company_name = self.company
        elif not self.company_name and not self.company:
            raise ValueError("Either company_name or company must be provided.")
        return self


class StagingPaginationResponse(BaseModel):
    """Paginated wrapper for staging list endpoint."""

    total: int
    items: list[StagingItemRead]