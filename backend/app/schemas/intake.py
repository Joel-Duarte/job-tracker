from typing import List, Optional
from pydantic import BaseModel, Field


class EmailPayload(BaseModel):
    conversation_id: str = Field(description="Unique email thread or conversation ID")
    received_at: str = Field(description="ISO timestamp of email receipt")
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