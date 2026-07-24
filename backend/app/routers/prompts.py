from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.prompts import PromptModel
from app.core.prompts import DEFAULT_PROMPTS

router = APIRouter(prefix="/api/v1/prompts", tags=["Prompts"])


class PromptResponse(BaseModel):
    name: str
    template: str


class PromptUpdateRequest(BaseModel):
    template: str


@router.get("/{name}", response_model=PromptResponse)
async def get_prompt(name: str, db: AsyncSession = Depends(get_db)):
    """Fetch active prompt template by name."""
    result = await db.execute(select(PromptModel).where(PromptModel.name == name))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    return prompt


@router.put("/{name}", response_model=PromptResponse)
async def update_prompt(name: str, payload: PromptUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update active prompt template in DB."""
    result = await db.execute(select(PromptModel).where(PromptModel.name == name))
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        prompt = PromptModel(name=name, template=payload.template)
        db.add(prompt)
    else:
        prompt.template = payload.template

    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.post("/{name}/reset", response_model=PromptResponse)
async def reset_prompt(name: str, db: AsyncSession = Depends(get_db)):
    """Reset a prompt back to default factory settings."""
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Default prompt for '{name}' does not exist")

    result = await db.execute(select(PromptModel).where(PromptModel.name == name))
    prompt = result.scalar_one_or_none()

    default_template = DEFAULT_PROMPTS[name]

    if not prompt:
        prompt = PromptModel(name=name, template=default_template)
        db.add(prompt)
    else:
        prompt.template = default_template

    await db.commit()
    await db.refresh(prompt)
    return prompt