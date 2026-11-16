from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.prompts import DEFAULT_PROMPTS, clear_prompt_cache
from app.core.security import verify_admin_access
from app.models.prompts import PromptModel
from app.schemas.prompts import (
    PromptEvaluateRequest,
    PromptEvaluateResponse,
    PromptResponse,
    PromptUpdateRequest,
)
from app.services.prompt_eval_service import (
    evaluate_prompt_against_golden,
    get_golden_cases_count,
)

router = APIRouter(
    prefix="/prompts", tags=["Prompts"], dependencies=[Depends(verify_admin_access)]
)


def _to_prompt_response(
    name: str, template: str, updated_at: datetime
) -> PromptResponse:
    cnt = get_golden_cases_count(name)
    return PromptResponse(
        name=name,
        template=template,
        updated_at=updated_at,
        has_golden_eval=cnt > 0,
        golden_cases_count=cnt,
    )


@router.get("", response_model=list[PromptResponse])
async def list_prompts(db: AsyncSession = Depends(get_db)):
    """List all available system prompts."""
    result = await db.execute(select(PromptModel).order_by(PromptModel.name))
    prompts_in_db = {p.name: p for p in result.scalars().all()}

    response_list = []
    for name in DEFAULT_PROMPTS.keys():
        if name in prompts_in_db and prompts_in_db[name].template:
            p = prompts_in_db[name]
            response_list.append(_to_prompt_response(name, p.template, p.updated_at))
        else:
            response_list.append(
                _to_prompt_response(name, DEFAULT_PROMPTS[name], datetime.now(UTC))
            )

    return response_list


@router.get("/{name}", response_model=PromptResponse)
async def get_prompt(name: str, db: AsyncSession = Depends(get_db)):
    """Fetch a specific prompt template by name (e.g., 'email_extraction', 'jd_extraction')."""
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{name}' not found. Valid options: {list(DEFAULT_PROMPTS.keys())}",
        )

    result = await db.execute(select(PromptModel).where(PromptModel.name == name))
    prompt = result.scalar_one_or_none()

    if not prompt or not prompt.template:
        return _to_prompt_response(name, DEFAULT_PROMPTS[name], datetime.now(UTC))

    return _to_prompt_response(prompt.name, prompt.template, prompt.updated_at)


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
    clear_prompt_cache(name)
    return _to_prompt_response(prompt.name, prompt.template, prompt.updated_at)


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
    clear_prompt_cache(name)
    return _to_prompt_response(prompt.name, prompt.template, prompt.updated_at)


@router.post("/{name}/evaluate", response_model=PromptEvaluateResponse)
async def evaluate_prompt_template(
    name: str,
    payload: PromptEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run synthetic golden evaluation for a prompt template (+ optional A/B comparison vs factory default)."""
    if name not in DEFAULT_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{name}' not found. Valid options: {list(DEFAULT_PROMPTS.keys())}",
        )
    if get_golden_cases_count(name) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prompt '{name}' does not yet have an offline-safe golden dataset.",
        )

    try:
        res = await evaluate_prompt_against_golden(
            db,
            name,
            candidate_template=payload.candidate_template,
            compare_default=payload.compare_default,
            concurrency=payload.concurrency,
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Golden prompt evaluation failed: {exc}",
        )
    return PromptEvaluateResponse(**res)
