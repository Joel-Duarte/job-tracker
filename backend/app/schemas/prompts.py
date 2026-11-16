from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PromptResponse(BaseModel):
    name: str = Field(
        description="Unique prompt key (e.g., 'email_extraction', 'jd_extraction')"
    )
    template: str = Field(description="The prompt template text")
    updated_at: datetime = Field(
        description="Timestamp of when the prompt was last updated"
    )
    has_golden_eval: bool = Field(
        default=False,
        description="True when a synthetic golden evaluation dataset exists for this prompt.",
    )
    golden_cases_count: int = Field(
        default=0,
        description="Number of golden benchmark scenarios covered for this prompt.",
    )

    model_config = ConfigDict(from_attributes=True)


class PromptUpdateRequest(BaseModel):
    template: str = Field(
        ..., min_length=10, description="The updated prompt template text"
    )


class PromptEvaluateRequest(BaseModel):
    candidate_template: str | None = Field(
        default=None,
        description="Optional unsaved candidate prompt template to test instead of the DB prompt.",
    )
    compare_default: bool = Field(
        default=False,
        description="When True, also evaluates the factory default prompt and reports delta.",
    )
    concurrency: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Optional concurrency override (defaults to active AI provider max_concurrency).",
    )


class PromptEvaluateCaseResult(BaseModel):
    id: str
    pipeline: str
    passed: bool
    elapsed_secs: float
    details: dict[str, Any] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)


class PromptEvaluateRunSummary(BaseModel):
    pipeline: str
    concurrency: int
    wall_secs: float
    passed: int
    total: int
    pass_rate: float
    all_passed: bool
    results: list[PromptEvaluateCaseResult] = Field(default_factory=list)


class PromptEvaluateResponse(BaseModel):
    prompt_name: str
    pipeline: str
    candidate_source: str
    concurrency: int
    concurrency_source: str
    candidate_result: PromptEvaluateRunSummary
    default_result: PromptEvaluateRunSummary | None = None
    delta_passed: int | None = None
    delta_pass_rate: float | None = None
