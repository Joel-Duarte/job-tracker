from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CompanyApplicationItem(BaseModel):
    id: int
    position: str | None = None
    status: str
    applied_at: datetime | None = None
    created_at: datetime | None = None
    latest_event_at: datetime | None = None
    job_url: str | None = None
    is_assessment: bool = False

    model_config = ConfigDict(from_attributes=True)


class CompanyRead(BaseModel):
    id: int
    name: str
    name_normalized: str
    domain: str | None = None
    rating: int | None = None
    notes: str | None = None
    pros: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    company_research: dict[str, Any] | None = None
    researched_at: datetime | None = None
    research_status: str = "NONE"
    about_url: str | None = None
    applications_count: int = 0
    active_applications_count: int = 0
    last_applied_at: datetime | None = None
    applications: list[CompanyApplicationItem] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    about_url: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    pros: list[str] | None = None
    red_flags: list[str] | None = None
    company_research: dict[str, Any] | None = None
    research_status: str | None = None


class CompanyMergeRequest(BaseModel):
    source_company_id: int | None = Field(
        None, description="ID of single company to be merged and deleted (legacy)"
    )
    source_company_ids: list[int] = Field(
        default_factory=list,
        description="List of company IDs to be merged and deleted",
    )
    target_company_id: int = Field(
        ..., description="ID of primary canonical company to retain"
    )
