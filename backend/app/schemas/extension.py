from typing import Any, Optional
from pydantic import BaseModel, Field


class ClipUrlRequest(BaseModel):
    url: str = Field(..., description="Active job posting URL to clip and scrape")
    notes: Optional[str] = Field(default=None, description="Optional user notes")
    raw_html: Optional[str] = Field(
        default=None, description="Optional pre-captured HTML from DOM"
    )


class ClipJobRequest(BaseModel):
    company: str = Field(
        ..., min_length=1, description="Company name captured from page"
    )
    position: str = Field(..., min_length=1, description="Job title captured from page")
    url: Optional[str] = Field(default=None, description="URL of the job posting")
    description: Optional[str] = Field(
        default="", description="Captured job description text"
    )
    external_job_id: Optional[str] = Field(
        default=None, description="Requisition or Job ID if found"
    )
    status: Optional[str] = Field(
        default="APPLIED", description="Application status (e.g. APPLIED, BOOKMARKED)"
    )
    location: Optional[str] = Field(
        default=None, description="Job location (Remote, City, etc.)"
    )
    salary: Optional[str] = Field(default=None, description="Salary range if present")
    notes: Optional[str] = Field(default=None, description="User notes or comments")


class ExtensionClipResponse(BaseModel):
    status: str = Field(description="Clip status: success, staged, error")
    application_id: Optional[int] = Field(
        default=None, description="Created or updated application ID"
    )
    company: Optional[str] = None
    position: Optional[str] = None
    event_id: Optional[int] = None
    staging_item_id: Optional[int] = None
    message: str = Field(default="")
    details: Optional[dict[str, Any]] = None
