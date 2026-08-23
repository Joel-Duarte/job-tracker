from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterviewPersona(StrEnum):
    TECHNICAL_BAR_RAISER = "TECHNICAL_BAR_RAISER"
    HIRING_MANAGER = "HIRING_MANAGER"
    BEHAVIORAL_CULTURE = "BEHAVIORAL_CULTURE"
    SUPPORTIVE_COACH = "SUPPORTIVE_COACH"


class QuestionMode(StrEnum):
    TEXT_CONVERSATIONAL = "TEXT_CONVERSATIONAL"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    HYBRID = "HYBRID"


class SessionStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class StarPresence(BaseModel):
    situation: bool = False
    task: bool = False
    action: bool = False
    result: bool = False


class QuestionOption(BaseModel):
    key: str
    text: str
    explanation: str | None = None


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
    options: list[QuestionOption] | None = None
    selected_option: str | None = None
    user_answer: str
    attempt_count: int = 1
    evaluation: TurnEvaluation | None = None
    is_drill_down: bool = False
    created_at: datetime


class SessionStartRequest(BaseModel):
    application_id: int | None = None
    persona: InterviewPersona = InterviewPersona.TECHNICAL_BAR_RAISER
    question_mode: QuestionMode = QuestionMode.TEXT_CONVERSATIONAL


class AnswerEvaluateRequest(BaseModel):
    turn_index: int
    answer_text: str
    selected_option: str | None = None


class DrillDownRequest(BaseModel):
    turn_index: int | None = None


class SaveNotesRequest(BaseModel):
    notes_markdown: str | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int | None = None
    persona: str
    question_mode: str = "TEXT_CONVERSATIONAL"
    status: str
    overall_score: float | None = None
    readiness_rating: str | None = None
    turns_data: list[dict[str, Any]] = Field(default_factory=list)
    summary_feedback: dict[str, Any] | None = None
    current_question: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class FinalizeSessionResponse(BaseModel):
    session_id: int
    overall_score: float
    readiness_rating: str
    summary_feedback: dict[str, Any]
    timeline_event_id: int | None = None
