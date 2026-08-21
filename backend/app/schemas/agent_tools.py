from typing import Literal

from pydantic import BaseModel, Field


# 1. Pipeline Metrics
class AnalyzePipelineMetricsInput(BaseModel):
    period: Literal["weekly", "monthly"] = Field(
        default="weekly",
        description="Granularity of cohort funnel metrics: 'weekly' or 'monthly'.",
    )
    num_periods: int = Field(
        default=8,
        ge=1,
        le=52,
        description="Number of past periods to aggregate for metrics and trend deltas.",
    )


# 2. Detect Stalled Applications
class DetectStalledApplicationsInput(BaseModel):
    inactivity_threshold_days: int = Field(
        default=14,
        ge=1,
        le=365,
        description="Number of days without activity after which an application is considered stalled.",
    )
    status: str | None = Field(
        default=None,
        description="Optional status filter (e.g. 'APPLIED', 'TECHNICAL_INTERVIEW', 'ASSESSMENT').",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Max number of stalled applications to return.",
    )


# 3. Query Market Benchmarks
class QueryMarketBenchmarksInput(BaseModel):
    position_keyword: str | None = Field(
        default=None,
        description="Optional filter by position title keyword (e.g., 'Python', 'Backend', 'Senior').",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Max number of job postings to aggregate.",
    )


# 4. Evaluate AI Fit Score
class EvaluateAIFitScoreInput(BaseModel):
    company_or_id: str = Field(
        description="Company name (e.g. 'Stripe') or numeric Application ID (e.g. '12')."
    )


# 5. Manage Intake Queue
class ManageIntakeQueueInput(BaseModel):
    action: Literal["list", "retry", "cancel", "fix"] = Field(
        default="list",
        description="Queue action to perform: 'list', 'retry', 'cancel', or 'fix'.",
    )
    task_id: int | None = Field(
        default=None,
        description="Intake task ID required for 'retry', 'cancel', or 'fix' actions.",
    )
    fix_raw_text: str | None = Field(
        default=None,
        description="Updated job description text required when action='fix'.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Max number of queue tasks to list.",
    )


# 6. Manage Action Items
class ManageActionItemsInput(BaseModel):
    action: Literal["list", "complete", "dismiss", "create"] = Field(
        default="list",
        description="Action to perform: 'list', 'complete', 'dismiss', or 'create'.",
    )
    item_id: int | None = Field(
        default=None,
        description="Action item ID required for 'complete' or 'dismiss'.",
    )
    urgency: str | None = Field(
        default=None,
        description="Optional urgency filter or value for create ('HIGH', 'MEDIUM', 'LOW').",
    )
    title: str | None = Field(
        default=None,
        description="Title of the action item required when action='create'.",
    )
    due_date: str | None = Field(
        default=None,
        description="Optional ISO due date string when action='create'.",
    )
    application_id: int | None = Field(
        default=None,
        description="Optional application ID when action='create'.",
    )


# 7. Semantic Vector Search
class SemanticSearchInput(BaseModel):
    query: str = Field(
        description="Semantic search query describing company, role, email content, or recruiter communication."
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Max number of matching documents to return.",
    )


# 8. Update Application Pipeline
class UpdateApplicationPipelineInput(BaseModel):
    company_or_id: str = Field(
        description="Company name (e.g. 'Stripe') or numeric Application ID (e.g. '12')."
    )
    new_status: str = Field(
        description="New pipeline status: APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT, or HIRED."
    )
    notes: str | None = Field(
        default=None,
        description="Optional explanation or reason for status transition.",
    )
    event_type: str = Field(
        default="STATUS_CHANGE",
        description="Type of timeline event logged for this update.",
    )


# Legacy Tools Input Schemas
class ListApplicationsInput(BaseModel):
    status: str | None = Field(
        default=None,
        description="Filter by status: APPLIED, TECHNICAL_INTERVIEW, OFFER, REJECTED, ASSESSMENT, HIRED.",
    )
    action_required_only: bool = Field(
        default=False,
        description="If true, only returns applications with pending action items.",
    )
    limit: int = Field(default=20, ge=1, le=50, description="Max records to return.")


class ApplicationDetailsInput(BaseModel):
    company_or_id: str = Field(
        description="Company name (e.g. 'Stripe') or numeric Application ID (e.g. '12')."
    )
