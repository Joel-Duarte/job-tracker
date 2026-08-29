from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 6:
        return "***"
    return f"{secret[:3]}...{secret[-3:]}"


class AIProviderCreate(BaseModel):
    name: str = Field(
        ...,
        description="Human-readable provider label e.g. 'Local LM Studio', 'Anthropic Claude'",
    )
    provider_type: str = Field(
        ...,
        description="Provider identifier: 'openai', 'anthropic', 'ollama', 'google_genai', 'openrouter', 'custom'",
    )
    base_url: str | None = Field(
        default=None, description="Base API URL e.g. 'http://192.168.1.187:1234/v1'"
    )
    api_key: str | None = Field(default=None, description="API key if required")
    max_concurrency: int = Field(
        default=1, ge=1, le=50, description="Max parallel AI requests to this provider"
    )
    is_active: bool = Field(default=True)
    is_fallback: bool = Field(
        default=False, description="Designated secondary auto-failover provider"
    )
    input_cost_per_million: float | None = Field(
        default=0.0, ge=0.0, description="Cost in USD per 1M input tokens"
    )
    output_cost_per_million: float | None = Field(
        default=0.0, ge=0.0, description="Cost in USD per 1M output tokens"
    )


class AIProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    max_concurrency: int | None = Field(default=None, ge=1, le=50)
    is_active: bool | None = None
    is_fallback: bool | None = None
    input_cost_per_million: float | None = Field(default=None, ge=0.0)
    output_cost_per_million: float | None = Field(default=None, ge=0.0)


class AIProviderRead(BaseModel):
    id: int
    name: str
    provider_type: str
    base_url: str | None = None
    api_key_masked: str | None = None
    max_concurrency: int = 1
    is_active: bool
    is_fallback: bool = False
    input_cost_per_million: float | None = 0.0
    output_cost_per_million: float | None = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AITaskBindingCreate(BaseModel):
    provider_id: int = Field(..., description="ID of the AIProviderModel to bind to")
    model_name: str = Field(
        ...,
        description="Model identifier e.g. 'qwen3.5-4b', 'claude-3-5-sonnet-20241022'",
    )
    temperature: float = Field(default=0.2, description="Sampling temperature")
    reasoning_effort: str | None = Field(
        default="none",
        description="Thinking mode: 'none', 'low', 'medium', 'high', 'custom'",
    )
    custom_extra_body: dict[str, Any] | None = Field(
        default=None,
        description="Custom payload parameters / extra body for local engines",
    )
    max_tokens: int | None = Field(default=None)
    top_p: float | None = Field(default=None)
    embedding_dimensions: int | None = Field(default=None)
    extra_kwargs: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)


class AITaskBindingUpdate(BaseModel):
    provider_id: int | None = None
    model_name: str | None = None
    temperature: float | None = None
    reasoning_effort: str | None = None
    custom_extra_body: dict[str, Any] | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    embedding_dimensions: int | None = None
    extra_kwargs: dict[str, Any] | None = None
    is_active: bool | None = None


class AITaskBindingRead(BaseModel):
    id: int
    task_type: str
    provider_id: int
    provider_name: str | None = None
    provider_type: str | None = None
    model_name: str
    temperature: float
    reasoning_effort: str | None = "none"
    custom_extra_body: dict[str, Any] | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    embedding_dimensions: int | None = None
    extra_kwargs: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelProbeRequest(BaseModel):
    model_name: str = Field(..., description="Target model name to probe")


class ModelProbeResponse(BaseModel):
    provider_id: int
    provider_name: str
    provider_type: str
    model_name: str
    is_reasoning_model: bool
    supported_reasoning_modes: list[str] = Field(
        default_factory=lambda: ["none", "low", "medium", "high", "custom"]
    )
    supports_reasoning_effort: bool = False
    supports_chat_template_kwargs: bool = False
    supports_thinking_config: bool = False
    recommended_reasoning_effort: str = "none"
    recommended_extra_body: dict[str, Any] | None = None
    detected_tags: list[str] = Field(default_factory=list)
    notes: str = ""


class AITaskTestResponse(BaseModel):
    status: str
    task_type: str
    provider_name: str
    provider_type: str
    model_name: str
    base_url: str | None = None
    response: str


class AIProviderTestResponse(BaseModel):
    status: str
    provider_name: str
    provider_type: str
    base_url: str | None = None
    response: str


class DiscoveredModel(BaseModel):
    id: str
    name: str
    is_discovered: bool = True
    is_embedding: bool = False
    is_reasoning: bool = False


class AIProviderModelsResponse(BaseModel):
    provider_id: int
    provider_name: str
    provider_type: str
    models: list[DiscoveredModel]


class AIHealthStatusRead(BaseModel):
    status: str
    provider_id: int | None = None
    provider_name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    latency_ms: float = 0.0
    error_message: str | None = None
    fallback_provider_id: int | None = None
    fallback_provider_name: str | None = None


class PricingRateRead(BaseModel):
    key: str
    display_name: str
    provider: str
    input_cost_per_million: float
    output_cost_per_million: float
    description: str | None = None


class PricingRateUpdate(BaseModel):
    key: str
    input_cost_per_million: float = Field(..., ge=0.0)
    output_cost_per_million: float = Field(..., ge=0.0)


class PricingRateBatchUpdate(BaseModel):
    rates: list[PricingRateUpdate]


class UsageOverviewRead(BaseModel):
    monthly_tokens: int = 0
    monthly_spend_usd: float = 0.0
    monthly_savings_usd: float = 0.0
    all_time_tokens: int = 0
    all_time_spend_usd: float = 0.0
    all_time_savings_usd: float = 0.0
    local_inference_percentage: float = 0.0
    total_llm_calls: int = 0
    avg_cost_per_assessment: float = 0.0
    task_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict)
    comparative_costs: list[dict[str, Any]] = Field(default_factory=list)
