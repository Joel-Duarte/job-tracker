from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanySearchResult(BaseModel):
    id: int
    name: str
    domain: str | None = None
    applications_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchResult(BaseModel):
    id: int
    application_id: int | None = None
    company_name: str | None = None
    position: str | None = None
    email_subject: str | None = None
    email_summary: str | None = None
    similarity_score: float  # e.g., 78.50
    received_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
