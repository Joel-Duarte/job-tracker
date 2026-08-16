from datetime import datetime
from typing import Any, Optional
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
    base_url: Optional[str] = Field(
        default=None, description="Base API URL e.g. 'http://192.168.1.187:1234/v1'"
    )
    api_key: Optional[str] = Field(default=None, description="API key if required")
    max_concurrency: int = Field(
        default=1, ge=1, le=50, description="Max parallel AI requests to this provider"
    )
    is_active: bool = Field(default=True)


class AIProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_concurrency: Optional[int] = Field(default=None, ge=1, le=50)
    is_active: Optional[bool] = None


class AIProviderRead(BaseModel):
    id: int
    name: str
    provider_type: str
    base_url: Optional[str] = None
    api_key_masked: Optional[str] = None
    max_concurrency: int = 1
    is_active: bool
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
    reasoning_effort: Optional[str] = Field(
        default="none", description="Thinking mode: 'none', 'low', 'medium', 'high'"
    )
    max_tokens: Optional[int] = Field(default=None)
    top_p: Optional[float] = Field(default=None)
    embedding_dimensions: Optional[int] = Field(default=None)
    extra_kwargs: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = Field(default=True)


class AITaskBindingUpdate(BaseModel):
    provider_id: Optional[int] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    embedding_dimensions: Optional[int] = None
    extra_kwargs: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class AITaskBindingRead(BaseModel):
    id: int
    task_type: str
    provider_id: int
    provider_name: Optional[str] = None
    provider_type: Optional[str] = None
    model_name: str
    temperature: float
    reasoning_effort: Optional[str] = "none"
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    embedding_dimensions: Optional[int] = None
    extra_kwargs: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AITaskTestResponse(BaseModel):
    status: str
    task_type: str
    provider_name: str
    provider_type: str
    model_name: str
    base_url: Optional[str] = None
    response: str


class AIProviderTestResponse(BaseModel):
    status: str
    provider_name: str
    provider_type: str
    base_url: Optional[str] = None
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
