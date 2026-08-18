from pydantic import BaseModel


class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None
    ENABLE_AUTO_NUDGE: bool | None = None
    EMAIL_NUDGE_PROMPT: str | None = None
    EMAIL_REPLY_PROMPT: str | None = None


class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool
    ENABLE_AUTO_NUDGE: bool
