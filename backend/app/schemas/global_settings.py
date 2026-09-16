from pydantic import BaseModel


class SystemSettingsRead(BaseModel):
    has_completed_onboarding: bool = False
    enable_email_intake: bool = False
    enable_embeddings: bool = False
    enable_web_search: bool = False
    enable_auto_cover_letter: bool = False
    cover_letter_match_threshold: int = 70
    cover_letter_length: str = "standard"
    cover_letter_tone: str = "professional"
    agent_chat_retention_days: int = 7
    search_provider: str = "automatic"
    searxng_url: str | None = None
    enable_llm_judge: bool = False
    llm_judge_audit_cover_letter: bool = True
    llm_judge_audit_application_qa: bool = True
    llm_judge_audit_interview_guide: bool = False
    llm_judge_action: str = "auto_rewrite"
    llm_judge_max_retries: int = 1


class SystemSettingsUpdate(BaseModel):
    has_completed_onboarding: bool | None = None
    enable_email_intake: bool | None = None
    enable_embeddings: bool | None = None
    enable_web_search: bool | None = None
    enable_auto_cover_letter: bool | None = None
    cover_letter_match_threshold: int | None = None
    cover_letter_length: str | None = None
    cover_letter_tone: str | None = None
    agent_chat_retention_days: int | None = None
    search_provider: str | None = None
    searxng_url: str | None = None
    enable_llm_judge: bool | None = None
    llm_judge_audit_cover_letter: bool | None = None
    llm_judge_audit_application_qa: bool | None = None
    llm_judge_audit_interview_guide: bool | None = None
    llm_judge_action: str | None = None
    llm_judge_max_retries: int | None = None


class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None
    ENABLE_WEB_SEARCH: bool | None = None
    AGENT_CHAT_RETENTION_DAYS: int | None = None
    ENABLE_AUTO_COVER_LETTER: bool | None = None
    COVER_LETTER_MATCH_THRESHOLD: int | None = None
    COVER_LETTER_LENGTH: str | None = None
    COVER_LETTER_TONE: str | None = None
    ENABLE_EMAIL_INTAKE: bool | None = None
    HAS_COMPLETED_ONBOARDING: bool | None = None
    SEARCH_PROVIDER: str | None = None
    SEARXNG_URL: str | None = None
    ENABLE_LLM_JUDGE: bool | None = None
    LLM_JUDGE_AUDIT_COVER_LETTER: bool | None = None
    LLM_JUDGE_AUDIT_APPLICATION_QA: bool | None = None
    LLM_JUDGE_AUDIT_INTERVIEW_GUIDE: bool | None = None
    LLM_JUDGE_ACTION: str | None = None
    LLM_JUDGE_MAX_RETRIES: int | None = None


class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool = False
    ENABLE_WEB_SEARCH: bool = False
    AGENT_CHAT_RETENTION_DAYS: int
    ENABLE_AUTO_COVER_LETTER: bool = False
    COVER_LETTER_MATCH_THRESHOLD: int = 70
    COVER_LETTER_LENGTH: str = "standard"
    COVER_LETTER_TONE: str = "professional"
    ENABLE_EMAIL_INTAKE: bool = False
    HAS_COMPLETED_ONBOARDING: bool = False
    SEARCH_PROVIDER: str = "automatic"
    SEARXNG_URL: str | None = None
    ENABLE_LLM_JUDGE: bool = False
    LLM_JUDGE_AUDIT_COVER_LETTER: bool = True
    LLM_JUDGE_AUDIT_APPLICATION_QA: bool = True
    LLM_JUDGE_AUDIT_INTERVIEW_GUIDE: bool = False
    LLM_JUDGE_ACTION: str = "auto_rewrite"
    LLM_JUDGE_MAX_RETRIES: int = 1


class TestSearchProviderRequest(BaseModel):
    provider: str = "searxng"
    searxng_url: str


class TestSearchProviderResponse(BaseModel):
    success: bool
    provider: str
    message: str
    latency_ms: float | None = None
