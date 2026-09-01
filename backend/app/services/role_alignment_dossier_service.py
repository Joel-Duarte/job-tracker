import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_factory import get_task_chat_model
from app.models.candidate_profile import CandidateCVModel
from app.models.role_alignment_dossier import RoleAlignmentDossierModel
from app.schemas.analytics import (
    RoleAlignmentDossierPayload,
    RoleAlignmentDossierResponse,
)
from app.services.analytics import get_role_alignment
from app.services.postgres_tracer import PostgresTracer

logger = logging.getLogger(__name__)


def _extract_json_block(text_content: str) -> dict[str, Any]:
    """Robustly extracts JSON object from LLM output."""
    text_content = text_content.strip()
    # Match markdown code fences ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text_content)
    if match:
        raw_json = match.group(1).strip()
    else:
        # Match outermost curly braces
        start = text_content.find("{")
        end = text_content.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_json = text_content[start : end + 1]
        else:
            raw_json = text_content

    return json.loads(raw_json)


SYSTEM_PROMPT = """You are an elite Executive Career Strategist and Technical Recruiter specializing in tech role positioning, ATS resume optimization, and high-stakes interview preparation.

Your task is to analyze a candidate's CV profile against aggregated market intelligence and requirements for a specific career track, and produce a high-impact, actionable Strategic Alignment Dossier.

You must output strictly valid JSON matching this exact structure:
{
  "executive_fit": {
    "market_competitiveness_rating": "EXCEPTIONAL" | "STRONG" | "MODERATE" | "EMERGING",
    "positioning_summary": "2-3 crisp sentences detailing candidate market positioning and key differentiation for this track.",
    "competitive_advantages": [
      "Key competitive strength 1",
      "Key competitive strength 2",
      "Key competitive strength 3"
    ],
    "primary_vulnerabilities": [
      "Top gap or vulnerability to proactively address 1",
      "Top gap or vulnerability to proactively address 2"
    ]
  },
  "bullet_rewrites": [
    {
      "original_bullet": "Full standalone CV bullet point or cohesive experience block (do NOT extract single sentences or fragments if they belong to a larger multi-sentence bullet). Provide 4 to 6 top high-leverage rewrites across the candidate profile.",
      "rewritten_bullet": "Consolidated, punchy rewrite elevating the entire entry using active power verbs, target track terminology, and quantified impact metrics (X-by-Y accomplishment format) that cleanly replaces the entire original block.",
      "target_competency": "e.g. Distributed Consensus / Real-Time Data Pipeline / Microservice Resilience",
      "impact_quantification": "e.g. Highlighted 40% latency reduction and scale metrics"
    }
  ],
  "talking_points": [
    {
      "topic_area": "e.g. System Scalability & High Availability",
      "technical_story_hook": "Specific narrative anchor from past experience illustrating technical depth",
      "key_takeaway": "The core engineering principle or business value demonstrated",
      "sample_questions": [
        "How do you handle cascading failures across distributed microservices?",
        "Describe a time you optimized an inefficient critical path."
      ]
    }
  ],
  "skill_bridge_roadmap": [
    {
      "skill_or_tool": "e.g. Kafka / gRPC / Terraform / Kubernetes",
      "category": "Core Infrastructure / Architecture / Cloud / Tooling",
      "rationale": "Why this skill bridges the gap for this specific track based on market demand",
      "learning_priority": "HIGH" | "MEDIUM" | "LOW",
      "recommended_actions": [
        "Concrete action 1: e.g. Build a hands-on event-driven prototype",
        "Concrete action 2: e.g. Review official architectural best practices"
      ]
    }
  ]
}
"""


async def get_role_alignment_dossier(
    db: AsyncSession,
    role_track: str = "all",
) -> RoleAlignmentDossierResponse | None:
    """
    Retrieves the existing AI Strategic Dossier from PostgreSQL if generated,
    or None if no dossier has been generated yet for this track.
    """
    norm_track = (role_track or "all").strip().lower()

    cv_stmt = select(CandidateCVModel).order_by(CandidateCVModel.id.desc()).limit(1)
    cv_res = await db.execute(cv_stmt)
    cv = cv_res.scalar_one_or_none()
    if not cv:
        return None

    existing_stmt = select(RoleAlignmentDossierModel).where(
        RoleAlignmentDossierModel.cv_id == cv.id,
        RoleAlignmentDossierModel.role_track == norm_track,
    )
    existing_res = await db.execute(existing_stmt)
    existing = existing_res.scalar_one_or_none()
    if not existing or not existing.ai_payload:
        return None

    try:
        payload = RoleAlignmentDossierPayload.model_validate(existing.ai_payload)
        return RoleAlignmentDossierResponse(
            id=existing.id,
            cv_id=existing.cv_id,
            role_track=existing.role_track,
            dossier=payload,
            model_name=existing.model_name,
            input_tokens=existing.input_tokens,
            output_tokens=existing.output_tokens,
            created_at=existing.created_at.isoformat(),
            updated_at=existing.updated_at.isoformat(),
        )
    except Exception as parse_err:
        logger.warning(
            "Failed validating cached dossier payload: %s",
            parse_err,
        )
        return None


async def enhance_role_alignment_dossier(
    db: AsyncSession,
    role_track: str = "all",
    force_regenerate: bool = True,
) -> RoleAlignmentDossierResponse:
    """
    Synthesizes a fresh AI Strategic Dossier using LLM task binding and PostgreSQL telemetry tracing.
    """
    norm_track = (role_track or "all").strip().lower()

    # 1. Fetch active Candidate CV
    cv_stmt = select(CandidateCVModel).order_by(CandidateCVModel.id.desc()).limit(1)
    cv_res = await db.execute(cv_stmt)
    cv = cv_res.scalar_one_or_none()

    if not cv:
        raise ValueError("Candidate CV profile not found. Please upload a CV first.")

    # 2. If not forcing regenerate, check if existing cached dossier is available
    if not force_regenerate:
        cached = await get_role_alignment_dossier(db, role_track=norm_track)
        if cached:
            return cached

    # 3. Gather track intelligence
    alignment_data = await get_role_alignment(db, role_track=norm_track, use_cache=True)

    # Format context for LLM
    cv_context = {
        "years_of_experience": cv.years_of_experience,
        "extracted_skills": cv.extracted_skills or [],
        "domain_expertise": cv.domain_expertise or [],
        "core_competencies": cv.core_competencies or [],
        "summary": cv.summary or "",
        "raw_text_snippet": cv.raw_text[:2500] if cv.raw_text else "",
    }

    track_context = {
        "target_track": norm_track,
        "total_analyzed_jobs": alignment_data.total_analyzed_jobs,
        "top_vocabulary_shifts": [
            {
                "cv_term": s.cv_term,
                "jd_term": s.jd_term,
                "frequency": s.frequency_count,
                "rationale": s.rationale,
            }
            for s in alignment_data.vocabulary_shifts[:15]
        ],
        "top_bullet_reframes": [
            {
                "original_bullet": b.original_bullet,
                "suggested_rewrite": b.suggested_rewrite,
                "reason": b.reason,
            }
            for b in alignment_data.bullet_reframes[:15]
        ],
    }

    user_prompt = f"""Target Role Track: {norm_track.upper()}

Candidate CV Profile:
{json.dumps(cv_context, indent=2)}

Market Intelligence & Track Requirements:
{json.dumps(track_context, indent=2)}

Generate the comprehensive Strategic Alignment Dossier in valid JSON."""

    # 4. Invoke LLM with telemetry
    chat_model = await get_task_chat_model(task_type="ROLE_ALIGNMENT_DOSSIER", db=db)
    tracer = PostgresTracer()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    response = await chat_model.ainvoke(
        messages,
        config={"callbacks": [tracer]},
    )

    response_text = getattr(response, "content", "")
    if isinstance(response_text, list):
        response_text = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in response_text
        )

    parsed_json = _extract_json_block(response_text)
    dossier_payload = RoleAlignmentDossierPayload.model_validate(parsed_json)

    # Extract token metrics if available
    usage = getattr(response, "usage_metadata", None) or {}
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
    model_name = getattr(chat_model, "model_name", None) or getattr(
        chat_model, "model", "default"
    )

    # 5. Persist or Update in Database
    upsert_stmt = select(RoleAlignmentDossierModel).where(
        RoleAlignmentDossierModel.cv_id == cv.id,
        RoleAlignmentDossierModel.role_track == norm_track,
    )
    upsert_res = await db.execute(upsert_stmt)
    dossier_record = upsert_res.scalar_one_or_none()

    if not dossier_record:
        dossier_record = RoleAlignmentDossierModel(
            cv_id=cv.id,
            role_track=norm_track,
            ai_payload=dossier_payload.model_dump(),
            model_name=str(model_name),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        db.add(dossier_record)
    else:
        dossier_record.ai_payload = dossier_payload.model_dump()
        dossier_record.model_name = str(model_name)
        dossier_record.input_tokens = input_tokens
        dossier_record.output_tokens = output_tokens
        dossier_record.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(dossier_record)

    return RoleAlignmentDossierResponse(
        id=dossier_record.id,
        cv_id=dossier_record.cv_id,
        role_track=dossier_record.role_track,
        dossier=dossier_payload,
        model_name=dossier_record.model_name,
        input_tokens=dossier_record.input_tokens,
        output_tokens=dossier_record.output_tokens,
        created_at=dossier_record.created_at.isoformat(),
        updated_at=dossier_record.updated_at.isoformat(),
    )
