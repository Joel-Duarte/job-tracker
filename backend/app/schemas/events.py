from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OtherEventDetail(BaseModel):
    id: int
    email_message_id: str | None = None
    email_conversation_id: str | None = None
    email_sender: str | None = None
    email_sender_name: str | None = None
    email_subject: str | None = None
    email_received_at: datetime | None = None
    email_type: str
    company: str | None = None
    event_type: str | None = None
    status: str | None = None
    action_required: bool = False
    action: str | None = None
    summary: str | None = None
    raw_body: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionItemSummary(BaseModel):
    id: int
    source: str  # "application_event" or "other_event"
    application_id: int | None = None
    company_name: str | None = None
    subject: str | None = None
    sender: str | None = None
    action: str | None = None
    received_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ResolveActionRequest(BaseModel):
    action_required: bool = False
