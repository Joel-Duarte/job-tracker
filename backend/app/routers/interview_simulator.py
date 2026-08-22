import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.interview_session import InterviewSessionModel
from app.schemas.interview_simulator import (
    AnswerEvaluateRequest,
    DrillDownRequest,
    FinalizeSessionResponse,
    SaveNotesRequest,
    SessionResponse,
    SessionStartRequest,
)
from app.services.interview_simulator_service import InterviewSimulatorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interviews/sessions", tags=["Interview Simulator"])


def _to_session_response(session: InterviewSessionModel) -> SessionResponse:
    turns = session.turns_data or []
    current_q = None
    if turns:
        # Most recent question turn
        current_q = turns[-1].get("question")

    return SessionResponse(
        id=session.id,
        application_id=session.application_id,
        persona=session.persona,
        status=session.status,
        overall_score=session.overall_score,
        readiness_rating=session.readiness_rating,
        turns_data=turns,
        summary_feedback=session.summary_feedback,
        current_question=current_q,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: SessionStartRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await InterviewSimulatorService.start_session(
            db=db,
            application_id=payload.application_id,
            persona=payload.persona.value,
        )
        return _to_session_response(session)
    except Exception as e:
        logger.error("Failed to start interview session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview session: {str(e)}",
        )


@router.post("/{session_id}/evaluate-answer", response_model=SessionResponse)
async def evaluate_answer(
    session_id: int,
    payload: AnswerEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await InterviewSimulatorService.evaluate_answer(
            db=db,
            session_id=session_id,
            turn_index=payload.turn_index,
            answer_text=payload.answer_text,
        )
        return _to_session_response(session)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error("Failed to evaluate answer: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate answer: {str(e)}",
        )


@router.post("/{session_id}/next-question", response_model=SessionResponse)
async def next_question(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await InterviewSimulatorService.generate_next_question(
            db=db, session_id=session_id
        )
        return _to_session_response(session)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error("Failed to generate next question: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate next question: {str(e)}",
        )


@router.post("/{session_id}/drill-down", response_model=SessionResponse)
async def drill_down(
    session_id: int,
    payload: Optional[DrillDownRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        turn_idx = payload.turn_index if payload else None
        session = await InterviewSimulatorService.generate_drill_down(
            db=db, session_id=session_id, turn_index=turn_idx
        )
        return _to_session_response(session)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error("Failed to generate drill-down question: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate drill-down question: {str(e)}",
        )


@router.post("/{session_id}/finalize", response_model=FinalizeSessionResponse)
async def finalize_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await InterviewSimulatorService.finalize_session(
            db=db, session_id=session_id
        )
        return FinalizeSessionResponse(**res)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error("Failed to finalize session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {str(e)}",
        )


@router.post("/{session_id}/save-notes")
async def save_notes(
    session_id: int,
    payload: Optional[SaveNotesRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        notes_md = payload.notes_markdown if payload else None
        app_model = await InterviewSimulatorService.save_notes(
            db=db, session_id=session_id, custom_markdown=notes_md
        )
        return {"message": "Notes saved successfully", "application_id": app_model.id}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to save notes: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save notes: {str(e)}",
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewSessionModel).where(InterviewSessionModel.id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found"
        )
    return _to_session_response(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    application_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterviewSessionModel).order_by(InterviewSessionModel.created_at.desc())
    if application_id is not None:
        stmt = stmt.where(InterviewSessionModel.application_id == application_id)
    stmt = stmt.limit(limit)

    res = await db.execute(stmt)
    sessions = res.scalars().all()
    return [_to_session_response(s) for s in sessions]
