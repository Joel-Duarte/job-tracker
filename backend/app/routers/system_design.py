import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.system_design import (
    CanvasDiagramSubmitRequest,
    ChallengeFrontierPromptResponse,
    DefenceMessageRequest,
    DiagramCatalogResponse,
    DiagramCoachChatRequest,
    DiagramCoachChatResponse,
    DiagramHintRequest,
    DiagramHintResponse,
    DiagramReviewRequest,
    FrontierEvaluationPacketRead,
    ImportFrontierChallengeRequest,
    ImportFrontierEvaluationRequest,
    RequirementsLedgerUpdateRequest,
    RequirementsMessageRequest,
    RequirementsRevealRequest,
    SessionModeUpdateRequest,
    SystemDesignChallengeCreate,
    SystemDesignChallengeGenerateRequest,
    SystemDesignChallengeRead,
    SystemDesignChallengeUpdate,
    SystemDesignSessionCreate,
    SystemDesignSessionRead,
)
from app.services.diagram_catalog import (
    CANONICAL_CATEGORIES,
    CANONICAL_DIAGRAM_BLOCKS,
)
from app.services.evaluation_worker import process_evaluation_task
from app.services.system_design_service import (
    DuplicateChallengeError,
    SystemDesignService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system-design", tags=["System Design Lab"])


def _http_error_from_value_error(ve: ValueError) -> HTTPException:
    msg = str(ve)
    code = (
        status.HTTP_404_NOT_FOUND
        if "not found" in msg.lower()
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=msg)


@router.get("/catalog", response_model=DiagramCatalogResponse)
async def get_diagram_catalog():
    """Return canonical architecture component categories and blocks for the Canvas Builder."""
    return {
        "categories": CANONICAL_CATEGORIES,
        "blocks": CANONICAL_DIAGRAM_BLOCKS,
    }


@router.get("/challenges", response_model=list[SystemDesignChallengeRead])
async def list_challenges(
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List curated system design challenges (omitting hidden interviewer briefs)."""
    challenges = await SystemDesignService.list_challenges(
        db=db, category=category, difficulty=difficulty
    )
    return [SystemDesignChallengeRead.model_validate(c) for c in challenges]


@router.get("/challenges/{slug_or_id}", response_model=SystemDesignChallengeRead)
async def get_challenge(
    slug_or_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single challenge by slug or numeric ID (omitting hidden brief)."""
    try:
        challenge = await SystemDesignService.get_challenge(
            db=db, slug_or_id=slug_or_id
        )
        return SystemDesignChallengeRead.model_validate(challenge)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


@router.post(
    "/challenges",
    response_model=SystemDesignChallengeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_challenge(
    payload: SystemDesignChallengeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a user-authored custom system design challenge (omitting hidden brief)."""
    try:
        challenge = await SystemDesignService.create_custom_challenge(
            db=db, payload=payload
        )
        return SystemDesignChallengeRead.model_validate(challenge)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/challenges/generate",
    response_model=SystemDesignChallengeRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_custom_challenge(
    payload: SystemDesignChallengeGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a tailored custom challenge using AI + optional job application & web search."""
    try:
        challenge = await SystemDesignService.generate_custom_challenge(
            db=db, payload=payload
        )
        return SystemDesignChallengeRead.model_validate(challenge)
    except DuplicateChallengeError as dce:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(dce))
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except Exception as exc:
        logger.error("Failed generating custom challenge: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed generating custom challenge: {exc}",
        )


@router.post(
    "/challenges/frontier-prompt",
    response_model=ChallengeFrontierPromptResponse,
)
async def prepare_frontier_challenge_prompt(
    payload: SystemDesignChallengeGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Build a self-contained Markdown prompt to run in Claude/ChatGPT/Gemini web chat."""
    try:
        return await SystemDesignService.prepare_frontier_challenge_prompt(
            db=db, payload=payload
        )
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/challenges/import",
    response_model=SystemDesignChallengeRead,
    status_code=status.HTTP_201_CREATED,
)
async def import_frontier_challenge(
    payload: ImportFrontierChallengeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate and save a custom challenge JSON response generated in a frontier chat."""
    try:
        challenge = await SystemDesignService.import_frontier_challenge(
            db=db, payload=payload
        )
        return SystemDesignChallengeRead.model_validate(challenge)
    except DuplicateChallengeError as dce:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(dce))
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/challenges/reset-defaults",
    response_model=list[SystemDesignChallengeRead],
)
async def reset_default_challenges(db: AsyncSession = Depends(get_db)):
    """Restore and reset the 8 built-in system design challenges to factory defaults."""
    challenges = await SystemDesignService.reset_default_challenges(db)
    return [SystemDesignChallengeRead.model_validate(c) for c in challenges]


@router.put(
    "/challenges/{challenge_id}",
    response_model=SystemDesignChallengeRead,
)
async def update_challenge(
    challenge_id: int,
    payload: SystemDesignChallengeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing system design challenge."""
    try:
        challenge = await SystemDesignService.update_challenge(
            db, challenge_id, payload
        )
        return SystemDesignChallengeRead.model_validate(challenge)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.delete("/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_challenge(
    challenge_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a system design challenge and any linked sessions."""
    try:
        await SystemDesignService.delete_custom_challenge(
            db=db, challenge_id=challenge_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as ve:
        msg = str(ve)
        code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=msg)


@router.post(
    "/sessions",
    response_model=SystemDesignSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    payload: SystemDesignSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Start a new System Design Lab session in ADAPTIVE, INTERVIEW, or PRACTICE mode."""
    try:
        session = await SystemDesignService.start_session(
            db=db,
            challenge_id=payload.challenge_id,
            application_id=payload.application_id,
            mode=payload.mode,
            brief_seed=payload.brief_seed,
            variant_id=payload.variant_id,
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.get("/sessions", response_model=list[SystemDesignSessionRead])
async def list_sessions(
    application_id: int | None = Query(default=None),
    session_status: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List saved System Design Lab sessions."""
    sessions = await SystemDesignService.list_sessions(
        db=db, application_id=application_id, status=session_status
    )
    await SystemDesignService.attach_active_queue_tasks(db, sessions)
    return [SystemDesignSessionRead.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SystemDesignSessionRead)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single System Design Lab session by ID."""
    try:
        session = await SystemDesignService.get_session(db=db, session_id=session_id)
        await SystemDesignService.attach_active_queue_tasks(db, [session])
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a System Design Lab session and its stored diagram directory."""
    try:
        await SystemDesignService.delete_session(db=db, session_id=session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.patch("/sessions/{session_id}/mode", response_model=SystemDesignSessionRead)
async def update_session_mode(
    session_id: int,
    payload: SessionModeUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a session between ADAPTIVE, INTERVIEW, and PRACTICE guidance modes."""
    try:
        session = await SystemDesignService.update_session_mode(
            db=db, session_id=session_id, mode=payload.mode
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/sessions/{session_id}/requirements/message",
    response_model=SystemDesignSessionRead,
)
async def send_requirements_message(
    session_id: int,
    payload: RequirementsMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a candidate clarifying question/message during Stage B discovery."""
    try:
        session = await SystemDesignService.send_requirements_message(
            db=db,
            session_id=session_id,
            message_text=payload.message,
            request_hint=payload.request_hint,
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except Exception as exc:
        logger.error("Failed processing requirements message: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed processing requirements message: {exc}",
        )


@router.post(
    "/sessions/{session_id}/requirements/extract",
    response_model=SystemDesignSessionRead,
)
async def extract_requirements_ledger(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Use the LLM to populate the requirements ledger from Stage B conversation."""
    try:
        session = await SystemDesignService.extract_requirements_ledger(
            db=db, session_id=session_id
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except Exception as exc:
        logger.error("Failed extracting requirements ledger: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed extracting requirements ledger: {exc}",
        )


@router.post(
    "/sessions/{session_id}/requirements/reveal",
    response_model=SystemDesignSessionRead,
)
async def reveal_requirements_ledger(
    session_id: int,
    payload: RequirementsRevealRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Reveal the session brief's requirements into the ledger so learners can study or jump straight to Studio."""
    try:
        lock_and_proceed = bool(payload.lock_and_proceed) if payload else False
        session = await SystemDesignService.reveal_requirements_ledger(
            db=db, session_id=session_id, lock_and_proceed=lock_and_proceed
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.put(
    "/sessions/{session_id}/requirements/ledger",
    response_model=SystemDesignSessionRead,
)
async def update_requirements_ledger(
    session_id: int,
    payload: RequirementsLedgerUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save candidate edits to the requirements ledger and lock/unlock stage."""
    try:
        session = await SystemDesignService.update_requirements_ledger(
            db=db, session_id=session_id, payload=payload
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/sessions/{session_id}/diagrams",
    response_model=SystemDesignSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_diagram(
    session_id: int,
    file: UploadFile = File(...),
    notes: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Upload or paste a PNG, JPEG, or WebP architecture diagram revision (v1..vN)."""
    try:
        file_bytes = await file.read()
        session = await SystemDesignService.upload_diagram(
            db=db, session_id=session_id, file_bytes=file_bytes, notes=notes
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except PermissionError as pe:
        logger.error("Diagram storage permission error: %s", pe)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(pe),
        )


@router.post(
    "/sessions/{session_id}/diagrams/canvas",
    response_model=SystemDesignSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_canvas_diagram(
    session_id: int,
    payload: CanvasDiagramSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Persist an interactive Canvas Builder revision as normalized Flow JSON (v1..vN)."""
    try:
        session = await SystemDesignService.submit_canvas_diagram(
            db=db, session_id=session_id, payload=payload
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except PermissionError as pe:
        logger.error("Canvas diagram storage permission error: %s", pe)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(pe),
        )


@router.get("/sessions/{session_id}/diagrams/{version}/flow")
async def get_diagram_flow(
    session_id: int,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """Return the normalized Flow JSON payload for a canvas diagram revision."""
    try:
        return await SystemDesignService.get_diagram_flow(
            db=db, session_id=session_id, version=version
        )
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/sessions/{session_id}/diagrams/hint",
    response_model=DiagramHintResponse,
)
async def request_diagram_hint(
    session_id: int,
    payload: DiagramHintRequest,
    db: AsyncSession = Depends(get_db),
):
    """Unlock guided blocks, path checklists, next wire hints, or live topology diagnostics."""
    try:
        return await SystemDesignService.request_diagram_hint(
            db=db, session_id=session_id, payload=payload
        )
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/sessions/{session_id}/diagrams/coach-chat",
    response_model=DiagramCoachChatResponse,
)
async def send_diagram_coach_message(
    session_id: int,
    payload: DiagramCoachChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Converse with the Studio Coach and receive optional click-to-apply canvas increments."""
    try:
        return await SystemDesignService.send_diagram_coach_message(
            db=db, session_id=session_id, payload=payload
        )
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.get("/sessions/{session_id}/diagrams/{version}/image")
async def get_diagram_image(
    session_id: int,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """Serve the stored diagram image bytes for a specific revision."""
    try:
        file_path, mime_type, filename = await SystemDesignService.get_diagram_file(
            db=db, session_id=session_id, version=version
        )
        return FileResponse(path=file_path, media_type=mime_type, filename=filename)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except PermissionError as pe:
        logger.error("Diagram retrieval permission error: %s", pe)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(pe),
        )


@router.post(
    "/sessions/{session_id}/review",
    response_model=SystemDesignSessionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def review_diagram_architecture(
    session_id: int,
    background_tasks: BackgroundTasks,
    payload: DiagramReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue background multimodal architecture review via the shared AI task queue."""
    try:
        session, task = await SystemDesignService.enqueue_architecture_review(
            db=db,
            session_id=session_id,
            diagram_version=payload.diagram_version if payload else None,
            use_web_search=payload.use_web_search if payload else False,
        )
        background_tasks.add_task(process_evaluation_task, task_id=task.id)
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except Exception as exc:
        logger.error("Failed enqueueing diagram architecture review: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed enqueueing diagram architecture review: {exc}",
        )


@router.post(
    "/sessions/{session_id}/defence/message",
    response_model=SystemDesignSessionRead,
)
async def send_defence_message(
    session_id: int,
    payload: DefenceMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a defence justification and receive the interviewer's next probe."""
    try:
        session = await SystemDesignService.send_defence_message(
            db=db,
            session_id=session_id,
            message_text=payload.message,
            request_hint=payload.request_hint,
            use_web_search=payload.use_web_search,
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except Exception as exc:
        logger.error("Failed processing defence message: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed processing defence message: {exc}",
        )


@router.post(
    "/sessions/{session_id}/evaluate",
    response_model=SystemDesignSessionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def evaluate_system_design_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue Stage F evidence-based final rubric evaluation via the shared AI task queue."""
    try:
        session, task = await SystemDesignService.enqueue_final_evaluation(
            db=db,
            session_id=session_id,
        )
        background_tasks.add_task(process_evaluation_task, task_id=task.id)
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
    except Exception as exc:
        logger.error("Failed enqueueing system design final evaluation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed enqueueing system design final evaluation: {exc}",
        )


@router.get(
    "/sessions/{session_id}/frontier-packet",
    response_model=FrontierEvaluationPacketRead,
)
async def get_frontier_evaluation_packet(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Export a self-contained Markdown evaluation prompt ready for a frontier LLM."""
    try:
        return await SystemDesignService.build_frontier_evaluation_packet(
            db=db, session_id=session_id
        )
    except ValueError as ve:
        raise _http_error_from_value_error(ve)


@router.post(
    "/sessions/{session_id}/import-evaluation",
    response_model=SystemDesignSessionRead,
)
async def import_frontier_evaluation(
    session_id: int,
    payload: ImportFrontierEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import an external frontier LLM scorecard (raw JSON or Markdown+JSON) onto the session."""
    try:
        session = await SystemDesignService.import_frontier_evaluation(
            db=db, session_id=session_id, raw_response=payload.raw_response
        )
        return SystemDesignSessionRead.model_validate(session)
    except ValueError as ve:
        raise _http_error_from_value_error(ve)
