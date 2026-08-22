from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class InterviewPersona(str, Enum):
    TECHNICAL_BAR_RAISER = "TECHNICAL_BAR_RAISER"
    HIRING_MANAGER = "HIRING_MANAGER"
    BEHAVIORAL_CULTURE = "BEHAVIORAL_CULTURE"
    SUPPORTIVE_COACH = "SUPPORTIVE_COACH"


class SessionStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class StarPresence(BaseModel):
    situation: bool = False
    task: bool = False
    action: bool = False
    result: bool = False


class TurnEvaluation(BaseModel):
    score: float = Field(..., ge=0, le=100)
    star_presence: StarPresence
    strengths: list[str] = Field(default_factory=list)
    missing_gaps: list[str] = Field(default_factory=list)
    constructive_critique: str
    exemplar_rewrite: str


class TurnData(BaseModel):
    turn_index: int
    question: str
    question_type: str = "BEHAVIORAL_STAR"
    user_answer: str
    attempt_count: int = 1
    evaluation: TurnEvaluation
    is_drill_down: bool = False
    created_at: datetime


class SessionStartRequest(BaseModel):
    application_id: Optional[int] = None
    persona: InterviewPersona = InterviewPersona.TECHNICAL_BAR_RAISER


class AnswerEvaluateRequest(BaseModel):
    turn_index: int
    answer_text: str


class DrillDownRequest(BaseModel):
    turn_index: Optional[int] = None


class SaveNotesRequest(BaseModel):
    notes_markdown: Optional[str] = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: Optional[int] = None
    persona: str
    status: str
    overall_score: Optional[float] = None
    readiness_rating: Optional[str] = None
    turns_data: list[dict[str, Any]] = Field(default_factory=list)
    summary_feedback: Optional[dict[str, Any]] = None
    current_question: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class FinalizeSessionResponse(BaseModel):
    session_id: int
    overall_score: float
    readiness_rating: str
    summary_feedback: dict[str, Any]
    timeline_event_id: Optional[int] = None
