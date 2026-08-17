from pydantic import BaseModel

class GlobalSettingsUpdate(BaseModel):
    ENABLE_EMBEDDINGS: bool | None = None

class GlobalSettingsRead(BaseModel):
    ENABLE_EMBEDDINGS: bool
