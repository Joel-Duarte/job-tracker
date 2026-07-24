from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

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

    extracted_data: ExtractedEmailInfo = Field(
        ..., description="The structured data extracted by the LLM"
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
    """Payload for user manual resolution/override of a staged email."""

    application_id: Optional[int] = Field(
        default=None,
        description="Optional ID of an existing application to explicitly link this event to.",
    )
    company_name: str = Field(
        ..., description="Corrected or confirmed company name."
    )
    position: str = Field(
        ..., description="Corrected or confirmed position title."
    )
    status: Optional[str] = Field(
        default="APPLIED",
        description="Normalized application status: 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED'.",
    )
    event_type: Optional[str] = Field(
        default="UPDATED",
        description="Specific event type: 'APPLICATION_CONFIRMATION', 'INTERVIEW_INVITE', 'REJECTION', 'OFFER_LETTER', etc.",
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


class StagingPaginationResponse(BaseModel):
    """Paginated wrapper for staging list endpoint."""

    total: int
    items: list[StagingItemRead]