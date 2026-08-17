from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PortfolioProjectItem(BaseModel):
    title: str = Field(..., description="Name of the portfolio project")
    description: str = Field(..., description="Brief summary of the project and impact")
    link: str | None = Field(
        None, description="URL to the live project, repo, or case study"
    )
    skills: list[str] | None = Field(
        default_factory=list, description="Primary skills or tech stack used"
    )


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
    summary: str = Field(
        default="", description="High-level candidate executive overview."
    )


class CandidateCVSaveRequest(BaseModel):
    raw_text: str = Field(
        ..., min_length=20, description="Raw pasted resume or CV text"
    )


class CandidateCVUpdateRequest(BaseModel):
    anonymized_text: str | None = None
    extracted_skills: list[str] | None = None
    years_of_experience: float | None = None
    domain_expertise: list[str] | None = None
    domain_experience: list[DomainExperienceItem] | None = None
    core_competencies: list[str] | None = None
    portfolio_projects: list[PortfolioProjectItem] | None = None
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
    portfolio_projects: list[PortfolioProjectItem] = Field(default_factory=list)
    summary: str | None = None
    is_active: bool
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
