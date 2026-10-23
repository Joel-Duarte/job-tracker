from typing import Any, TypedDict


class JobTrackerState(TypedDict, total=False):
    user_created_lead: bool
    # Input data
    internet_message_id: str | None
    provider_message_id: str | None
    in_reply_to: str | None
    references: list[str]
    plain_body: str | None
    html_body: str | None
    calendar_events: list[dict[str, Any]]
    original_body: str
    message_id: str | None
    conversation_id: str | None
    sender: str | None
    sender_name: str | None
    subject: str
    body: str
    received_at: str | None

    # Processing metadata & flags
    task_id: int | None
    is_duplicate: bool
    is_application: bool
    error: str | None

    # Extraction output
    extracted_data: dict[str, Any] | None

    # Matching & Routing
    company_name: str | None
    position_name: str | None
    match_score: float
    company_id: int | None
    application_id: int | None
    match_reason: str | None
    route: str  # "commit" | "staging" | "skip" | "other_event"

    # Scraping & Enrichment (Phase 3 readiness)
    job_url: str | None
    scraped_spec: str | None

    # Database records generated
    staging_item_id: int | None
    event_id: int | None
    embedding_created: bool
    cover_letter_status: str | None
