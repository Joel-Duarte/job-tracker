from typing import List, Optional
from pydantic import BaseModel, Field


class EmailExtractionResult(BaseModel):
    email_type: str = Field(description="Type/category of the email")
    company: Optional[str] = Field(default=None, description="Company name if present")
    position: str = Field(description="Job position or title")
    external_job_id: Optional[str] = Field(default=None, description="External job/requisition ID")
    job_url: Optional[str] = Field(default=None, description="URL to the job listing")
    event_type: Optional[str] = Field(default=None, description="Event type, e.g., INTERVIEW_INVITE")
    status: Optional[str] = Field(default=None, description="Application status")
    action_required: bool = Field(description="Whether user action is required")
    action: Optional[str] = Field(default=None, description="Action details if required")
    summary: str = Field(description="Brief summary of the email body")


class ApplicationSummaryResult(BaseModel):
    snapshot: str = Field(description="Full text snapshot of application history")
    current_stage: str = Field(description="Current stage e.g., REJECTED, APPLIED")
    next_action: Optional[str] = Field(default=None, description="Next action item if any")


class ExtractedJobSpec(BaseModel):
    """Structured job details extracted from raw webpage or pasted job description text."""
    job_found: bool = Field(
        description="True if the provided text contains an actual job vacancy/description; False if error page, navigation, or unrelated text."
    )
    company: str = Field(
        default="Not Specified",
        description="Company, employer, or organization name"
    )
    position: str = Field(
        default="Not Specified",
        description="Job title or role position"
    )
    location_work_type: str = Field(
        default="Not Specified",
        description="Location and work model e.g. 'San Francisco, CA (Hybrid)' or 'Remote (US)'"
    )
    salary_benefits: str = Field(
        default="Not Specified",
        description="Salary range, compensation, and key benefits or perks mentioned"
    )
    core_responsibilities: str = Field(
        default="Not Specified",
        description="Core duties, responsibilities, and expected impact"
    )
    requirements_qualifications: str = Field(
        default="Not Specified",
        description="Key technical requirements, years of experience, education, and required qualifications"
    )
    ats_keywords: List[str] = Field(
        default_factory=list,
        description="Critical technical and domain ATS keywords for candidate matching"
    )
    raw_markdown_summary: Optional[str] = Field(
        default=None,
        description="Clean formatted markdown overview of the role"
    )


class JobAssessmentResult(BaseModel):
    company: str = Field(description="Company name extracted from the job posting")
    position: str = Field(description="Position or job title")
    fit_score: int = Field(description="Qualitative AI match/fit score from 0 to 100")
    programmatic_match_score: int = Field(default=0, description="Programmatic keyword overlap score (0 to 100)")
    matching_skills: List[str] = Field(default_factory=list, description="List of matching skills / strengths")
    missing_skills: List[str] = Field(default_factory=list, description="List of missing skills or requirements")
    pros: List[str] = Field(default_factory=list, description="Key advantages / pros of this role")
    cons: List[str] = Field(default_factory=list, description="Potential caveats or drawbacks")
    salary_min: Optional[float] = Field(default=None, description="Minimum compensation if mentioned")
    salary_max: Optional[float] = Field(default=None, description="Maximum compensation if mentioned")
    currency: Optional[str] = Field(default="USD", description="Salary currency")
    location: Optional[str] = Field(default=None, description="Job location")
    work_model: Optional[str] = Field(default=None, description="Remote, Hybrid, or Onsite")
    recommendation: str = Field(default="APPLY", description="Recommendation: APPLY_STRONGLY, APPLY, CAUTION, SKIP")
    summary: str = Field(description="Brief summary of the evaluation")