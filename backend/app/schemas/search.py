from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CompanySearchResult(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    applications_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchResult(BaseModel):
    id: int
    application_id: Optional[int] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    email_subject: Optional[str] = None
    email_summary: Optional[str] = None
    similarity_score: float  # e.g., 78.50
    received_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
