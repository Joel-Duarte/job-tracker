import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.candidate_profile import CandidateCVModel
from app.schemas.candidate_profile import (
    CandidateCVResponse,
    CandidateCVSaveRequest,
    CandidateCVUpdateRequest,
)
from app.services.llm import anonymize_and_parse_cv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile/cv", tags=["Candidate CV Profile"])


@router.get("", response_model=Optional[CandidateCVResponse])
async def get_active_cv_profile(db: AsyncSession = Depends(get_db)):
    """Retrieves the active candidate CV profile and extracted skills."""
    stmt = (
        select(CandidateCVModel)
        .where(CandidateCVModel.is_active == True)
        .order_by(CandidateCVModel.id.desc())
    )
    res = await db.execute(stmt)
    profile = res.scalars().first()
    return profile


@router.post("", response_model=CandidateCVResponse, status_code=status.HTTP_201_CREATED)
async def process_and_save_cv_profile(
    payload: CandidateCVSaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests raw candidate CV/resume, runs AI de-identification & duration conversion at 0.2 temperature,
    extracts canonical skills, and activates as user's profile.
    """
    raw_text = payload.raw_text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CV content cannot be empty.",
        )

    # 1. AI De-identification & canonical skill extraction
    try:
        anonymized_result = await anonymize_and_parse_cv(db, raw_text)
    except Exception as err:
        logger.error("Failed CV de-identification: %s", err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze and de-identify CV: {str(err)}",
        )

    # 2. Deactivate previous active profiles
    stmt_deact = select(CandidateCVModel).where(CandidateCVModel.is_active == True)
    res = await db.execute(stmt_deact)
    for p in res.scalars().all():
        p.is_active = False

    # 3. Save new profile
    cv_record = CandidateCVModel(
        raw_text=raw_text,
        anonymized_text=anonymized_result.anonymized_resume,
        extracted_skills=anonymized_result.extracted_skills,
        years_of_experience=anonymized_result.total_years_experience,
        domain_expertise=anonymized_result.domain_expertise,
        core_competencies=anonymized_result.core_competencies,
        summary=anonymized_result.summary,
        is_active=True,
    )
    db.add(cv_record)
    await db.commit()
    await db.refresh(cv_record)

    return cv_record


@router.patch("/{id}", response_model=CandidateCVResponse)
async def update_cv_profile(
    id: int,
    payload: CandidateCVUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Updates skills, summary, or anonymized text for a CV profile."""
    stmt = select(CandidateCVModel).where(CandidateCVModel.id == id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV profile ID {id} not found.",
        )

    if payload.anonymized_text is not None:
        profile.anonymized_text = payload.anonymized_text
    if payload.extracted_skills is not None:
        profile.extracted_skills = payload.extracted_skills
    if payload.years_of_experience is not None:
        profile.years_of_experience = payload.years_of_experience
    if payload.domain_expertise is not None:
        profile.domain_expertise = payload.domain_expertise
    if payload.core_competencies is not None:
        profile.core_competencies = payload.core_competencies
    if payload.summary is not None:
        profile.summary = payload.summary

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv_profile(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Deletes a candidate CV profile."""
    stmt = select(CandidateCVModel).where(CandidateCVModel.id == id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV profile ID {id} not found.",
        )

    await db.delete(profile)
    await db.commit()
    return None
