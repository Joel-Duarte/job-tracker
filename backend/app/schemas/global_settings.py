from pydantic import BaseModel


class SystemSettingsRead(BaseModel):
    has_completed_onboarding: bool = False
    enable_email_intake: bool = False
    enable_embeddings: bool = False
    enable_web_search: bool = False
    enable_auto_cover_letter: bool = False
    cover_letter_match_threshold: int = 70
    cover_letter_length: str = "standard"
    agent_chat_retention_days: int = 7


class SystemSettingsUpdate(BaseModel):
    has_completed_onboarding: bool | None = None
    enable_email_intake: bool | None = None
    enable_embeddings: bool | None = None
    enable_web_search: bool | None = None
    enable_auto_cover_letter: bool | None = None
    cover_letter_match_threshold: int | None = None
    cover_letter_length: str | None = None
    agent_chat_retention_days: int | None = None


class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None
    ENABLE_WEB_SEARCH: bool | None = None
    AGENT_CHAT_RETENTION_DAYS: int | None = None
    ENABLE_AUTO_COVER_LETTER: bool | None = None
    COVER_LETTER_MATCH_THRESHOLD: int | None = None
    COVER_LETTER_LENGTH: str | None = None
    ENABLE_EMAIL_INTAKE: bool | None = None
    HAS_COMPLETED_ONBOARDING: bool | None = None


class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool = False
    ENABLE_WEB_SEARCH: bool = False
    AGENT_CHAT_RETENTION_DAYS: int
    ENABLE_AUTO_COVER_LETTER: bool = False
    COVER_LETTER_MATCH_THRESHOLD: int = 70
    COVER_LETTER_LENGTH: str = "standard"
    ENABLE_EMAIL_INTAKE: bool = False
    HAS_COMPLETED_ONBOARDING: bool = False
