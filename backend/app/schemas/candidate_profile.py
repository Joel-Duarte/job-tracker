from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DomainExperienceItem(BaseModel):
    domain: str = Field(
        ...,
        description="Specialized domain area e.g. 'Backend Systems', 'Fintech', 'Cloud & DevOps'",
    )
    years: float = Field(
        default=1.0,
        ge=0.0,
        le=50.0,
        description="Estimated years of experience in this specific area",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this domain area is included in AI qualification matching",
    )


class SpokenLanguageItem(BaseModel):
    language: str = Field(
        ...,
        description="Natural/spoken language name e.g. 'English', 'German', 'French', 'Portuguese'",
    )
    proficiency: str = Field(
        default="Fluent",
        description="Proficiency level e.g. 'Native', 'Fluent', 'Intermediate', 'Basic', 'C1', 'B2'",
    )


class CVAnonymizationResult(BaseModel):
    anonymized_resume: str = Field(
        description="De-identified resume text with names, addresses, emails, and specific company names scrubbed, and dates converted to duration windows."
    )
    extracted_skills: list[str] = Field(
        default_factory=list,
        description="Canonical technical skills, libraries, frameworks, tools, and methodologies extracted from the CV.",
    )
    total_years_experience: float = Field(
        default=0.0,
        description="Calculated total cumulative professional experience in years.",
    )
    domain_expertise: list[str] = Field(
        default_factory=list,
        description="Industry domain tags (e.g. 'Fintech', 'Distributed Systems', 'Cloud Infrastructure', 'E-commerce').",
    )
    domain_breakdown: list[DomainExperienceItem] = Field(
        default_factory=list,
        description="Granular domain and specialization experience breakdown with estimated durations.",
    )
    core_competencies: list[str] = Field(
        default_factory=list,
        description="Top 4-6 standout professional strengths and core competencies.",
    )
    spoken_languages: list[SpokenLanguageItem] = Field(
        default_factory=list,
        description="Natural/spoken languages and proficiencies extracted from the CV (e.g. English - Native, German - B2).",
    )
    summary: str = Field(
        default="", description="High-level candidate executive overview."
    )


class CandidateCVSaveRequest(BaseModel):
    raw_text: str = Field(
        ..., min_length=20, description="Raw pasted resume or CV text"
    )


class CVParsedDocumentResponse(BaseModel):
    text: str = Field(description="Extracted plain text from uploaded document.")
    filename: str = Field(description="Name of uploaded document file.")


class CandidateCVUpdateRequest(BaseModel):
    anonymized_text: str | None = None
    extracted_skills: list[str] | None = None
    years_of_experience: float | None = None
    domain_expertise: list[str] | None = None
    domain_experience: list[DomainExperienceItem] | None = None
    core_competencies: list[str] | None = None
    spoken_languages: list[SpokenLanguageItem] | None = None
    summary: str | None = None


class CandidateCVResponse(BaseModel):
    id: int
    raw_text: str
    anonymized_text: str | None = None
    extracted_skills: list[str] = Field(default_factory=list)
    years_of_experience: float | None = None
    domain_expertise: list[str] = Field(default_factory=list)
    domain_experience: list[DomainExperienceItem] = Field(default_factory=list)
    core_competencies: list[str] = Field(default_factory=list)
    spoken_languages: list[SpokenLanguageItem] = Field(default_factory=list)
    summary: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CVTaskStatusResponse(BaseModel):
    task_id: int
    task_type: str = "CV_EXTRACTION"
    status: str
    stage: str
    error_message: str | None = None
    profile_id: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
