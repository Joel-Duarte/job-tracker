from typing import Optional
from pydantic import BaseModel, Field


class EmailExtractionResult(BaseModel):
    email_type: str = Field(description="Type/category of the email")
    company: Optional[str] = Field(default=None, description="Company name if present")
    position: str = Field(description="Job position or title")
    external_job_id: Optional[str] = Field(default=None, description="External job/requisition ID")
    job_url: Optional[str] = Field(default=None, description="URL to the job listing")
    event_type: Optional[str] = Field(default=None, description="Event type, e.g., INTERVIEW_INVITE")
    status: Optional[str] = Field(default=None, description="Application status")
    action_required: bool = Field(description="Whether user action is required")
    action: Optional[str] = Field(default=None, description="Action details if required")
    summary: str = Field(description="Brief summary of the email body")


class ApplicationSummaryResult(BaseModel):
    snapshot: str = Field(description="Full text snapshot of application history")
    current_stage: str = Field(description="Current stage e.g., REJECTED, APPLIED")
    next_action: Optional[str] = Field(default=None, description="Next action item if any")