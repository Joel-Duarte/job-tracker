from pydantic import BaseModel


class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None
    AGENT_CHAT_RETENTION_DAYS: int | None = None


class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool
    AGENT_CHAT_RETENTION_DAYS: int
