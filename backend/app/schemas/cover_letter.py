from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CoverLetterGenerateRequest(BaseModel):
    custom_instructions: str | None = Field(
        default=None,
        description="Optional custom instructions or specific points to emphasize.",
    )
    tone: str | None = Field(
        default=None,
        description="Optional tone override (e.g., professional, conversational, enthusiastic).",
    )


class CoverLetterUpdateRequest(BaseModel):
    content: str = Field(
        ...,
        description="Updated cover letter markdown text content.",
    )


class CoverLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: int
    cover_letter_markdown: str | None = Field(
        default=None,
        description="Markdown content of the cover letter.",
    )
    content: str | None = Field(
        default=None,
        description="Alias for cover_letter_markdown content.",
    )
    cover_letter_status: str = Field(
        default="PENDING",
        description="Status: PENDING, GENERATING, COMPLETED, FAILED, or SKIPPED",
    )
    status: str = Field(
        default="PENDING",
        description="Alias for cover_letter_status",
    )
    highlighted_skills: list[str] = Field(
        default_factory=list,
        description="Key candidate skills highlighted in the cover letter.",
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None
