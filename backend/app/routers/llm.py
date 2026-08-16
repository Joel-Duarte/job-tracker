import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.llm_factory import get_active_llm_config_dict, get_chat_model
from app.models.llm import LLMConfigModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-config", tags=["LLM Configuration"])


class LLMConfigRead(BaseModel):
    id: int | None = None
    provider_name: str
    api_base: str | None = None
    api_key: str | None = None
    model_name: str
    embedding_model_name: str | None = None
    temperature: float
    top_k: int | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    agent_model_name: str | None = None
    agent_temperature: float
    agent_top_k: int | None = None
    agent_top_p: float | None = None
    agent_max_tokens: int | None = None
    agent_max_recursions: int
    is_active: bool = True
    source: str = Field(
        description="Indicates whether config comes from 'database' or '.env'"
    )


class LLMConfigUpdate(BaseModel):
    provider_name: str | None = Field(default=None, description="Name of the provider")
    api_base: str | None = Field(
        default=None, description="Custom base URL for the LLM API"
    )
    api_key: str | None = Field(
        default=None, description="API key if required by provider"
    )
    model_name: str | None = Field(default=None, description="Primary model identifier")
    embedding_model_name: str | None = Field(
        default=None, description="Embedding model identifier"
    )
    temperature: float | None = Field(
        default=None, description="Primary model temperature"
    )
    top_k: int | None = Field(default=None, description="Primary model top_k")
    top_p: float | None = Field(default=None, description="Primary model top_p")
    max_tokens: int | None = Field(default=None, description="Primary model max tokens")
    agent_model_name: str | None = Field(
        default=None, description="Agent specific model identifier"
    )
    agent_temperature: float | None = Field(
        default=None, description="Agent temperature"
    )
    agent_top_k: int | None = Field(default=None, description="Agent top_k")
    agent_top_p: float | None = Field(default=None, description="Agent top_p")
    agent_max_tokens: int | None = Field(default=None, description="Agent max tokens")
    agent_max_recursions: int | None = Field(
        default=None, description="Agent max recursions"
    )


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
            temperature=db_config.temperature,
            top_k=db_config.top_k,
            top_p=db_config.top_p,
            max_tokens=db_config.max_tokens,
            agent_model_name=db_config.agent_model_name,
            agent_temperature=db_config.agent_temperature,
            agent_top_k=db_config.agent_top_k,
            agent_top_p=db_config.agent_top_p,
            agent_max_tokens=db_config.agent_max_tokens,
            agent_max_recursions=db_config.agent_max_recursions,
            is_active=db_config.is_active,
            source="database",
        )

    return LLMConfigRead(
        provider_name=settings.LLM_PROVIDER_NAME,
        api_base=settings.LLM_API_BASE,
        api_key=settings.LLM_API_KEY,
        model_name=settings.LLM_MODEL_NAME,
        embedding_model_name=settings.EMBEDDING_MODEL_NAME,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        max_tokens=None,
        agent_model_name=None,
        agent_temperature=0.2,
        agent_top_k=50,
        agent_top_p=1.0,
        agent_max_tokens=None,
        agent_max_recursions=15,
        is_active=True,
        source=".env",
    )


@router.patch("", response_model=LLMConfigRead)
async def update_llm_config(
    payload: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    stmt = select(LLMConfigModel).where(LLMConfigModel.is_active == True)
    res = await db.execute(stmt)
    db_config = res.scalar_one_or_none()

    update_data = payload.model_dump(exclude_unset=True)

    if not db_config:
        db_config = LLMConfigModel(
            provider_name=update_data.get("provider_name", settings.LLM_PROVIDER_NAME),
            api_base=update_data.get("api_base", settings.LLM_API_BASE),
            api_key=update_data.get("api_key", settings.LLM_API_KEY),
            model_name=update_data.get("model_name", settings.LLM_MODEL_NAME),
            embedding_model_name=update_data.get(
                "embedding_model_name", settings.EMBEDDING_MODEL_NAME
            ),
            temperature=update_data.get("temperature", 0.7),
            top_k=update_data.get("top_k", 50),
            top_p=update_data.get("top_p", 1.0),
            max_tokens=update_data.get("max_tokens", None),
            agent_model_name=update_data.get("agent_model_name", None),
            agent_temperature=update_data.get("agent_temperature", 0.2),
            agent_top_k=update_data.get("agent_top_k", 50),
            agent_top_p=update_data.get("agent_top_p", 1.0),
            agent_max_tokens=update_data.get("agent_max_tokens", None),
            agent_max_recursions=update_data.get("agent_max_recursions", 15),
            is_active=True,
        )
        db.add(db_config)
    else:
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
        temperature=db_config.temperature,
        top_k=db_config.top_k,
        top_p=db_config.top_p,
        max_tokens=db_config.max_tokens,
        agent_model_name=db_config.agent_model_name,
        agent_temperature=db_config.agent_temperature,
        agent_top_k=db_config.agent_top_k,
        agent_top_p=db_config.agent_top_p,
        agent_max_tokens=db_config.agent_max_tokens,
        agent_max_recursions=db_config.agent_max_recursions,
        is_active=db_config.is_active,
        source="database",
    )


@router.delete("", status_code=status.HTTP_200_OK)
async def reset_llm_config_to_env(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    stmt = delete(LLMConfigModel)
    await db.execute(stmt)
    await db.commit()
    return {
        "message": "LLM configuration reset to .env fallback settings successfully."
    }


@router.post("/test")
async def test_llm_connection(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    cfg = await get_active_llm_config_dict(db)

    try:
        chat_model = await get_chat_model(db, max_tokens=10)
        response = await chat_model.ainvoke(
            [HumanMessage(content="Respond with 'OK' to verify connectivity.")]
        )
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        return {
            "status": "success",
            "source": cfg.get("source", "unknown"),
            "provider_used": cfg.get("provider_name"),
            "model_used": cfg.get("model_name"),
            "api_base_used": cfg.get("api_base"),
            "response": content.strip(),
        }
    except Exception as err:
        logger.error("LLM Connection Test Failed: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to provider '{cfg.get('provider_name')}' using model '{cfg.get('model_name')}' at '{cfg.get('api_base')}': {err!s}",
        )
