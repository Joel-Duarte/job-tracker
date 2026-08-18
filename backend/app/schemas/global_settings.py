from pydantic import BaseModel


class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None
    auto_generate_cover_letter: bool | None = None
    cover_letter_min_match_pct: int | None = None


class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool
    auto_generate_cover_letter: bool = False
    cover_letter_min_match_pct: int = 50
