import base64
import json
import logging
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.llm_factory import get_task_chat_model, strip_reasoning_tags
from app.core.prompts import DEFAULT_PROMPTS
from app.models.applications import ApplicationModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.system_design import (
    SystemDesignChallengeModel,
    SystemDesignSessionModel,
)
from app.schemas.system_design import (
    ArchitectureReviewSchema,
    DiagramRevisionRead,
    FinalEvaluationSchema,
    FrontierEvaluationPacketRead,
    RequirementsLedgerSchema,
    RequirementsLedgerUpdateRequest,
    RubricDimensionScore,
    SystemDesignChallengeCreate,
    SystemDesignChallengeGenerateRequest,
    SystemDesignChallengeUpdate,
)
from app.services.interview_simulator_service import (
    _format_prompt_from_db,
    _invoke_llm_adaptive,
)
from app.services.postgres_tracer import PostgresTracer
from app.services.system_design_seed import seed_system_design_challenges

logger = logging.getLogger(__name__)

# Shared disk storage root for binary diagrams (backend/data/system_design locally,
# /app/data/system_design inside container).
SYSTEM_DESIGN_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "system_design"
MAX_DIAGRAM_BYTES = 10 * 1024 * 1024  # 10 MB

ARCHITECTURE_REVIEW_JSON_INSTRUCTIONS = """
Respond ONLY with a valid JSON object matching this exact schema (no markdown fences):
{
  "interpreted_components": ["<component observed in diagram>"],
  "interpreted_data_flows": ["<data or request flow observed>"],
  "visual_clarifications_needed": ["<illegible label, missing arrow direction, or notation ambiguity (do NOT score as a flaw)>"],
  "strengths": ["<sound architectural choice aligned with requirements>"],
  "missing_components": ["<required component omitted from diagram>"],
  "bottlenecks_and_spofs": ["<single point of failure or scaling bottleneck>"],
  "unnecessary_complexity": ["<over-engineered technology unjustified by locked scale>"],
  "requirement_gaps": ["<locked functional or non-functional requirement not yet addressed>"],
  "overall_impression": "<concise 2-3 sentence architectural summary>",
  "suggested_defence_topics": ["<targeted defence probing question 1>", "<question 2>"]
}
"""

DEFENCE_SYSTEM_PROMPT = """You are conducting Stage E (Interactive Architecture Defence) for the System Design challenge: {challenge_title}.

MODE INSTRUCTION:
{mode_instruction}

LOCKED REQUIREMENTS LEDGER:
{requirements_ledger_json}

LATEST ARCHITECTURE REVIEW FINDINGS:
{latest_review_json}

HIDDEN INTERVIEWER BRIEF (GROUND TRUTH — DO NOT DUMP RAW JSON):
{hidden_brief_json}

DEFENCE INTERVIEWER RULES:
1. Probe trade-offs, failure modes, data consistency guarantees, single points of failure, and scaling bottlenecks from the candidate's submitted diagram and architecture review.
2. Ask ONE focused probing question per turn so the candidate can justify their engineering reasoning clearly.
3. Acknowledge valid trade-off defences concisely when earned, and challenge hand-waved answers cleanly.
4. Keep responses concise (2-5 sentences)."""

DEFAULT_RUBRIC_DIMENSIONS: list[str] = [
    "Requirements Clarity",
    "Scope & Prioritization",
    "Back-of-the-Envelope Estimation",
    "API & Interface Design",
    "Data Model & Storage Choice",
    "High-Level Architecture",
    "Scalability & Partitioning",
    "Reliability & Fault Tolerance",
    "Caching & Latency Optimization",
    "Right-Sizing & Simplicity (YAGNI)",
    "Trade-off Justification",
    "Defence Communication Under Pressure",
]

VALID_READINESS_RATINGS = (
    "NEEDS_PRACTICE",
    "DEVELOPING",
    "INTERVIEW_READY",
    "STRONG_HIRE",
)

FINAL_EVALUATION_PROMPT = """You are producing the Stage F evidence-based final interview evaluation for System Design challenge: {challenge_title}.

HIDDEN INTERVIEWER BRIEF (GROUND TRUTH RUBRIC):
{hidden_brief_json}

STRICT EVIDENCE RULES:
1. Score the candidate ONLY on demonstrated evidence in their requirements conversation, locked requirements ledger, submitted diagram reviews, and defence responses below.
2. EVERY rubric item MUST include a concrete `evidence` quote or specific observation referencing the candidate's transcript turns, locked ledger items, or diagram components (minimum 5 non-whitespace characters; never generic filler).
3. Evaluate across the 12 core dimensions:
{dimensions_list}
4. Respond ONLY with a valid JSON object matching this exact schema (no markdown fences):
{{
  "overall_score": 0,
  "readiness_rating": "NEEDS_PRACTICE | DEVELOPING | INTERVIEW_READY | STRONG_HIRE",
  "executive_summary": "<2-4 sentence overall assessment>",
  "rubric_scores": [
    {{
      "dimension": "<one of the 12 rubric dimensions>",
      "score": 1,
      "evidence": "<concrete observation from ledger, diagram review, or transcript>",
      "critique": "<specific strength or gap and why it earned this score>"
    }}
  ],
  "key_strengths": ["<evidence-backed strength>"],
  "critical_gaps": ["<evidence-backed gap>"],
  "recommended_next_steps": ["<concrete practice or revision action>"]
}}
"""

MODE_INSTRUCTIONS: dict[str, str] = {
    "ADAPTIVE": (
        "ADAPTIVE INTERVIEWER MODE (Realistic Interview + On-Demand Coaching): "
        "Conduct a realistic Staff-level system design interview where the candidate leads. "
        "Do NOT volunteer unasked scale numbers, hints, or solutions during standard Q&A. "
        "HOWEVER, when the candidate explicitly asks for help, a hint, or guidance (or when "
        "a coaching hint is requested for a turn), respond with a brief, constructive nudge "
        "pointing out what constraint, bottleneck, or trade-off to think about next without "
        "handing over the full answer."
    ),
    "INTERVIEW": (
        "INTERVIEW MODE (Strict Bar Raiser): Conduct a realistic Staff-level system design interview. "
        "Never volunteer unasked scale figures, hints, or expected architectural components. "
        "Answer only what the candidate explicitly asks, challenge vague assumptions, and ask them "
        "to justify constraints or estimate numbers."
    ),
    "PRACTICE": (
        "PRACTICE / COACHING MODE (Collaborative Mentor): Help the candidate practice structured requirements "
        "discovery while still letting them lead. Answer clarifying questions accurately, and if they ask for "
        "hints or overlook essential constraint areas (such as read/write ratio, latency SLA, durability, or scale bounds), "
        "provide brief, constructive nudges on what to consider next."
    ),
}

CUSTOM_CHALLENGE_GENERATE_PROMPT = """You are a Staff System Design Interview Architect designing a tailored system design interview challenge.

Respond ONLY with a valid JSON object matching this exact schema (no markdown fences):
{{
  "title": "<concise realistic challenge title, e.g. Design a Real-Time Fraud Scoring Pipeline>",
  "category": "<DISTRIBUTED_SYSTEMS | DATA_INFRASTRUCTURE | REALTIME_COMMUNICATION | STREAMING_MEDIA | STORAGE_SYSTEMS | AI_PLATFORM>",
  "difficulty": "{difficulty}",
  "prompt_summary": "<1-2 sentence scenario summary shown on the challenge card>",
  "initial_prompt": "<2-4 sentence intentionally broad opening interview prompt matching how a real interviewer opens the session without leaking scale numbers or answers>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"],
  "interviewer_brief": {{
    "hidden_context": {{
      "scale_targets": "<concrete hidden DAU/QPS/storage/latency numbers revealed only when asked>",
      "key_constraints": ["<constraint 1>", "<constraint 2>"]
    }},
    "expected_components": ["<core component 1>", "<core component 2>", "<core component 3>"],
    "over_engineering_traps": ["<unjustified complexity trap 1>"],
    "defence_questions": [
      "<challenging architecture defence question 1>",
      "<challenging architecture defence question 2>"
    ]
  }}
}}
"""

_HINT_REQUEST_RE = re.compile(
    r"\b(hint|coach me|help me|nudge|what should i ask|give me a clue|i'?m stuck|stuck on)\b",
    re.IGNORECASE,
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "custom-challenge"


def _is_hint_request(message_text: str, request_hint: bool = False) -> bool:
    return bool(request_hint or _HINT_REQUEST_RE.search(message_text or ""))


async def _fetch_web_grounding_snippets(
    db: AsyncSession, query: str, max_results: int = 4
) -> str:
    """Fetch optional web search snippets without breaking offline/local execution."""
    cleaned_query = " ".join((query or "").split())[:220]
    if not cleaned_query:
        return ""
    try:
        from app.services.web_search import search_web

        results = await search_web(cleaned_query, max_results=max_results, db=db)
    except Exception as exc:
        logger.warning("Web search grounding skipped (%s): %s", cleaned_query, exc)
        return ""

    lines: list[str] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        url = str(item.get("url") or "").strip()
        if snippet or title:
            suffix = f" ({url})" if url else ""
            lines.append(f"- {title}: {snippet}{suffix}".strip())
    return "\n".join(lines)


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object from raw LLM text or fenced markdown pasted from external models."""
    cleaned = strip_reasoning_tags(raw_text or "").strip()
    if not cleaned:
        raise ValueError("Empty response cannot be parsed as JSON.")

    try:
        parsed = JsonOutputParser().parse(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE):
        try:
            candidate = json.loads(block.strip())
            if isinstance(candidate, dict):
                return candidate
        except Exception:
            continue

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            candidate = json.loads(cleaned[first_brace : last_brace + 1])
            if isinstance(candidate, dict):
                return candidate
        except Exception:
            pass

    raise ValueError("Could not extract a valid JSON scorecard object from response.")


REQUIREMENTS_EXTRACTION_PROMPT = """You are extracting structured requirements from a System Design interview requirements-discovery conversation.

STRICT GROUNDING RULES:
1. Extract ONLY functional requirements, non-functional requirements, scale estimates, out-of-scope decisions, and notes that were explicitly discussed, clarified, or agreed upon in the conversation below or already recorded in the existing ledger.
2. Do NOT copy hidden metrics or unmentioned requirements from external knowledge.
3. Preserve still-valid items from the existing ledger unless contradicted or refined by later turns.
4. Respond ONLY with a valid JSON object matching this exact schema (no markdown fences):
{{
  "functional_requirements": ["<item 1>", "<item 2>"],
  "non_functional_requirements": ["<SLA/availability/consistency requirement>"],
  "scale_estimates": {{
    "<metric_name>": "<estimate string>"
  }},
  "out_of_scope": ["<excluded feature>"],
  "notes": "<concise summary note>"
}}

Challenge: {challenge_title}

Existing Ledger:
{existing_ledger_json}

Requirements Transcript:
{transcript_text}
"""


def _detect_image_format(data: bytes) -> tuple[str, str]:
    """Validate image magic bytes and return ``(mime_type, file_extension)``."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("image/png", "png")
    if data.startswith(b"\xff\xd8\xff"):
        return ("image/jpeg", "jpg")
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("image/webp", "webp")
    raise ValueError(
        "Unsupported image format. Please upload a PNG, JPEG, or WebP image."
    )


def _build_chat_messages(
    system_prompt: str, transcript: list[dict[str, Any]]
) -> list[Any]:
    messages: list[Any] = [SystemMessage(content=system_prompt)]
    for turn in transcript:
        content = str(turn.get("content", ""))
        if turn.get("role") == "interviewer":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def _extract_text_content(content: Any) -> str:
    """Normalizes string or block-list LLM content into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in out:
                out.append(text)
        return out
    return []


def _normalize_scale_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(k).strip(): str(v).strip()
        for k, v in value.items()
        if str(k).strip() and v is not None and str(v).strip()
    }


def _build_session_fallback_evidence(session: SystemDesignSessionModel) -> str:
    ledger = session.requirements_ledger or {}
    req_turns = sum(
        1
        for t in (session.requirements_transcript or [])
        if t.get("role") == "candidate"
    )
    def_turns = sum(
        1 for t in (session.defence_transcript or []) if t.get("role") == "candidate"
    )
    diagrams_count = len(session.diagrams_metadata or [])
    reviews_count = len(session.architecture_reviews or [])
    fn_count = len(ledger.get("functional_requirements") or [])
    locked_label = "locked" if ledger.get("is_locked") else "unlocked"
    return (
        f"Session {session.id} evidence: {req_turns} requirements turns, "
        f"{fn_count} functional requirements ({locked_label} ledger), "
        f"{diagrams_count} diagram revision(s), {reviews_count} review(s), "
        f"and {def_turns} defence response(s)."
    )


def _derive_readiness_rating(overall_score: float) -> str:
    if overall_score >= 88.0:
        return "STRONG_HIRE"
    if overall_score >= 70.0:
        return "INTERVIEW_READY"
    if overall_score >= 50.0:
        return "DEVELOPING"
    return "NEEDS_PRACTICE"


def _normalize_final_evaluation(
    raw_data: dict[str, Any], session: SystemDesignSessionModel
) -> dict[str, Any]:
    fallback_evidence = _build_session_fallback_evidence(session)
    raw_scores = raw_data.get("rubric_scores")
    normalized_scores: list[RubricDimensionScore] = []

    if isinstance(raw_scores, list):
        for idx, item in enumerate(raw_scores):
            if not isinstance(item, dict):
                continue
            dimension = str(
                item.get("dimension")
                or DEFAULT_RUBRIC_DIMENSIONS[idx % len(DEFAULT_RUBRIC_DIMENSIONS)]
            ).strip()
            try:
                raw_score = int(round(float(item.get("score", 3))))
            except (TypeError, ValueError):
                raw_score = 3
            clamped_score = max(1, min(5, raw_score))

            raw_evidence = str(item.get("evidence") or "").strip()
            evidence_text = (
                raw_evidence if len(raw_evidence) >= 5 else fallback_evidence
            )

            critique_text = str(
                item.get("critique")
                or item.get("rationale")
                or f"Evaluated at score {clamped_score}/5 based on session evidence."
            ).strip()

            normalized_scores.append(
                RubricDimensionScore(
                    dimension=dimension or f"Dimension {idx + 1}",
                    score=clamped_score,
                    evidence=evidence_text,
                    critique=critique_text,
                )
            )

    if not normalized_scores:
        for dim in DEFAULT_RUBRIC_DIMENSIONS:
            normalized_scores.append(
                RubricDimensionScore(
                    dimension=dim,
                    score=3,
                    evidence=fallback_evidence,
                    critique="Baseline score inferred from recorded session artifacts.",
                )
            )

    raw_overall = raw_data.get("overall_score")
    computed_overall = round(
        (sum(s.score for s in normalized_scores) / (len(normalized_scores) * 5))
        * 100.0,
        1,
    )
    try:
        overall_score = (
            float(raw_overall) if raw_overall is not None else computed_overall
        )
    except (TypeError, ValueError):
        overall_score = computed_overall
    overall_score = max(0.0, min(100.0, round(overall_score, 1)))

    raw_rating = str(raw_data.get("readiness_rating") or "").strip().upper()
    readiness_rating = (
        raw_rating
        if raw_rating in VALID_READINESS_RATINGS
        else _derive_readiness_rating(overall_score)
    )

    executive_summary = str(
        raw_data.get("executive_summary")
        or (
            f"Final system design evaluation completed with {overall_score:.0f}/100 "
            f"({readiness_rating}) across {len(normalized_scores)} rubric dimensions."
        )
    ).strip()

    key_strengths = _normalize_string_list(raw_data.get("key_strengths")) or [
        "Engaged in iterative requirements and architectural reasoning."
    ]
    critical_gaps = _normalize_string_list(raw_data.get("critical_gaps")) or [
        "Continue quantifying bottleneck thresholds and failure recovery playbooks."
    ]
    recommended_next_steps = _normalize_string_list(
        raw_data.get("recommended_next_steps")
    ) or [
        "Revise the architecture diagram to explicitly annotate replication and backpressure controls."
    ]

    validated = FinalEvaluationSchema(
        overall_score=overall_score,
        readiness_rating=readiness_rating,  # type: ignore[arg-type]
        executive_summary=executive_summary,
        rubric_scores=normalized_scores,
        key_strengths=key_strengths,
        critical_gaps=critical_gaps,
        recommended_next_steps=recommended_next_steps,
    )
    return validated.model_dump()


class SystemDesignService:
    """Stateless domain service managing System Design Lab lifecycle in PostgreSQL."""

    @staticmethod
    async def _ensure_challenges_seeded(db: AsyncSession) -> None:
        count = (
            await db.execute(
                select(func.count()).select_from(SystemDesignChallengeModel)
            )
        ).scalar_one()
        if count == 0:
            await seed_system_design_challenges(db)

    @staticmethod
    async def list_challenges(
        db: AsyncSession,
        category: str | None = None,
        difficulty: str | None = None,
    ) -> list[SystemDesignChallengeModel]:
        await SystemDesignService._ensure_challenges_seeded(db)
        stmt = select(SystemDesignChallengeModel)
        if category:
            stmt = stmt.where(SystemDesignChallengeModel.category == category)
        if difficulty:
            stmt = stmt.where(SystemDesignChallengeModel.difficulty == difficulty)
        stmt = stmt.order_by(SystemDesignChallengeModel.id.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_challenge(
        db: AsyncSession, slug_or_id: str | int
    ) -> SystemDesignChallengeModel:
        await SystemDesignService._ensure_challenges_seeded(db)
        if isinstance(slug_or_id, int) or (
            isinstance(slug_or_id, str) and slug_or_id.isdigit()
        ):
            stmt = select(SystemDesignChallengeModel).where(
                SystemDesignChallengeModel.id == int(slug_or_id)
            )
        else:
            stmt = select(SystemDesignChallengeModel).where(
                SystemDesignChallengeModel.slug == str(slug_or_id)
            )
        challenge = (await db.execute(stmt)).scalar_one_or_none()
        if not challenge:
            raise ValueError(f"System design challenge '{slug_or_id}' not found.")
        return challenge

    @staticmethod
    async def _unique_challenge_slug(db: AsyncSession, base_title: str) -> str:
        base_slug = _slugify(base_title)
        candidate = base_slug
        counter = 1
        while True:
            existing = (
                await db.execute(
                    select(SystemDesignChallengeModel.id).where(
                        SystemDesignChallengeModel.slug == candidate
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                return candidate
            counter += 1
            candidate = f"{base_slug}-{counter}"

    @staticmethod
    async def create_custom_challenge(
        db: AsyncSession, payload: SystemDesignChallengeCreate
    ) -> SystemDesignChallengeModel:
        """Create a user-authored custom System Design challenge."""
        await SystemDesignService._ensure_challenges_seeded(db)
        slug = await SystemDesignService._unique_challenge_slug(db, payload.title)
        expected_components = _normalize_string_list(payload.expected_components)
        tags = _normalize_string_list(payload.tags) or ["custom"]

        interviewer_brief = {
            "hidden_context": {
                "scale_notes": payload.scale_notes.strip()
                or "Clarify expected DAU, QPS, storage retention, and p99 latency bounds.",
            },
            "expected_components": expected_components
            or ["API Gateway", "Core Application Service", "Primary Data Store"],
            "over_engineering_traps": [],
            "defence_questions": [
                "Walk me through your primary bottleneck under 10x peak load.",
                "Which component in your design is the highest-risk single point of failure and how do you mitigate it?",
            ],
        }

        challenge = SystemDesignChallengeModel(
            slug=slug,
            title=payload.title.strip(),
            category=payload.category.strip().upper() or "DISTRIBUTED_SYSTEMS",
            difficulty=payload.difficulty.strip().upper() or "MEDIUM",
            prompt_summary=payload.prompt_summary.strip(),
            initial_prompt=payload.initial_prompt.strip(),
            tags=tags,
            interviewer_brief=interviewer_brief,
            is_builtin=False,
        )
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)
        return challenge

    @staticmethod
    async def generate_custom_challenge(
        db: AsyncSession, payload: SystemDesignChallengeGenerateRequest
    ) -> SystemDesignChallengeModel:
        """Use AI (plus optional tracked Job Application & Web Search) to generate a custom challenge."""
        await SystemDesignService._ensure_challenges_seeded(db)
        topic_text = payload.topic.strip()
        app_context_parts: list[str] = []
        search_seed = topic_text

        if payload.application_id is not None:
            app_stmt = (
                select(ApplicationModel)
                .options(
                    selectinload(ApplicationModel.company),
                    selectinload(ApplicationModel.job_posting),
                )
                .where(ApplicationModel.id == payload.application_id)
            )
            application = (await db.execute(app_stmt)).scalar_one_or_none()
            if not application:
                raise ValueError(f"Application {payload.application_id} not found.")
            company_name = (
                application.company.name if application.company else "Target Company"
            )
            role_title = application.position or "Software Engineer"
            search_seed = f"{company_name} {role_title} {topic_text}".strip()
            app_context_parts.append(
                f"Target Role: {role_title} at {company_name} (status: {application.status})"
            )
            if application.job_posting:
                skills = application.job_posting.required_skills or []
                if skills:
                    app_context_parts.append(
                        f"Required Skills: {', '.join(str(s) for s in skills[:12])}"
                    )
                if application.job_posting.description_markdown:
                    app_context_parts.append(
                        "Job Description Excerpt:\n"
                        + application.job_posting.description_markdown[:1500]
                    )

        if not topic_text and not app_context_parts:
            raise ValueError(
                "Provide either a challenge topic or link an application_id."
            )

        difficulty = payload.difficulty.strip().upper() or "MEDIUM"
        web_snippets = ""
        if payload.use_web_search and search_seed:
            web_snippets = await _fetch_web_grounding_snippets(
                db,
                f"{search_seed} system design architecture engineering blog scale",
            )

        sys_prompt = CUSTOM_CHALLENGE_GENERATE_PROMPT.format(difficulty=difficulty)
        user_sections = []
        if topic_text:
            user_sections.append(f"Requested Topic / Scenario:\n{topic_text}")
        if app_context_parts:
            user_sections.append(
                "Job Application Context:\n" + "\n".join(app_context_parts)
            )
        if web_snippets:
            user_sections.append(
                "Recent Web Search Context (ground engineering constraints cleanly):\n"
                + web_snippets
            )

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(
            db, task_type="SYSTEM_DESIGN_INTERVIEWER"
        )
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(content="\n\n".join(user_sections)),
            ],
            tracer,
            db,
        )
        raw_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        parsed = _extract_json_object(raw_text)

        title = str(
            parsed.get("title")
            or (
                f"Design: {topic_text[:60]}"
                if topic_text
                else "Tailored Role System Design"
            )
        ).strip()
        slug = await SystemDesignService._unique_challenge_slug(db, title)
        raw_brief = parsed.get("interviewer_brief")
        interviewer_brief = (
            dict(raw_brief)
            if isinstance(raw_brief, dict)
            else {
                "hidden_context": {
                    "scale_targets": "Establish DAU, QPS, latency SLA, and fault tolerance targets."
                },
                "expected_components": [
                    "API Gateway",
                    "Core Service",
                    "Primary Storage",
                ],
                "over_engineering_traps": [],
                "defence_questions": [
                    "How does your design degrade gracefully when downstream storage slows down?"
                ],
            }
        )

        challenge = SystemDesignChallengeModel(
            slug=slug,
            title=title[:200],
            category=str(parsed.get("category") or "DISTRIBUTED_SYSTEMS")
            .strip()
            .upper(),
            difficulty=str(parsed.get("difficulty") or difficulty).strip().upper(),
            prompt_summary=str(
                parsed.get("prompt_summary")
                or topic_text
                or "Custom AI-generated system design interview scenario."
            ).strip(),
            initial_prompt=str(
                parsed.get("initial_prompt")
                or f"Design {title}. Start by clarifying requirements, expected scale, and key constraints."
            ).strip(),
            tags=_normalize_string_list(parsed.get("tags")) or ["ai-generated"],
            interviewer_brief=interviewer_brief,
            is_builtin=False,
        )
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)
        return challenge

    @staticmethod
    async def update_challenge(
        db: AsyncSession, challenge_id: int, payload: SystemDesignChallengeUpdate
    ) -> SystemDesignChallengeModel:
        """Update an existing System Design challenge (built-in or custom)."""
        challenge = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.id == challenge_id
                )
            )
        ).scalar_one_or_none()
        if not challenge:
            raise LookupError(f"System design challenge {challenge_id} not found.")

        challenge.title = payload.title.strip()
        challenge.category = payload.category.strip().upper() or "DISTRIBUTED_SYSTEMS"
        challenge.difficulty = payload.difficulty.strip().upper() or "MEDIUM"
        challenge.prompt_summary = payload.prompt_summary.strip()
        challenge.initial_prompt = payload.initial_prompt.strip()
        challenge.tags = _normalize_string_list(payload.tags) or ["custom"]

        brief = dict(challenge.interviewer_brief or {})
        expected = _normalize_string_list(payload.expected_components)
        if expected:
            brief["expected_components"] = expected
        if payload.scale_notes.strip():
            hidden = dict(brief.get("hidden_context") or {})
            hidden["scale_notes"] = payload.scale_notes.strip()
            brief["hidden_context"] = hidden
        challenge.interviewer_brief = brief
        flag_modified(challenge, "interviewer_brief")

        await db.commit()
        await db.refresh(challenge)
        return challenge

    @staticmethod
    async def reset_default_challenges(
        db: AsyncSession,
    ) -> list[SystemDesignChallengeModel]:
        """Restore and reset the 8 built-in challenges while preserving custom challenges."""
        await seed_system_design_challenges(db)
        return await SystemDesignService.list_challenges(db)

    @staticmethod
    async def delete_custom_challenge(db: AsyncSession, challenge_id: int) -> None:
        """Delete a system design challenge and any linked sessions."""
        challenge = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.id == challenge_id
                )
            )
        ).scalar_one_or_none()
        if not challenge:
            raise ValueError(f"System design challenge {challenge_id} not found.")

        # Remove linked sessions cleanly before deleting because FK uses ON DELETE RESTRICT.
        linked_sessions = (
            (
                await db.execute(
                    select(SystemDesignSessionModel).where(
                        SystemDesignSessionModel.challenge_id == challenge_id
                    )
                )
            )
            .scalars()
            .all()
        )
        for session in linked_sessions:
            await db.delete(session)
            session_dir = SYSTEM_DESIGN_DATA_DIR / f"session_{session.id}"
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)

        await db.flush()
        await db.delete(challenge)
        await db.commit()

    @staticmethod
    async def start_session(
        db: AsyncSession,
        challenge_id: int,
        application_id: int | None = None,
        mode: str = "ADAPTIVE",
    ) -> SystemDesignSessionModel:
        if mode not in MODE_INSTRUCTIONS:
            raise ValueError(
                f"Invalid mode '{mode}'. Expected ADAPTIVE, INTERVIEW, or PRACTICE."
            )

        await SystemDesignService._ensure_challenges_seeded(db)
        challenge = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.id == challenge_id
                )
            )
        ).scalar_one_or_none()
        if not challenge:
            raise ValueError(f"System design challenge {challenge_id} not found.")

        initial_turn = {
            "turn_index": 1,
            "role": "interviewer",
            "content": challenge.initial_prompt,
            "stage": "REQUIREMENTS",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        session = SystemDesignSessionModel(
            challenge_id=challenge.id,
            application_id=application_id,
            mode=mode,
            stage="REQUIREMENTS",
            status="IN_PROGRESS",
            requirements_transcript=[initial_turn],
            requirements_ledger=RequirementsLedgerSchema().model_dump(),
        )
        db.add(session)
        await db.commit()
        return await SystemDesignService.get_session(db, session.id)

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        application_id: int | None = None,
        status: str | None = None,
    ) -> list[SystemDesignSessionModel]:
        stmt = select(SystemDesignSessionModel).options(
            selectinload(SystemDesignSessionModel.challenge)
        )
        if application_id is not None:
            stmt = stmt.where(SystemDesignSessionModel.application_id == application_id)
        if status:
            stmt = stmt.where(SystemDesignSessionModel.status == status)
        stmt = stmt.order_by(
            SystemDesignSessionModel.updated_at.desc(),
            SystemDesignSessionModel.id.desc(),
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_session(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        stmt = (
            select(SystemDesignSessionModel)
            .options(selectinload(SystemDesignSessionModel.challenge))
            .where(SystemDesignSessionModel.id == session_id)
        )
        session = (await db.execute(stmt)).scalar_one_or_none()
        if not session:
            raise ValueError(f"System design session {session_id} not found.")
        return session

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: int) -> None:
        session = await SystemDesignService.get_session(db, session_id)
        await db.delete(session)
        await db.commit()

        session_dir = SYSTEM_DESIGN_DATA_DIR / f"session_{session_id}"
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)

    @staticmethod
    async def update_session_mode(
        db: AsyncSession, session_id: int, mode: str
    ) -> SystemDesignSessionModel:
        if mode not in MODE_INSTRUCTIONS:
            raise ValueError(
                f"Invalid mode '{mode}'. Expected ADAPTIVE, INTERVIEW, or PRACTICE."
            )
        session = await SystemDesignService.get_session(db, session_id)
        session.mode = mode
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def send_requirements_message(
        db: AsyncSession,
        session_id: int,
        message_text: str,
        request_hint: bool = False,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService.get_session(db, session_id)
        challenge = session.challenge
        assisted = _is_hint_request(message_text, request_hint)

        transcript = list(session.requirements_transcript or [])
        candidate_turn = {
            "turn_index": len(transcript) + 1,
            "role": "candidate",
            "content": message_text.strip(),
            "stage": session.stage,
            "assisted": assisted,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        transcript.append(candidate_turn)

        mode_instruction = MODE_INSTRUCTIONS.get(
            session.mode, MODE_INSTRUCTIONS["ADAPTIVE"]
        )
        if assisted:
            mode_instruction += (
                "\nCOACHING HINT REQUESTED ON THIS TURN: The candidate explicitly asked "
                "for a hint or guidance. Provide a concise, encouraging coaching nudge "
                "pointing out what requirement, scale metric, or constraint to examine next "
                "without handing over the complete solution."
            )

        sys_prompt = await _format_prompt_from_db(
            db,
            "system_design_interviewer",
            DEFAULT_PROMPTS["system_design_interviewer"],
            mode_instruction=mode_instruction,
            challenge_title=challenge.title,
            initial_prompt=challenge.initial_prompt,
            hidden_brief_json=json.dumps(challenge.interviewer_brief or {}, indent=2),
            stage=session.stage,
            requirements_ledger_json=json.dumps(
                session.requirements_ledger or {}, indent=2
            ),
        )

        messages = _build_chat_messages(sys_prompt, transcript)

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(
            db, task_type="SYSTEM_DESIGN_INTERVIEWER"
        )
        llm_res = await _invoke_llm_adaptive(chat_model, messages, tracer, db)
        reply_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        if not reply_text:
            reply_text = "Could you clarify the specific constraint or assumption you want to explore?"

        interviewer_turn = {
            "turn_index": len(transcript) + 1,
            "role": "interviewer",
            "content": reply_text,
            "stage": session.stage,
            "assisted": assisted,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        transcript.append(interviewer_turn)

        session.requirements_transcript = transcript
        flag_modified(session, "requirements_transcript")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def extract_requirements_ledger(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService.get_session(db, session_id)
        challenge = session.challenge
        existing_ledger = session.requirements_ledger or {}

        transcript_lines = [
            f"[{t.get('role', 'unknown')}]: {t.get('content', '')}"
            for t in (session.requirements_transcript or [])
        ]
        prompt = REQUIREMENTS_EXTRACTION_PROMPT.format(
            challenge_title=challenge.title,
            existing_ledger_json=json.dumps(existing_ledger, indent=2),
            transcript_text="\n".join(transcript_lines) or "(No turns recorded yet.)",
        )

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(
            db, task_type="SYSTEM_DESIGN_INTERVIEWER"
        )
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=prompt),
                HumanMessage(
                    content="Extract the discussed requirements ledger JSON now."
                ),
            ],
            tracer,
            db,
        )

        raw_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        parsed = JsonOutputParser().parse(raw_text)
        if not isinstance(parsed, dict):
            parsed = {}

        ledger = RequirementsLedgerSchema(
            functional_requirements=_normalize_string_list(
                parsed.get("functional_requirements")
            ),
            non_functional_requirements=_normalize_string_list(
                parsed.get("non_functional_requirements")
            ),
            scale_estimates=_normalize_scale_dict(parsed.get("scale_estimates")),
            out_of_scope=_normalize_string_list(parsed.get("out_of_scope")),
            notes=str(
                parsed.get("notes") or existing_ledger.get("notes") or ""
            ).strip(),
            is_locked=bool(existing_ledger.get("is_locked", False)),
        )

        session.requirements_ledger = ledger.model_dump()
        flag_modified(session, "requirements_ledger")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def update_requirements_ledger(
        db: AsyncSession,
        session_id: int,
        payload: RequirementsLedgerUpdateRequest,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService.get_session(db, session_id)

        ledger = RequirementsLedgerSchema(
            functional_requirements=_normalize_string_list(
                payload.functional_requirements
            ),
            non_functional_requirements=_normalize_string_list(
                payload.non_functional_requirements
            ),
            scale_estimates=_normalize_scale_dict(payload.scale_estimates),
            out_of_scope=_normalize_string_list(payload.out_of_scope),
            notes=payload.notes.strip(),
            is_locked=payload.is_locked,
        )
        session.requirements_ledger = ledger.model_dump()

        if payload.is_locked and session.stage == "REQUIREMENTS":
            session.stage = "DESIGN"
        elif (
            not payload.is_locked
            and session.stage == "DESIGN"
            and not session.diagrams_metadata
        ):
            session.stage = "REQUIREMENTS"

        flag_modified(session, "requirements_ledger")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def upload_diagram(
        db: AsyncSession,
        session_id: int,
        file_bytes: bytes,
        notes: str = "",
    ) -> SystemDesignSessionModel:
        if not file_bytes:
            raise ValueError("Uploaded diagram file is empty.")
        if len(file_bytes) > MAX_DIAGRAM_BYTES:
            raise ValueError("Diagram exceeds maximum size of 10 MB.")

        mime_type, ext = _detect_image_format(file_bytes)
        session = await SystemDesignService.get_session(db, session_id)

        diagrams = list(session.diagrams_metadata or [])
        version = max((int(d.get("version", 0)) for d in diagrams), default=0) + 1
        filename = f"v{version}.{ext}"

        session_dir = SYSTEM_DESIGN_DATA_DIR / f"session_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / filename).write_bytes(file_bytes)

        entry = DiagramRevisionRead(
            version=version,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            notes=(notes or "").strip(),
            uploaded_at=datetime.now(UTC).isoformat(),
        ).model_dump()
        diagrams.append(entry)

        session.diagrams_metadata = diagrams
        if session.stage == "REQUIREMENTS":
            session.stage = "DESIGN"
        flag_modified(session, "diagrams_metadata")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def get_diagram_file(
        db: AsyncSession, session_id: int, version: int
    ) -> tuple[Path, str, str]:
        session = await SystemDesignService.get_session(db, session_id)
        entry = next(
            (
                d
                for d in (session.diagrams_metadata or [])
                if int(d.get("version", -1)) == version
            ),
            None,
        )
        if not entry:
            raise ValueError(
                f"Diagram revision v{version} not found for session {session_id}."
            )

        session_dir = (SYSTEM_DESIGN_DATA_DIR / f"session_{session_id}").resolve()
        file_path = (session_dir / str(entry["filename"])).resolve()
        if not file_path.is_relative_to(session_dir) or not file_path.is_file():
            raise ValueError(
                f"Diagram file for revision v{version} is missing on disk."
            )
        return (file_path, str(entry["mime_type"]), str(entry["filename"]))

    @staticmethod
    async def analyze_diagram_architecture(
        db: AsyncSession,
        session_id: int,
        diagram_version: int | None = None,
        use_web_search: bool = False,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService.get_session(db, session_id)
        challenge = session.challenge
        diagrams = list(session.diagrams_metadata or [])
        if not diagrams:
            raise ValueError("No diagram uploaded for this session yet.")

        if diagram_version is not None:
            target_entry = next(
                (d for d in diagrams if int(d.get("version", -1)) == diagram_version),
                None,
            )
            if not target_entry:
                raise ValueError(
                    f"Diagram revision v{diagram_version} not found for session {session_id}."
                )
        else:
            target_entry = diagrams[-1]

        target_version = int(target_entry["version"])
        file_path, mime_type, _ = await SystemDesignService.get_diagram_file(
            db, session_id, target_version
        )
        encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        data_uri = f"data:{mime_type};base64,{encoded}"

        base_prompt = await _format_prompt_from_db(
            db,
            "system_design_reviewer",
            DEFAULT_PROMPTS["system_design_reviewer"],
            challenge_title=challenge.title,
            requirements_ledger_json=json.dumps(
                session.requirements_ledger or {}, indent=2
            ),
            hidden_brief_json=json.dumps(challenge.interviewer_brief or {}, indent=2),
            candidate_notes=str(target_entry.get("notes") or "None provided."),
        )
        web_section = ""
        if use_web_search:
            snippets = await _fetch_web_grounding_snippets(
                db,
                f"{challenge.title} distributed systems architecture patterns trade-offs {str(target_entry.get('notes') or '')[:120]}",
            )
            if snippets:
                web_section = (
                    "\n\nWEB SEARCH REFERENCE SNIPPETS (Optional benchmark context):\n"
                    + snippets
                )

        sys_prompt = f"{base_prompt.strip()}{web_section}\n\n{ARCHITECTURE_REVIEW_JSON_INSTRUCTIONS}"

        human_msg = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        f"Inspect the attached architecture diagram (revision v{target_version}) "
                        "and return ONLY the JSON review object."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": data_uri},
                },
            ]
        )

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(db, task_type="SYSTEM_DESIGN_REVIEWER")
        llm_res = await _invoke_llm_adaptive(
            chat_model, [SystemMessage(content=sys_prompt), human_msg], tracer, db
        )

        raw_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        parsed = JsonOutputParser().parse(raw_text)
        if not isinstance(parsed, dict):
            parsed = {}

        review = ArchitectureReviewSchema(
            diagram_version=target_version,
            interpreted_components=_normalize_string_list(
                parsed.get("interpreted_components")
            ),
            interpreted_data_flows=_normalize_string_list(
                parsed.get("interpreted_data_flows")
            ),
            visual_clarifications_needed=_normalize_string_list(
                parsed.get("visual_clarifications_needed")
            ),
            strengths=_normalize_string_list(parsed.get("strengths")),
            missing_components=_normalize_string_list(parsed.get("missing_components")),
            bottlenecks_and_spofs=_normalize_string_list(
                parsed.get("bottlenecks_and_spofs")
            ),
            unnecessary_complexity=_normalize_string_list(
                parsed.get("unnecessary_complexity")
            ),
            requirement_gaps=_normalize_string_list(parsed.get("requirement_gaps")),
            overall_impression=str(
                parsed.get("overall_impression") or "Architecture review completed."
            ).strip(),
            suggested_defence_topics=_normalize_string_list(
                parsed.get("suggested_defence_topics")
            ),
        )

        reviews = [
            r
            for r in (session.architecture_reviews or [])
            if int(r.get("diagram_version", -1)) != target_version
        ]
        reviews.append(review.model_dump())
        reviews.sort(key=lambda r: int(r.get("diagram_version", 0)))

        session.architecture_reviews = reviews
        session.stage = "REVIEW"
        flag_modified(session, "architecture_reviews")

        if not session.defence_transcript:
            brief_questions = _normalize_string_list(
                (challenge.interviewer_brief or {}).get("defence_questions")
            )
            opening_question = (
                review.suggested_defence_topics[0]
                if review.suggested_defence_topics
                else (
                    brief_questions[0]
                    if brief_questions
                    else "Walk me through the primary failure modes and scaling bottlenecks in your submitted design."
                )
            )
            session.defence_transcript = [
                {
                    "turn_index": 1,
                    "role": "interviewer",
                    "content": opening_question,
                    "stage": "DEFENCE",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            ]
            flag_modified(session, "defence_transcript")

        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def run_queued_architecture_review(
        db: AsyncSession,
        session_id: int,
        diagram_version: int | None = None,
        use_web_search: bool = False,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService.get_session(db, session_id)
        diagrams = list(session.diagrams_metadata or [])
        if not diagrams:
            raise ValueError("No diagram uploaded for this session yet.")

        if diagram_version is not None:
            matching = next(
                (d for d in diagrams if int(d.get("version", -1)) == diagram_version),
                None,
            )
            if not matching:
                raise ValueError(
                    f"Diagram revision v{diagram_version} not found for session {session_id}."
                )
            target_version = int(matching["version"])
        else:
            target_version = int(diagrams[-1]["version"])

        task = IntakeEvaluationTaskModel(
            task_type="SYSTEM_DESIGN_REVIEW",
            title_hint=f"System Design Review: {session.challenge.title} (v{target_version})",
            status="QUEUED",
            stage="ANALYZING",
            result_json={
                "session_id": session_id,
                "diagram_version": target_version,
                "use_web_search": bool(use_web_search),
            },
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        from app.services.evaluation_worker import process_evaluation_task

        await process_evaluation_task(task.id, db=db)
        await db.refresh(task)
        if task.status == "FAILED":
            raise RuntimeError(task.error_message or "Architecture review task failed.")

        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def send_defence_message(
        db: AsyncSession,
        session_id: int,
        message_text: str,
        request_hint: bool = False,
        use_web_search: bool = False,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService.get_session(db, session_id)
        challenge = session.challenge
        assisted = _is_hint_request(message_text, request_hint)

        defence_transcript = list(session.defence_transcript or [])
        candidate_turn = {
            "turn_index": len(defence_transcript) + 1,
            "role": "candidate",
            "content": message_text.strip(),
            "stage": "DEFENCE",
            "assisted": assisted,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        defence_transcript.append(candidate_turn)

        mode_instruction = MODE_INSTRUCTIONS.get(
            session.mode, MODE_INSTRUCTIONS["ADAPTIVE"]
        )
        if assisted:
            mode_instruction += (
                "\nCOACHING HINT REQUESTED ON THIS TURN: The candidate asked for a hint "
                "or coaching guidance. Provide a brief, helpful hint pointing out the key "
                "failure mode or trade-off angle to consider without giving away the answer."
            )

        latest_review = (
            (session.architecture_reviews or [])[-1]
            if session.architecture_reviews
            else {}
        )
        sys_prompt = DEFENCE_SYSTEM_PROMPT.format(
            challenge_title=challenge.title,
            mode_instruction=mode_instruction,
            requirements_ledger_json=json.dumps(
                session.requirements_ledger or {}, indent=2
            ),
            latest_review_json=json.dumps(latest_review, indent=2),
            hidden_brief_json=json.dumps(challenge.interviewer_brief or {}, indent=2),
        )

        if use_web_search:
            snippets = await _fetch_web_grounding_snippets(
                db,
                f"{challenge.title} {message_text[:140]} system design trade-offs failure modes",
            )
            if snippets:
                sys_prompt += (
                    "\n\nWEB SEARCH REFERENCE SNIPPETS (Optional factual grounding):\n"
                    + snippets
                )

        messages = _build_chat_messages(sys_prompt, defence_transcript)
        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(
            db, task_type="SYSTEM_DESIGN_INTERVIEWER"
        )
        llm_res = await _invoke_llm_adaptive(chat_model, messages, tracer, db)
        reply_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        if not reply_text:
            reply_text = "Can you explain the trade-offs of that choice under peak load or partial failure?"

        interviewer_turn = {
            "turn_index": len(defence_transcript) + 1,
            "role": "interviewer",
            "content": reply_text,
            "stage": "DEFENCE",
            "assisted": assisted,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        defence_transcript.append(interviewer_turn)

        session.defence_transcript = defence_transcript
        if session.stage in ("DESIGN", "REVIEW", "REQUIREMENTS"):
            session.stage = "DEFENCE"
        flag_modified(session, "defence_transcript")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def evaluate_session(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        """Synthesize the Stage F evidence-backed 12-dimension final scorecard."""
        session = await SystemDesignService.get_session(db, session_id)
        challenge = session.challenge

        req_candidate_turns = [
            t
            for t in (session.requirements_transcript or [])
            if t.get("role") == "candidate"
        ]
        def_candidate_turns = [
            t
            for t in (session.defence_transcript or [])
            if t.get("role") == "candidate"
        ]
        assisted_turns_count = sum(
            1 for t in (req_candidate_turns + def_candidate_turns) if t.get("assisted")
        )
        independent_turns_count = (
            len(req_candidate_turns) + len(def_candidate_turns) - assisted_turns_count
        )

        sys_prompt = FINAL_EVALUATION_PROMPT.format(
            challenge_title=challenge.title,
            hidden_brief_json=json.dumps(challenge.interviewer_brief or {}, indent=2),
            dimensions_list="\n".join(f"- {dim}" for dim in DEFAULT_RUBRIC_DIMENSIONS),
        )
        sys_prompt += (
            f"\nCOACHING / HINT TELEMETRY: Candidate made {independent_turns_count} "
            f"independent turn(s) and {assisted_turns_count} assisted/hint-requested turn(s). "
            "Factor hint reliance fairly into discovery and trade-off independence scores."
        )

        context_payload = {
            "mode": session.mode,
            "challenge_title": challenge.title,
            "initial_prompt": challenge.initial_prompt,
            "assisted_turns_count": assisted_turns_count,
            "independent_turns_count": independent_turns_count,
            "requirements_transcript": session.requirements_transcript or [],
            "requirements_ledger": session.requirements_ledger or {},
            "diagram_revisions": session.diagrams_metadata or [],
            "architecture_reviews": session.architecture_reviews or [],
            "defence_transcript": session.defence_transcript or [],
        }

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(db, task_type="SYSTEM_DESIGN_REVIEWER")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(
                    content=(
                        "Evaluate this complete System Design Lab session and return ONLY JSON:\n"
                        + json.dumps(context_payload, indent=2)
                    )
                ),
            ],
            tracer,
            db,
        )

        raw_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        parsed = JsonOutputParser().parse(raw_text)
        if not isinstance(parsed, dict):
            parsed = {}

        eval_dict = _normalize_final_evaluation(parsed, session)
        now = datetime.now(UTC)
        session.final_evaluation = eval_dict
        session.overall_score = float(eval_dict["overall_score"])
        session.readiness_rating = str(eval_dict["readiness_rating"])
        session.stage = "COMPLETED"
        session.status = "COMPLETED"
        session.completed_at = now
        session.updated_at = now
        flag_modified(session, "final_evaluation")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def run_queued_final_evaluation(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        """Create and run an IntakeEvaluationTaskModel for Stage F final evaluation."""
        session = await SystemDesignService.get_session(db, session_id)
        task = IntakeEvaluationTaskModel(
            task_type="SYSTEM_DESIGN_EVALUATION",
            title_hint=f"System Design Evaluation: {session.challenge.title}",
            status="QUEUED",
            stage="ANALYZING",
            raw_text=f"session_id={session_id}",
            result_json={
                "session_id": session_id,
                "challenge_slug": session.challenge.slug,
            },
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        from app.services.evaluation_worker import process_evaluation_task

        await process_evaluation_task(task.id, db=db)
        await db.refresh(task)
        if task.status == "FAILED":
            raise RuntimeError(
                task.error_message or "System design final evaluation task failed."
            )

        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def build_frontier_evaluation_packet(
        db: AsyncSession, session_id: int
    ) -> FrontierEvaluationPacketRead:
        """Assemble a complete Markdown grading dossier for an external frontier LLM."""
        session = await SystemDesignService.get_session(db, session_id)
        challenge = session.challenge

        req_turns = list(session.requirements_transcript or [])
        def_turns = list(session.defence_transcript or [])
        all_candidate_turns = [
            t for t in (req_turns + def_turns) if t.get("role") == "candidate"
        ]
        assisted_count = sum(1 for t in all_candidate_turns if t.get("assisted"))
        independent_count = len(all_candidate_turns) - assisted_count

        def _fmt_turns(turns: list[dict[str, Any]]) -> str:
            if not turns:
                return "_No turns recorded._"
            lines = []
            for t in turns:
                role = str(t.get("role") or "unknown")
                idx = t.get("turn_index", "?")
                badge = " [ASSISTED / HINT REQUESTED]" if t.get("assisted") else ""
                lines.append(
                    f"- **Turn {idx} ({role}{badge})**: {t.get('content', '')}"
                )
            return "\n".join(lines)

        diagrams = list(session.diagrams_metadata or [])
        latest_version = int(diagrams[-1]["version"]) if diagrams else None
        dimensions_md = "\n".join(f"- `{dim}`" for dim in DEFAULT_RUBRIC_DIMENSIONS)

        json_template = json.dumps(
            {
                "overall_score": 0,
                "readiness_rating": "NEEDS_PRACTICE | DEVELOPING | INTERVIEW_READY | STRONG_HIRE",
                "executive_summary": "<2-4 sentence overall Staff-level assessment>",
                "rubric_scores": [
                    {
                        "dimension": dim,
                        "score": 3,
                        "evidence": "<concrete observation from diagram, ledger, or transcript>",
                        "critique": "<specific strength or gap and why it earned this score>",
                    }
                    for dim in DEFAULT_RUBRIC_DIMENSIONS
                ],
                "key_strengths": ["<evidence-backed strength>"],
                "critical_gaps": ["<evidence-backed gap>"],
                "recommended_next_steps": ["<concrete practice or revision action>"],
            },
            indent=2,
        )

        packet_sections = [
            f"# System Design Interview Evaluation Dossier: {challenge.title}",
            "",
            "> **Instructions for Frontier Evaluator (Claude / ChatGPT / Gemini)**:",
            "> 1. If the candidate uploaded their architecture diagram image alongside this prompt, inspect the image visually FIRST (check component boxes, arrows, stores, queues, replication, failure boundaries) before relying on local review summaries.",
            "> 2. Score strictly on demonstrated evidence in the attached diagram, locked requirements ledger, requirements discovery transcript, and defence answers.",
            f"> 3. Note coaching telemetry: **{independent_count} independent** candidate turn(s) vs **{assisted_count} assisted/hint-requested** turn(s).",
            "> 4. Respond with a rigorous critique AND include ONE valid JSON code block matching the schema at the bottom so the candidate can import your scorecard directly back into Job Tracker.",
            "",
            "## 1. Challenge Brief & Hidden Ground Truth",
            f"- **Title**: {challenge.title}",
            f"- **Category / Difficulty**: {challenge.category} / {challenge.difficulty}",
            f"- **Initial Prompt**: {challenge.initial_prompt}",
            "",
            "```json",
            json.dumps(challenge.interviewer_brief or {}, indent=2),
            "```",
            "",
            "## 2. Requirements Discovery Transcript (Stage B)",
            _fmt_turns(req_turns),
            "",
            "## 3. Candidate Requirements Ledger (Stage B Locked State)",
            "```json",
            json.dumps(session.requirements_ledger or {}, indent=2),
            "```",
            "",
            "## 4. Submitted Diagram Revisions & Local AI Review Notes (Stages C & D)",
            "```json",
            json.dumps(
                {
                    "diagrams_metadata": diagrams,
                    "architecture_reviews": session.architecture_reviews or [],
                },
                indent=2,
            ),
            "```",
            "",
            "## 5. Interactive Architecture Defence Transcript (Stage E)",
            _fmt_turns(def_turns),
            "",
            "## 6. Required 12-Dimension Evidence-Backed JSON Output",
            "Evaluate ALL 12 dimensions below (score `1`-`5`, concrete `evidence` quote/observation >= 5 chars):",
            dimensions_md,
            "",
            "Return valid JSON matching this schema:",
            "```json",
            json_template,
            "```",
        ]

        return FrontierEvaluationPacketRead(
            session_id=session.id,
            challenge_title=challenge.title,
            filename=f"{challenge.slug}-session-{session.id}-frontier-packet.md",
            diagram_version=latest_version,
            markdown_packet="\n".join(packet_sections),
        )

    @staticmethod
    async def import_frontier_evaluation(
        db: AsyncSession, session_id: int, raw_response: str
    ) -> SystemDesignSessionModel:
        """Parse and save an external frontier LLM scorecard back onto the session."""
        session = await SystemDesignService.get_session(db, session_id)
        parsed = _extract_json_object(raw_response)
        if not any(
            k in parsed for k in ("rubric_scores", "overall_score", "executive_summary")
        ):
            raise ValueError(
                "Imported JSON must contain at least one of: rubric_scores, overall_score, or executive_summary."
            )

        eval_dict = _normalize_final_evaluation(parsed, session)
        now = datetime.now(UTC)
        session.final_evaluation = eval_dict
        session.overall_score = float(eval_dict["overall_score"])
        session.readiness_rating = str(eval_dict["readiness_rating"])
        session.stage = "COMPLETED"
        session.status = "COMPLETED"
        session.completed_at = now
        session.updated_at = now
        flag_modified(session, "final_evaluation")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)
