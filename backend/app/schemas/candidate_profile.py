from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CVAnonymizationResult(BaseModel):
    anonymized_resume: str = Field(
        description="De-identified resume text with names, addresses, emails, and specific company names scrubbed, and dates converted to duration windows."
    )
    extracted_skills: List[str] = Field(
        default_factory=list,
        description="Canonical technical skills, libraries, frameworks, tools, and methodologies extracted from the CV."
    )
    total_years_experience: float = Field(
        default=0.0,
        description="Calculated total cumulative professional experience in years."
    )
    domain_expertise: List[str] = Field(
        default_factory=list,
        description="Industry domain tags (e.g. 'Fintech', 'Distributed Systems', 'Cloud Infrastructure', 'E-commerce')."
    )
    summary: str = Field(
        default="",
        description="High-level candidate executive overview."
    )


class CandidateCVSaveRequest(BaseModel):
    raw_text: str = Field(..., min_length=20, description="Raw pasted resume or CV text")


class CandidateCVUpdateRequest(BaseModel):
    anonymized_text: Optional[str] = None
    extracted_skills: Optional[List[str]] = None
    years_of_experience: Optional[float] = None
    domain_expertise: Optional[List[str]] = None
    summary: Optional[str] = None


class CandidateCVResponse(BaseModel):
    id: int
    raw_text: str
    anonymized_text: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)
    years_of_experience: Optional[float] = None
    domain_expertise: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
