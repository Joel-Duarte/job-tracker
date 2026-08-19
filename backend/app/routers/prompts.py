from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.prompts import DEFAULT_PROMPTS
from app.core.security import verify_admin_access
from app.models.prompts import PromptModel
from app.schemas.prompts import PromptResponse, PromptUpdateRequest

router = APIRouter(
    prefix="/prompts", tags=["Prompts"], dependencies=[Depends(verify_admin_access)]
)


@router.get("", response_model=list[PromptResponse])
async def list_prompts(db: AsyncSession = Depends(get_db)):
    """List all available system prompts."""
    result = await db.execute(select(PromptModel).order_by(PromptModel.name))
    prompts_in_db = {p.name: p for p in result.scalars().all()}

    response_list = []
    for name in DEFAULT_PROMPTS.keys():
        if name in prompts_in_db and prompts_in_db[name].template:
            response_list.append(prompts_in_db[name])
        else:
            # Fallback for unseeded/missing rows
            response_list.append(
                PromptResponse(
                    name=name,
                    template=DEFAULT_PROMPTS[name],
                    updated_at=datetime.now(UTC),
                )
            )

    return response_list


@router.get("/{name}", response_model=PromptResponse)
async def get_prompt(name: str, db: AsyncSession = Depends(get_db)):
    """Fetch a specific prompt template by name ('extraction' or 'summarization')."""
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{name}' not found. Valid options: {list(DEFAULT_PROMPTS.keys())}",
        )

    result = await db.execute(select(PromptModel).where(PromptModel.name == name))
    prompt = result.scalar_one_or_none()

    if not prompt or not prompt.template:
        return PromptResponse(
            name=name,
            template=DEFAULT_PROMPTS[name],
            updated_at=datetime.now(UTC),
        )

    return prompt


@router.patch("/{name}", response_model=PromptResponse)
async def update_prompt(
    name: str,
    payload: PromptUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a prompt template."""
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prompt name '{name}'. Valid options: {list(DEFAULT_PROMPTS.keys())}",
        )

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
    """Reset a prompt template back to factory defaults."""
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Default prompt for '{name}' does not exist. Valid options: {list(DEFAULT_PROMPTS.keys())}",
        )

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
