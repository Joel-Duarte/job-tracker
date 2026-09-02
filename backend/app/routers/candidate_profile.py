import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_admin_access
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.candidate_profile import (
    CandidateCVResponse,
    CandidateCVSaveRequest,
    CandidateCVUpdateRequest,
    CVParsedDocumentResponse,
    CVTaskStatusResponse,
)
from app.services.evaluation_worker import process_evaluation_task
from app.services.file_parser import normalize_resume_text, parse_cv_document
from app.services.skill_normalizer import normalize_skills_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile/cv", tags=["Candidate CV Profile"])


@router.get("", response_model=CandidateCVResponse | None)
async def get_active_cv_profile(db: AsyncSession = Depends(get_db)):
    """Retrieves the active candidate CV profile and extracted skills."""
    stmt = select(CandidateCVModel).limit(1)
    res = await db.execute(stmt)
    profile = res.scalars().first()
    return profile


@router.post(
    "",
    response_model=CVTaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_access)],
)
async def enqueue_cv_profile_processing(
    payload: CandidateCVSaveRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Enqueues candidate CV for asynchronous de-identification, duration conversion,
    and canonical skill extraction bounded by provider concurrency limits.
    """
    raw_text = normalize_resume_text(payload.raw_text.strip())
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CV content cannot be empty.",
        )

    task = IntakeEvaluationTaskModel(
        task_type="CV_EXTRACTION",
        raw_text=raw_text,
        title_hint="Candidate CV Profile",
        status="QUEUED",
        stage="QUEUED",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Dispatch to shared background worker queue
    background_tasks.add_task(process_evaluation_task, task_id=task.id)

    return CVTaskStatusResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        stage=task.stage,
        error_message=None,
        profile_id=None,
        created_at=task.created_at,
        completed_at=None,
        result=None,
    )


@router.post(
    "/parse-file",
    response_model=CVParsedDocumentResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_access)],
)
async def parse_cv_document_file(
    file: UploadFile = File(...),
):
    """
    Parses an uploaded resume file (.pdf, .docx, .doc, .txt) and returns extracted plain text.
    Does not save to database, enforcing a manual review step in the client.
    """
    filename = file.filename or "uploaded_resume.txt"

    # 10 MB size limit check
    MAX_FILE_SIZE = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 10 MB.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        extracted_text = parse_cv_document(filename, content)
        return CVParsedDocumentResponse(text=extracted_text, filename=filename)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error("Error parsing document file %s: %s", filename, err, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document file '{filename}': {err!s}",
        ) from err


@router.get("/tasks/{task_id}", response_model=CVTaskStatusResponse)
async def get_cv_task_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves status and stage of an asynchronous CV processing task."""
    stmt = select(IntakeEvaluationTaskModel).where(
        IntakeEvaluationTaskModel.id == task_id,
        IntakeEvaluationTaskModel.task_type == "CV_EXTRACTION",
    )
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CV processing task ID {task_id} not found.",
        )

    profile_id = None
    if task.result_json and isinstance(task.result_json, dict):
        profile_id = task.result_json.get("profile_id")

    return CVTaskStatusResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        stage=task.stage,
        error_message=task.error_message,
        profile_id=profile_id,
        created_at=task.created_at,
        completed_at=task.completed_at,
        result=task.result_json,
    )


@router.patch(
    "/{id}",
    response_model=CandidateCVResponse,
    dependencies=[Depends(verify_admin_access)],
)
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
        profile.extracted_skills = normalize_skills_list(payload.extracted_skills)
    if payload.years_of_experience is not None:
        profile.years_of_experience = payload.years_of_experience
    if payload.domain_experience is not None:
        profile.domain_experience = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in payload.domain_experience
        ]
        # Keep domain_expertise tag list synchronized
        profile.domain_expertise = [
            item["domain"] if isinstance(item, dict) else item.domain
            for item in payload.domain_experience
        ]
    elif payload.domain_expertise is not None:
        profile.domain_expertise = payload.domain_expertise
    if payload.spoken_languages is not None:
        profile.spoken_languages = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in payload.spoken_languages
        ]
    if payload.summary is not None:
        profile.summary = payload.summary

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_admin_access)],
)
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
