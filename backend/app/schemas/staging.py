from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.intake import ExtractedEmailInfo


class StagingItemRead(BaseModel):
    """Schema for displaying an item in the staging queue."""

    id: int
    email_account_id: int | None = None
    email_message_id: str | None = None
    email_internet_message_id: str | None = None
    email_conversation_id: str | None = None
    email_sender: str | None = None
    email_sender_name: str | None = None
    email_subject: str | None = None
    email_received_at: datetime | None = None
    email_raw_body: str | None = None

    extracted_data: dict[str, Any] | ExtractedEmailInfo = Field(
        ...,
        description="The structured data extracted by the LLM or pre-screen assessment",
    )
    match_score: float | None = Field(
        default=None, description="Confidence score from fuzzy matching (0.0 to 1.0)"
    )
    match_reason: str | None = Field(
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

    application_id: int | None = Field(
        default=None,
        description="Optional ID of an existing application to explicitly link this event to.",
    )
    company_name: str | None = Field(
        default=None, description="Corrected or confirmed company name."
    )
    company: str | None = Field(
        default=None, description="Alternative field for company name."
    )
    position: str = Field(..., description="Corrected or confirmed position title.")
    status: str | None = Field(
        default="APPLIED",
        description="Normalized application status: 'APPLIED', 'ONLINE_ASSESSMENT', 'TECHNICAL_INTERVIEW', 'OFFER', 'REJECTED'.",
    )
    event_type: str | None = Field(
        default="APPLICATION_CONFIRMATION",
        description="Specific event type: 'APPLICATION_CONFIRMATION', 'INTERVIEW_INVITATION', 'ONLINE_ASSESSMENT', 'REJECTION', 'OFFER_LETTER', etc.",
    )
    summary: str | None = Field(default=None, description="Updated event summary text.")
    action_required: bool = Field(
        default=False, description="Flag indicating if action is required by the user."
    )
    action: str | None = Field(
        default=None, description="Specific action details if required."
    )
    urgency: str | None = Field(
        default="MEDIUM",
        description="Action item urgency level: 'HIGH', 'MEDIUM', or 'LOW'.",
    )
    due_date: datetime | None = Field(
        default=None,
        description="Optional deadline or due date for the action item.",
    )
    external_job_id: str | None = Field(
        default=None, description="Job reference or requisition ID."
    )
    job_url: str | None = Field(
        default=None, description="Link to application portal or job post."
    )
    create_new: bool | None = Field(
        default=False,
        description="If True, creates a brand new Application record even if an existing application matches the company/position.",
    )
    description_markdown: str | None = Field(default=None)
    salary_min: float | None = Field(default=None)
    salary_max: float | None = Field(default=None)
    currency: str | None = Field(default="USD")
    location: str | None = Field(default=None)
    work_model: str | None = Field(default=None)
    required_skills: list[str] | None = Field(default_factory=list)

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


class StagingBulkDismissRequest(BaseModel):
    item_ids: list[int] | None = Field(
        default=None, description="List of specific staging item IDs to dismiss."
    )
    dismiss_all_pending: bool = Field(
        default=False,
        description="If True, dismisses all pending staging items matching filters.",
    )
    status_filter: str | None = Field(
        default="PENDING", description="Status filter when dismiss_all_pending is True."
    )
    search: str | None = Field(
        default=None, description="Search filter when dismiss_all_pending is True."
    )


class StagingBulkDismissResponse(BaseModel):
    dismissed_count: int
    message: str
