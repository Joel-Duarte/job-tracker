from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OtherEventDetail(BaseModel):
    id: int
    email_message_id: Optional[str] = None
    email_conversation_id: Optional[str] = None
    email_sender: Optional[str] = None
    email_sender_name: Optional[str] = None
    email_subject: Optional[str] = None
    email_received_at: Optional[datetime] = None
    email_type: str
    company: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    action_required: bool = False
    action: Optional[str] = None
    summary: Optional[str] = None
    raw_body: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionItemSummary(BaseModel):
    id: int
    source: str  # "application_event" or "other_event"
    application_id: Optional[int] = None
    company_name: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    action: Optional[str] = None
    received_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ResolveActionRequest(BaseModel):
    action_required: bool = False
