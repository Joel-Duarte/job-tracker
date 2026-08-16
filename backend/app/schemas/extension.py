from typing import Any

from pydantic import BaseModel, Field


class ClipUrlRequest(BaseModel):
    url: str = Field(..., description="Active job posting URL to clip and scrape")
    notes: str | None = Field(default=None, description="Optional user notes")
    raw_html: str | None = Field(
        default=None, description="Optional pre-captured HTML from DOM"
    )


class ClipJobRequest(BaseModel):
    company: str = Field(
        ..., min_length=1, description="Company name captured from page"
    )
    position: str = Field(..., min_length=1, description="Job title captured from page")
    url: str | None = Field(default=None, description="URL of the job posting")
    description: str | None = Field(
        default="", description="Captured job description text"
    )
    external_job_id: str | None = Field(
        default=None, description="Requisition or Job ID if found"
    )
    status: str | None = Field(
        default="APPLIED", description="Application status (e.g. APPLIED, BOOKMARKED)"
    )
    location: str | None = Field(
        default=None, description="Job location (Remote, City, etc.)"
    )
    salary: str | None = Field(default=None, description="Salary range if present")
    notes: str | None = Field(default=None, description="User notes or comments")


class ExtensionClipResponse(BaseModel):
    status: str = Field(description="Clip status: success, staged, error")
    application_id: int | None = Field(
        default=None, description="Created or updated application ID"
    )
    company: str | None = None
    position: str | None = None
    event_id: int | None = None
    staging_item_id: int | None = None
    message: str = Field(default="")
    details: dict[str, Any] | None = None
