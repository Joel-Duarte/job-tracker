from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SystemDesignMode = Literal["ADAPTIVE", "INTERVIEW", "PRACTICE"]
SystemDesignStage = Literal["REQUIREMENTS", "DESIGN", "REVIEW", "DEFENCE", "COMPLETED"]
SystemDesignStatus = Literal["IN_PROGRESS", "COMPLETED", "ABANDONED"]


class SystemDesignChallengeRead(BaseModel):
    """Candidate-safe challenge projection.

    Explicitly omits ``interviewer_brief`` so hidden scale targets, expected
    architecture components, and scoring criteria never leak to candidates.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    category: str
    difficulty: str
    prompt_summary: str
    initial_prompt: str
    tags: list[str] = Field(default_factory=list)
    is_builtin: bool
    created_at: datetime


class RequirementsLedgerSchema(BaseModel):
    """Structured functional, non-functional, scale, and scope ledger."""

    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    scale_estimates: dict[str, str] = Field(default_factory=dict)
    out_of_scope: list[str] = Field(default_factory=list)
    notes: str = ""
    is_locked: bool = False


class TranscriptTurnSchema(BaseModel):
    """Single message turn in Stage B requirements discovery or Stage E defence."""

    turn_index: int
    role: Literal["interviewer", "candidate"]
    content: str
    stage: str
    timestamp: str


class DiagramRevisionRead(BaseModel):
    """Metadata for a single uploaded diagram image revision (binary lives on disk)."""

    version: int
    filename: str
    mime_type: str
    size_bytes: int
    notes: str = ""
    uploaded_at: str


class ArchitectureReviewSchema(BaseModel):
    """Structured multimodal critique separating visual ambiguity from design flaws."""

    diagram_version: int
    interpreted_components: list[str] = Field(default_factory=list)
    interpreted_data_flows: list[str] = Field(default_factory=list)
    visual_clarifications_needed: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_components: list[str] = Field(default_factory=list)
    bottlenecks_and_spofs: list[str] = Field(default_factory=list)
    unnecessary_complexity: list[str] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    overall_impression: str
    suggested_defence_topics: list[str] = Field(default_factory=list)


class RubricDimensionScore(BaseModel):
    """Single scored rubric dimension backed by concrete session evidence."""

    dimension: str
    score: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=5)
    critique: str

    @field_validator("evidence")
    @classmethod
    def _validate_non_blank_evidence(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise ValueError(
                "Evidence must contain at least 5 non-whitespace characters."
            )
        return cleaned


class FinalEvaluationSchema(BaseModel):
    """Evidence-backed final scorecard and actionable next steps."""

    overall_score: float = Field(ge=0.0, le=100.0)
    readiness_rating: Literal[
        "NEEDS_PRACTICE", "DEVELOPING", "INTERVIEW_READY", "STRONG_HIRE"
    ]
    executive_summary: str
    rubric_scores: list[RubricDimensionScore]
    key_strengths: list[str]
    critical_gaps: list[str]
    recommended_next_steps: list[str]


class SystemDesignSessionCreate(BaseModel):
    """Payload to start a new system design practice or interview session."""

    challenge_id: int
    application_id: int | None = None
    mode: SystemDesignMode = "ADAPTIVE"


class SystemDesignChallengeCreate(BaseModel):
    """Manual creation of a custom system design challenge."""

    title: str = Field(..., min_length=3, max_length=200)
    category: str = Field(default="DISTRIBUTED_SYSTEMS", max_length=80)
    difficulty: str = Field(default="MEDIUM", max_length=40)
    prompt_summary: str = Field(..., min_length=5, max_length=600)
    initial_prompt: str = Field(..., min_length=10, max_length=4000)
    tags: list[str] = Field(default_factory=list)
    expected_components: list[str] = Field(default_factory=list)
    scale_notes: str = ""


class SystemDesignChallengeUpdate(BaseModel):
    """Payload to edit an existing system design challenge (built-in or custom)."""

    title: str = Field(..., min_length=3, max_length=255)
    category: str = Field("DISTRIBUTED_SYSTEMS", min_length=2, max_length=64)
    difficulty: str = Field("MEDIUM", min_length=2, max_length=32)
    prompt_summary: str = Field(..., min_length=5, max_length=1500)
    initial_prompt: str = Field(..., min_length=10, max_length=4000)
    tags: list[str] = Field(default_factory=list)
    expected_components: list[str] = Field(default_factory=list)
    scale_notes: str = Field("", max_length=2000)


class SystemDesignChallengeGenerateRequest(BaseModel):
    """AI generation of a custom system design challenge from a topic or job application."""

    topic: str = Field(default="", max_length=1000)
    application_id: int | None = None
    difficulty: str = Field(default="MEDIUM", max_length=40)
    use_web_search: bool = True


def _strip_non_empty_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Message cannot be blank.")
    return cleaned


class RequirementsMessageRequest(BaseModel):
    """Candidate message submitted during Stage B requirements discovery."""

    message: str = Field(..., min_length=1, max_length=8000)
    request_hint: bool = False

    @field_validator("message")
    @classmethod
    def _validate_non_empty_message(cls, value: str) -> str:
        return _strip_non_empty_text(value)


class DiagramReviewRequest(BaseModel):
    """Optional target diagram revision for Stage D architecture analysis."""

    diagram_version: int | None = Field(default=None, ge=1)
    use_web_search: bool = False


class DefenceMessageRequest(BaseModel):
    """Candidate answer or defence statement submitted during Stage E."""

    message: str = Field(..., min_length=1, max_length=8000)
    request_hint: bool = False
    use_web_search: bool = False

    @field_validator("message")
    @classmethod
    def _validate_non_empty_message(cls, value: str) -> str:
        return _strip_non_empty_text(value)


class FrontierEvaluationPacketRead(BaseModel):
    """Self-contained markdown dossier for grading in a frontier model (Claude/GPT/Gemini)."""

    session_id: int
    challenge_title: str
    filename: str
    diagram_version: int | None = None
    markdown_packet: str


class ImportFrontierEvaluationRequest(BaseModel):
    """Paste raw JSON or Markdown+JSON output from an external frontier model to save scorecard."""

    raw_response: str = Field(..., min_length=10, max_length=60000)


class RequirementsLedgerUpdateRequest(BaseModel):
    """Manual edit and/or lock state update for the requirements ledger."""

    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    scale_estimates: dict[str, str] = Field(default_factory=dict)
    out_of_scope: list[str] = Field(default_factory=list)
    notes: str = ""
    is_locked: bool = False


class SessionModeUpdateRequest(BaseModel):
    """Switch session guidance mode between INTERVIEW and PRACTICE."""

    mode: SystemDesignMode


class SystemDesignSessionRead(BaseModel):
    """Candidate-facing session state returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    challenge_id: int
    application_id: int | None = None
    mode: str
    stage: str
    status: str
    requirements_transcript: list[dict[str, Any]] = Field(default_factory=list)
    requirements_ledger: dict[str, Any] = Field(default_factory=dict)
    diagrams_metadata: list[dict[str, Any]] = Field(default_factory=list)
    architecture_reviews: list[dict[str, Any]] = Field(default_factory=list)
    defence_transcript: list[dict[str, Any]] = Field(default_factory=list)
    final_evaluation: dict[str, Any] | None = None
    overall_score: float | None = None
    readiness_rating: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    challenge: SystemDesignChallengeRead | None = None
