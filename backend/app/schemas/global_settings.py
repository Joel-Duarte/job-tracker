from pydantic import BaseModel


class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None
    AGENT_CHAT_RETENTION_DAYS: int | None = None
    ENABLE_AUTO_COVER_LETTER: bool | None = None
    COVER_LETTER_MATCH_THRESHOLD: int | None = None


class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool
    AGENT_CHAT_RETENTION_DAYS: int
    ENABLE_AUTO_COVER_LETTER: bool
    COVER_LETTER_MATCH_THRESHOLD: int
