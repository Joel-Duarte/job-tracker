from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptResponse(BaseModel):
    name: str = Field(
        description="Unique prompt key (e.g., 'email_extraction', 'jd_extraction')"
    )
    template: str = Field(description="The prompt template text")
    updated_at: datetime = Field(
        description="Timestamp of when the prompt was last updated"
    )

    model_config = ConfigDict(from_attributes=True)


class PromptUpdateRequest(BaseModel):
    template: str = Field(
        ..., min_length=10, description="The updated prompt template text"
    )
