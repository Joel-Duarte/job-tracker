import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EmailExtractionResult(BaseModel):
    email_type: str = Field(description="Type/category of the email")
    company: str | None = Field(default=None, description="Company name if present")
    position: str = Field(description="Job position or title")
    external_job_id: str | None = Field(
        default=None, description="External job/requisition ID"
    )
    job_url: str | None = Field(default=None, description="URL to the job listing")
    event_type: str | None = Field(
        default=None, description="Event type, e.g., INTERVIEW_INVITE"
    )
    status: str | None = Field(default=None, description="Application status")
    action_required: bool = Field(description="Whether user action is required")
    action: str | None = Field(default=None, description="Action details if required")
    due_date: str | None = Field(
        default=None,
        description="Explicit deadline date or scheduled interview date in ISO YYYY-MM-DD format if mentioned in the email",
    )
    summary: str = Field(description="Brief summary of the email body")


class ApplicationSummaryResult(BaseModel):
    snapshot: str = Field(description="Full text snapshot of application history")
    current_stage: str = Field(description="Current stage e.g., REJECTED, APPLIED")
    next_action: str | None = Field(default=None, description="Next action item if any")


class SpokenLanguageRequirement(BaseModel):
    language: str = Field(
        ...,
        description="Spoken/natural language name e.g. 'English', 'German', 'French', 'Portuguese'",
    )
    requirement: str = Field(
        default="mandatory",
        description="Requirement strictness: 'mandatory' (must-have/required/implicit from JD text language) or 'preferred' (nice-to-have/plus)",
    )
    proficiency: str | None = Field(
        default=None,
        description="Proficiency level if specified e.g. 'Fluent / C1', 'Native', 'Working Proficiency / B2'",
    )


class LanguageMatchResult(BaseModel):
    is_matched: bool = Field(
        default=True,
        description="True if all mandatory spoken language requirements are satisfied by candidate profile",
    )
    detected_jd_language: str = Field(
        default="English",
        description="Primary written language of the job description",
    )
    required_languages: list[SpokenLanguageRequirement] = Field(
        default_factory=list,
        description="List of all required and preferred spoken languages for this role",
    )
    missing_mandatory: list[str] = Field(
        default_factory=list,
        description="List of mandatory spoken languages missing from candidate profile",
    )
    missing_preferred: list[str] = Field(
        default_factory=list,
        description="List of preferred/nice-to-have spoken languages missing from candidate profile",
    )
    warning: str | None = Field(
        default=None,
        description="Detailed, human-readable warning banner text if a language mismatch is detected",
    )


class ExtractedJobSpec(BaseModel):
    """Structured job details extracted from raw webpage or pasted job description text."""

    job_found: bool = Field(
        default=True,
        description="True if the provided text contains an actual job vacancy/description; False if error page, navigation, or unrelated text.",
    )
    company: str = Field(
        default="Not Specified", description="Company, employer, or organization name"
    )
    company_url: str | None = Field(
        default=None,
        description="Official company website domain or URL, e.g. 'stripe.com', 'linear.app', 'datadoghq.com'",
    )
    position: str = Field(
        default="Not Specified", description="Job title or role position"
    )
    detected_language: str = Field(
        default="English",
        description="Primary natural language in which the job description text is written (e.g. English, German, French, Portuguese, Spanish, etc.)",
    )
    required_spoken_languages: list[SpokenLanguageRequirement] = Field(
        default_factory=list,
        description="Spoken/natural language requirements. If no explicit requirements are stated, the detected written language of the JD must be included as a mandatory requirement.",
    )
    why_hiring: str | None = Field(
        default=None,
        description="Explicit company expansion, scaling, or team creation reasons. Must be null if not explicitly mentioned in text.",
    )
    what_you_will_build: str | None = Field(
        default=None,
        description="Concrete deliverables, systems, or product domains. Must be null if not explicitly mentioned in text.",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Array of clean, itemized action items (e.g., 'Design distributed data pipelines'). Company-specific introductory phrases must be stripped.",
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="Array of hard prerequisites, years of experience, and qualifications as clean itemized strings.",
    )
    extracted_skills: list[str] = Field(
        default_factory=list,
        description="Array of technical skills and competencies mentioned in the job description.",
    )
    compensation_text: str | None = Field(
        default=None,
        description="Formatted salary or rate range string e.g. '$195,000 - $245,000 USD'.",
    )
    location_text: str | None = Field(
        default=None,
        description="Clean city and country string e.g. 'San Francisco, CA'.",
    )
    workplace_type: str | None = Field(
        default=None,
        description="Clean classification string: 'Remote', 'Hybrid', or 'On-site'.",
    )
    raw_markdown_summary: str | None = Field(
        default=None, description="Clean formatted markdown overview of the role"
    )


class VocabularyTranslationItem(BaseModel):
    jd_term: str = Field(description="Exact terminology or phrase required by the JD")
    cv_term: str = Field(
        description="Equivalent terminology currently used in the candidate CV"
    )
    replacement_guidance: str = Field(
        description="Specific instructions for swapping the term"
    )


class ImpactReframingItem(BaseModel):
    bullet_point: str = Field(description="Original bullet point from the CV")
    suggested_rewrite: str = Field(
        description="Reframed bullet point aligning with JD action verbs and metrics"
    )
    reason: str = Field(
        description="Rationale for how this reframe improves ATS rank / recruiter appeal"
    )


class ResumeTailoringStrategy(BaseModel):
    vocabulary_translation: list[VocabularyTranslationItem] = Field(
        default_factory=list,
        description="List of exact synonym vocabulary replacements",
    )
    impact_reframing: list[ImpactReframingItem] = Field(
        default_factory=list,
        description="List of bullet point rewrites adding metrics and aligning with JD action verbs",
    )
    structural_adjustments: list[str] = Field(
        default_factory=list,
        description="Section ordering, emphasis, or layout adjustments to optimize profile clarity",
    )


class OptimizationGaps(BaseModel):
    missing_completely: list[str] = Field(
        default_factory=list,
        description="Mandatory JD terms entirely absent from CV (acknowledged gap, not hallucinated)",
    )
    vocabulary_mismatches: list[str] = Field(
        default_factory=list,
        description="Skills present in CV under a different term (e.g. Node vs Node.js, Postgres vs PostgreSQL)",
    )
    experience_mismatch: str | None = Field(
        default=None, description="Years of experience or seniority level delta if any"
    )


class HardMatches(BaseModel):
    keyword_match_rate: str = Field(
        default="0/10",
        description="Match rate of core mandatory skills found (e.g. '8/10 core skills found')",
    )
    top_alignment: list[str] = Field(
        default_factory=list,
        description="Top 3 candidate skills that best align with must-haves in the JD",
    )


class JobAssessmentResult(BaseModel):
    company: str = Field(description="Company name extracted from the job posting")
    company_url: str | None = Field(
        default=None,
        description="Official company website domain or URL, e.g. 'stripe.com', 'linear.app'",
    )
    position: str = Field(description="Position or job title")
    fit_score: int = Field(description="Calculated AI match/fit score from 0 to 100")
    programmatic_match_score: int = Field(
        default=0, description="Programmatic keyword overlap score (0 to 100)"
    )
    match_summary: str = Field(
        default="",
        description="2-sentence overview defining the profile-to-JD delta gap",
    )
    hard_matches: HardMatches | None = Field(
        default=None, description="Core hard keyword matches and top aligned skills"
    )
    optimization_gaps: OptimizationGaps | None = Field(
        default=None, description="Strict terminology mismatches and experience delta"
    )
    tailoring_strategy: ResumeTailoringStrategy | None = Field(
        default=None, description="Step-by-step resume tailoring recommendations"
    )
    markdown_report: str | None = Field(
        default=None, description="Full structured Markdown audit report"
    )
    matching_skills: list[str] = Field(
        default_factory=list, description="List of matching skills / strengths"
    )
    missing_skills: list[str] = Field(
        default_factory=list, description="List of missing skills or requirements"
    )
    pros: list[str] = Field(
        default_factory=list, description="Key advantages / pros of this role"
    )
    cons: list[str] = Field(
        default_factory=list, description="Potential caveats or drawbacks"
    )
    salary_min: float | None = Field(
        default=None, description="Minimum compensation if mentioned"
    )
    salary_max: float | None = Field(
        default=None, description="Maximum compensation if mentioned"
    )
    currency: str | None = Field(default="USD", description="Salary currency")
    location: str | None = Field(default=None, description="Job location")
    work_model: str | None = Field(
        default=None, description="Remote, Hybrid, or Onsite"
    )
    recommendation: str = Field(
        default="APPLY",
        description="Recommendation: APPLY_STRONGLY, APPLY, CAUTION, SKIP",
    )
    language_match: LanguageMatchResult | None = Field(
        default=None,
        description="Spoken language match audit and mismatch warnings",
    )
    summary: str = Field(default="", description="Brief summary of the evaluation")

    @field_validator("work_model", mode="before")
    @classmethod
    def normalize_work_model(cls, v: Any) -> str | None:
        if not v or not isinstance(v, str):
            return None
        lower = v.lower().strip()
        if "hybrid" in lower:
            return "Hybrid"
        if "remote" in lower or "telecommute" in lower:
            return "Remote"
        if "on-site" in lower or "onsite" in lower or "in-office" in lower:
            return "On-site"
        cleaned = re.sub(r"\s*\([^)]*\)", "", v).strip()
        return cleaned[:30] if cleaned else None
