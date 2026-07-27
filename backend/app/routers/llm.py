import logging
from typing import Any, Dict, Optional
import litellm
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.llm import LLMConfigModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-config", tags=["LLM Configuration"])


class LLMConfigRead(BaseModel):
    id: Optional[int] = None
    provider_name: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model_name: str
    embedding_model_name: Optional[str] = None
    is_active: bool = True
    source: str = Field(description="Indicates whether config comes from 'database' or '.env'")


class LLMConfigUpdate(BaseModel):
    provider_name: Optional[str] = Field(default="custom", description="Name of the provider")
    api_base: Optional[str] = Field(default=None, description="Custom base URL for the LLM API")
    api_key: Optional[str] = Field(default=None, description="API key if required by provider")
    model_name: Optional[str] = Field(default=None, description="Primary model identifier")
    embedding_model_name: Optional[str] = Field(default=None, description="Embedding model identifier")


@router.get("", response_model=LLMConfigRead)
async def get_current_llm_config(db: AsyncSession = Depends(get_db)) -> Any:
    stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
    res = await db.execute(stmt)
    db_config = res.scalar_one_or_none()

    if db_config:
        return LLMConfigRead(
            id=db_config.id,
            provider_name=db_config.provider_name,
            api_base=db_config.api_base,
            api_key=db_config.api_key,
            model_name=db_config.model_name,
            embedding_model_name=db_config.embedding_model_name,
            is_active=db_config.is_active,
            source="database",
        )

    return LLMConfigRead(
        provider_name=settings.LLM_PROVIDER_NAME,
        api_base=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY,
        model_name=settings.LLM_MODEL_NAME,
        embedding_model_name=getattr(settings, "LLM_EMBEDDING_MODEL_NAME", settings.EMBEDDING_MODEL_NAME),
        is_active=True,
        source=".env",
    )


@router.patch("", response_model=LLMConfigRead)
async def update_llm_config(
    payload: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Updates the active database LLM configuration. 
    If no active configuration exists yet, it creates one automatically.
    """
    stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
    res = await db.execute(stmt)
    db_config = res.scalar_one_or_none()

    update_data = payload.model_dump(exclude_unset=True)

    if not db_config:
        # Auto-create if it doesn't exist yet, falling back to defaults for missing fields
        db_config = LLMConfigModel(
            provider_name=update_data.get("provider_name", settings.LLM_PROVIDER_NAME),
            api_base=update_data.get("api_base", settings.LLM_API_BASE),
            api_key=update_data.get("api_key", settings.LLM_API_KEY),
            model_name=update_data.get("model_name", settings.LLM_MODEL_NAME),
            embedding_model_name=update_data.get("embedding_model_name", settings.EMBEDDING_MODEL_NAME),
            is_active=True,
        )
        db.add(db_config)
    else:
        # Update existing fields
        for field, value in update_data.items():
            setattr(db_config, field, value)

    await db.commit()
    await db.refresh(db_config)

    return LLMConfigRead(
        id=db_config.id,
        provider_name=db_config.provider_name,
        api_base=db_config.api_base,
        api_key=db_config.api_key,
        model_name=db_config.model_name,
        embedding_model_name=db_config.embedding_model_name,
        is_active=db_config.is_active,
        source="database",
    )


@router.delete("", status_code=status.HTTP_200_OK)
async def reset_llm_config_to_env(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    stmt = delete(LLMConfigModel)
    await db.execute(stmt)
    await db.commit()
    return {"message": "LLM configuration reset to .env fallback settings successfully."}


@router.post("/test")
async def test_llm_connection(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
    res = await db.execute(stmt)
    db_config = res.scalar_one_or_none()

    if db_config:
        provider_name = db_config.provider_name
        raw_model_name = db_config.model_name
        api_base = db_config.api_base
        api_key = db_config.api_key
        source = "database"
    else:
        provider_name = getattr(settings, "LLM_PROVIDER_NAME", "env_default")
        raw_model_name = settings.LLM_MODEL_NAME
        api_base = settings.LLM_API_BASE
        api_key = settings.LLM_API_KEY
        source = ".env"

    formatted_model_name = raw_model_name
    if provider_name and provider_name != "env_default" and "/" not in raw_model_name:
        formatted_model_name = f"{provider_name}/{raw_model_name}"

    try:
        kwargs: Dict[str, Any] = {
            "model": formatted_model_name,
            "api_base": api_base,
            "api_key": api_key,
            "messages": [{"role": "user", "content": "Respond with 'OK' to verify connectivity."}],
            "max_tokens": 10,
        }

        response = await litellm.acompletion(**kwargs)
        content = response.choices[0].message.content.strip() # type: ignore[attr-defined]
        return {
            "status": "success",
            "source": source,
            "provider_used": provider_name,
            "model_used": formatted_model_name,
            "api_base_used": api_base,
            "response": content,
        }
    except Exception as e:
        logger.error(f"LLM Connection Test Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to provider '{provider_name}' using model '{formatted_model_name}' at '{api_base}': {str(e)}",
        )