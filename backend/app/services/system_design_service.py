import base64
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import tempfile
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.llm_factory import (
    get_model_telemetry_metadata,
    get_task_chat_model,
    strip_reasoning_tags,
)
from app.core.prompts import DEFAULT_PROMPTS
from app.models.applications import ApplicationModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.system_design import (
    SystemDesignChallengeModel,
    SystemDesignSessionModel,
)
from app.schemas.system_design import (
    ArchitectureReviewSchema,
    CanvasDiagramSubmitRequest,
    ChallengeFrontierPromptResponse,
    CoachCanvasAction,
    DiagramCoachChatRequest,
    DiagramCoachChatResponse,
    DiagramHintRequest,
    DiagramHintResponse,
    DiagramRevisionRead,
    FinalEvaluationSchema,
    FrontierEvaluationPacketRead,
    ImportFrontierChallengeRequest,
    RequirementsLedgerSchema,
    RequirementsLedgerUpdateRequest,
    RevealedComponentHint,
    RubricDimensionScore,
    SystemDesignChallengeCreate,
    SystemDesignChallengeGenerateRequest,
    SystemDesignChallengeUpdate,
    SystemDesignSessionRead,
)
from app.services.diagram_catalog import (
    CLOUD_PROVIDERS,
    build_coach_canvas_actions,
    compute_diagram_hint_penalty,
    evaluate_canvas_topology,
    node_matches_expected,
    normalize_cloud_provider,
    normalize_flow_payload,
    resolve_challenge_blueprint,
    summarize_diagram_flow,
)
from app.services.interview_simulator_service import (
    _format_prompt_from_db,
    _invoke_llm_adaptive,
)
from app.services.postgres_tracer import PostgresTracer
from app.services.system_design_seed import seed_system_design_challenges

logger = logging.getLogger(__name__)

# Configurable disk storage root for binary diagrams (SYSTEM_DESIGN_DATA_DIR env/setting,
# defaulting to <backend_root>/data/system_design locally or /app/data/system_design in Docker).
_DEFAULT_STORAGE_SENTINEL = settings.get_system_design_data_dir()
SYSTEM_DESIGN_DATA_DIR = _DEFAULT_STORAGE_SENTINEL
MAX_DIAGRAM_BYTES = 10 * 1024 * 1024  # 10 MB


def _get_storage_root() -> Path:
    """Resolve the active diagram storage root with NO silent fallback."""
    if SYSTEM_DESIGN_DATA_DIR != _DEFAULT_STORAGE_SENTINEL:
        return Path(SYSTEM_DESIGN_DATA_DIR).expanduser().resolve()
    configured = (settings.SYSTEM_DESIGN_DATA_DIR or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    env_configured = os.environ.get("SYSTEM_DESIGN_DATA_DIR", "").strip()
    if env_configured:
        return Path(env_configured).expanduser().resolve()
    return settings.get_system_design_data_dir().expanduser().resolve()


def _ensure_writable_session_dir(session_id: int) -> Path:
    """Create and verify writability of the session diagram directory without silent fallback."""
    root = _get_storage_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        session_dir = (root / f"session_{session_id}").resolve()
        if not session_dir.is_relative_to(root):
            raise PermissionError(
                f"Resolved session directory '{session_dir}' escapes configured storage root '{root}'."
            )
        session_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=session_dir, prefix=".write_probe_", delete=True
        ):
            pass
        return session_dir
    except (PermissionError, OSError) as exc:
        uid = os.getuid() if hasattr(os, "getuid") else "unknown"
        raise PermissionError(
            f"System design diagram storage directory '{root}' is not writable by current user "
            f"(uid={uid}): {exc}. Configure SYSTEM_DESIGN_DATA_DIR to a writable directory or "
            "fix ownership for the executing user (never use chmod 777)."
        ) from exc


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

STRICT SCORING & OUTPUT RULES:
1. Score the candidate ONLY on demonstrated evidence in their requirements conversation, locked requirements ledger, submitted diagram reviews, and defence responses below.
2. SCALE: Every dimension `score` MUST be an integer in 1..5 ONLY (1=poor/missing, 2=weak, 3=acceptable, 4=strong, 5=exceptional Staff level). NEVER use a 1-10 scale.
3. OVERALL SCORE: `overall_score` MUST be on a 0..100 scale and MUST match `round((sum(all 12 scores) / 60) * 100, 1)`.
   - `STRONG_HIRE`: 88.0 - 100.0
   - `INTERVIEW_READY`: 70.0 - 87.9
   - `DEVELOPING`: 50.0 - 69.9
   - `NEEDS_PRACTICE`: 0.0 - 49.9
4. COMPLETENESS: You MUST include ALL 12 exact dimension names listed below (no omissions, no duplicates, no renamed dimensions):
{dimensions_list}
5. EVIDENCE & ADVICE: Every single rubric item MUST have concise, concrete `evidence` (>= 5 chars referencing session artifacts) AND actionable `critique` advice (>= 5 chars explaining improvement or strength).
6. TOKEN EFFICIENCY: Output the complete JSON object immediately with concise strings (1-2 sentences per field). Do NOT output `<think>` reasoning or markdown fences.

Respond ONLY with a single complete JSON object matching this exact schema:
{{
  "overall_score": 0,
  "readiness_rating": "NEEDS_PRACTICE | DEVELOPING | INTERVIEW_READY | STRONG_HIRE",
  "executive_summary": "<2-3 sentence overall assessment>",
  "rubric_scores": [
    {{
      "dimension": "<exact dimension name from the 12 listed above>",
      "score": 3,
      "evidence": "<concrete observation from ledger, diagram review, or transcript>",
      "critique": "<specific strength or gap and actionable improvement advice>"
    }}
  ],
  "key_strengths": ["<evidence-backed strength>"],
  "critical_gaps": ["<evidence-backed gap>"],
  "recommended_next_steps": ["<concrete practice or revision action>"]
}}
"""

MODE_INSTRUCTIONS: dict[str, str] = {
    "ADAPTIVE": (
        "ADAPTIVE STAKEHOLDER MODE (Realistic Stakeholder + On-Demand Coaching): "
        "During requirements discovery, act as the Product Owner / Business Stakeholder: "
        "answer the candidate's clarifying questions directly using concrete figures from the brief "
        "without dumping unasked sections or bouncing questions back. "
        "HOWEVER, when the candidate explicitly asks for help, a hint, or guidance (or when "
        "a coaching hint is requested for a turn), respond with a brief, constructive nudge "
        "pointing out what requirement area, constraint, or trade-off to ask about next without "
        "handing over the full answer."
    ),
    "INTERVIEW": (
        "INTERVIEW MODE (Strict Stakeholder): During requirements discovery, act strictly as the "
        "Product Owner / Business Stakeholder being interviewed. Answer only what the candidate "
        "explicitly asks using concrete figures from the brief; do not volunteer unasked sections "
        "or coaching hints, and never bounce a clarifying question back to the candidate. "
        "If something is not in the brief, state that it is unspecified."
    ),
    "PRACTICE": (
        "PRACTICE / COACHING MODE (Collaborative Stakeholder): Answer the candidate's clarifying "
        "questions directly with concrete figures from the brief, and if they ask for hints or "
        "overlook essential constraint areas (such as read/write ratio, latency SLA, retention/TTL, "
        "privacy, or analytics freshness), suggest 1-2 unexplored requirement areas to ask about next."
    ),
}

CUSTOM_CHALLENGE_GENERATE_PROMPT = """You are a Staff System Design Interview Architect designing a tailored system design interview challenge with 3 genuinely distinct architectural requirement variants.

CRITICAL RULES:
1. UNIQUENESS: Never duplicate or lightly re-skin any challenge in the provided EXISTING CHALLENGES list. Pick a concrete, role-relevant system design problem with a genuinely different problem domain and architectural bottleneck.
2. CONTEXT GROUNDING & PRIVACY: If job application notes, company research, job description, match gap analysis, or interview email clues are provided, use them to target the company's real technical domain, scale pressures, and probable interview focus. NEVER copy private compensation figures, recruiter contacts, or verbatim personal notes into candidate-facing `title`, `prompt_summary`, or `initial_prompt`.
3. NO ANSWER LEAKS: Keep `prompt_summary` and `initial_prompt` intentionally broad so the candidate still discovers scale, SLAs, and trade-offs during Stage 1 requirements interview.

Respond ONLY with a valid JSON object matching this exact schema (no markdown fences):
{{
  "title": "<concise realistic challenge title, e.g. Design a Real-Time Fraud Scoring Pipeline>",
  "category": "<DISTRIBUTED_SYSTEMS | DATA_INFRASTRUCTURE | REALTIME_COMMUNICATION | STREAMING_MEDIA | STORAGE_SYSTEMS | AI_PLATFORM>",
  "difficulty": "{difficulty}",
  "prompt_summary": "<1-2 sentence scenario summary shown on the challenge card without spoiling variant trade-offs>",
  "initial_prompt": "<2-4 sentence intentionally broad opening interview prompt matching how a real stakeholder opens the session without leaking scale numbers or answers>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"],
  "interviewer_brief": {{
    "variants": [
      {{
        "variant_id": "<short-kebab-slug-1>",
        "title": "<Variant 1 Scenario Name, e.g. Cost-Constrained MVP>",
        "focus_summary": "<1-sentence trade-off focus for post-session summary>",
        "business_context": {{
          "product_goal": "<core business/product objective>",
          "target_users": "<who uses the system>"
        }},
        "scale_estimates": {{
          "dau": "<concrete DAU/MAU target>",
          "daily_volume": "<concrete daily writes/reads>",
          "qps": "<average and peak QPS>"
        }},
        "functional_requirements": ["<core functional requirement 1>", "<core functional requirement 2>"],
        "non_functional_requirements": ["<latency p99 target>", "<availability SLA>", "<consistency/privacy requirement>"],
        "constraints": ["<business or operational constraint 1>"],
        "priorities": ["P0: <top priority>", "P1: <secondary priority>"],
        "out_of_scope": ["<explicitly excluded feature 1>"],
        "hidden_context": {{
          "scale_targets": "<concrete hidden DAU/QPS/storage/latency numbers revealed only when asked>",
          "key_constraints": ["<constraint 1>", "<constraint 2>"]
        }},
        "expected_components": ["Load Balancer", "API Gateway", "Stateless App Service", "Primary Relational DB", "<additional atomic component e.g. Distributed Cache (Redis) or Scheduler / TTL Sweeper>"],
        "diagram_palette_extensions": [
          {{"type_id": "<optional-custom-slug>", "label": "<Optional Specialized Block>", "category": "compute_services", "icon": "box", "default_role": "<1-sentence role>"}}
        ],
        "over_engineering_traps": ["<unjustified complexity trap 1>"],
        "defence_questions": [
          "<challenging architecture defence question 1>",
          "<challenging architecture defence question 2>"
        ]
      }},
      {{
        "variant_id": "<short-kebab-slug-2>",
        "title": "<Variant 2 Scenario Name with fundamentally different scale/SLA/compliance trade-offs>",
        "focus_summary": "<1-sentence trade-off focus>",
        "business_context": {{"product_goal": "...", "target_users": "..."}},
        "scale_estimates": {{"dau": "...", "daily_volume": "...", "qps": "..."}},
        "functional_requirements": ["..."],
        "non_functional_requirements": ["..."],
        "constraints": ["..."],
        "priorities": ["P0: ...", "P1: ..."],
        "out_of_scope": ["..."],
        "hidden_context": {{"scale_targets": "...", "key_constraints": ["..."]}},
        "expected_components": ["..."],
        "over_engineering_traps": ["..."],
        "defence_questions": ["...", "..."]
      }},
      {{
        "variant_id": "<short-kebab-slug-3>",
        "title": "<Variant 3 Scenario Name stressing a different dimension like bursts, strict consistency, or geo-locality>",
        "focus_summary": "<1-sentence trade-off focus>",
        "business_context": {{"product_goal": "...", "target_users": "..."}},
        "scale_estimates": {{"dau": "...", "daily_volume": "...", "qps": "..."}},
        "functional_requirements": ["..."],
        "non_functional_requirements": ["..."],
        "constraints": ["..."],
        "priorities": ["P0: ...", "P1: ..."],
        "out_of_scope": ["..."],
        "hidden_context": {{"scale_targets": "...", "key_constraints": ["..."]}},
        "expected_components": ["..."],
        "over_engineering_traps": ["..."],
        "defence_questions": ["...", "..."]
      }}
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


class DuplicateChallengeError(ValueError):
    """Raised when a generated or imported challenge closely overlaps an existing active challenge."""

    def __init__(
        self,
        message: str,
        *,
        existing_title: str = "",
        existing_slug: str = "",
    ) -> None:
        super().__init__(message)
        self.existing_title = existing_title
        self.existing_slug = existing_slug


_TITLE_WRAPPER_STOPWORDS = {
    "design",
    "build",
    "create",
    "architect",
    "implement",
    "a",
    "an",
    "the",
    "system",
    "service",
    "platform",
    "architecture",
    "engine",
    "pipeline",
    "for",
    "of",
    "and",
    "with",
    "to",
    "in",
    "on",
}


def _tokenize_title_domain(title: str) -> tuple[str, set[str]]:
    raw_words = re.findall(r"[a-z0-9]+", str(title or "").lower())
    domain_words = [w for w in raw_words if w not in _TITLE_WRAPPER_STOPWORDS]
    effective = domain_words or raw_words
    return (" ".join(effective), set(effective))


def _find_similar_challenge(
    title: str,
    existing_challenges: list[dict[str, str]],
) -> dict[str, str] | None:
    """Detect whether a candidate challenge title duplicates an existing active challenge."""
    cand_slug = _slugify(title)
    cand_clean, cand_tokens = _tokenize_title_domain(title)
    if not cand_clean:
        return None

    for item in existing_challenges:
        ex_title = str(item.get("title") or "").strip()
        ex_slug = str(item.get("slug") or _slugify(ex_title)).strip()
        if not ex_title:
            continue
        if cand_slug == ex_slug:
            return item
        ex_clean, ex_tokens = _tokenize_title_domain(ex_title)
        if not ex_clean:
            continue
        if cand_clean == ex_clean:
            return item
        union = cand_tokens | ex_tokens
        inter = cand_tokens & ex_tokens
        jaccard = (len(inter) / len(union)) if union else 0.0
        ratio = SequenceMatcher(None, cand_clean, ex_clean).ratio()
        if jaccard >= 0.72 and len(inter) >= 2:
            return item
        if ratio >= 0.84:
            return item
        # Stemmed containment check (e.g. shortener vs shortening, rate limiter vs rate limiting)
        if len(cand_tokens) >= 2 and len(ex_tokens) >= 2:
            if (cand_tokens <= ex_tokens or ex_tokens <= cand_tokens) and ratio >= 0.65:
                return item
    return None


def _validate_generated_challenge_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    """Validate completeness of an AI-generated or Frontier-imported challenge payload."""
    if not isinstance(parsed, dict):
        raise ValueError("Challenge payload must be a JSON object.")

    title = str(parsed.get("title") or "").strip()
    prompt_summary = str(parsed.get("prompt_summary") or "").strip()
    initial_prompt = str(parsed.get("initial_prompt") or "").strip()

    for label, text, min_len in (
        ("title", title, 5),
        ("prompt_summary", prompt_summary, 12),
        ("initial_prompt", initial_prompt, 15),
    ):
        if len(text) < min_len or text.lower() in _PLACEHOLDER_STRINGS:
            raise ValueError(
                f"Challenge field '{label}' must be meaningful (>= {min_len} chars, non-placeholder)."
            )

    raw_brief = parsed.get("interviewer_brief")
    if not isinstance(raw_brief, dict) or not raw_brief:
        raise ValueError(
            "Challenge payload must include a non-empty 'interviewer_brief' object."
        )

    variants = _extract_brief_variants(raw_brief)
    if "variants" in raw_brief and raw_brief.get("variants") is not None:
        if len(variants) < 2:
            raise ValueError(
                "Challenge interviewer_brief.variants must define at least 2 distinct scenario variants."
            )
        for idx, var in enumerate(variants, start=1):
            has_scope = bool(
                _normalize_string_list(var.get("functional_requirements"))
                or _normalize_string_list(var.get("expected_components"))
            )
            has_questions = bool(_normalize_string_list(var.get("defence_questions")))
            if not has_scope or not has_questions:
                raise ValueError(
                    f"Variant {idx} ('{var.get('title')}') must include expected_components/functional_requirements and defence_questions."
                )
    else:
        expected_components = _normalize_string_list(
            raw_brief.get("expected_components")
        )
        defence_questions = _normalize_string_list(raw_brief.get("defence_questions"))
        if not expected_components or not defence_questions:
            raise ValueError(
                "Challenge interviewer_brief must include either 2+ structured variants or non-empty expected_components and defence_questions."
            )

    return parsed


_VARIANT_BRIEF_COPY_KEYS = (
    "business_context",
    "scale_estimates",
    "functional_requirements",
    "non_functional_requirements",
    "constraints",
    "priorities",
    "out_of_scope",
    "hidden_context",
    "expected_components",
    "expected_paths",
    "diagram_palette_extensions",
    "common_bottlenecks_and_spofs",
    "over_engineering_traps",
    "defence_questions",
)


def _extract_brief_variants(
    interviewer_brief: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return normalized scenario variant dicts from challenge.interviewer_brief, if defined."""
    if not isinstance(interviewer_brief, dict):
        return []
    raw_variants = interviewer_brief.get("variants")
    if not isinstance(raw_variants, list):
        return []
    variants: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_variants):
        if not isinstance(item, dict):
            continue
        vid = _slugify(
            str(item.get("variant_id") or item.get("title") or f"variant-{idx + 1}")
        )
        v = dict(item)
        v["variant_id"] = vid
        v["title"] = str(item.get("title") or f"Scenario {idx + 1}").strip()
        v["focus_summary"] = str(item.get("focus_summary") or "").strip()
        variants.append(v)
    return variants


def _build_session_brief(
    challenge: SystemDesignChallengeModel, variant: dict[str, Any] | None
) -> dict[str, Any]:
    """Assemble the isolated single-scenario interviewer brief persisted onto a session."""
    base_brief = dict(challenge.interviewer_brief or {})
    base_brief.pop("variants", None)
    if variant is None:
        return base_brief
    scoped = dict(base_brief)
    scoped["variant_id"] = str(variant.get("variant_id") or "default")
    scoped["variant_title"] = str(variant.get("title") or "Standard Scenario")
    if variant.get("focus_summary"):
        scoped["focus_summary"] = str(variant["focus_summary"])
    for key in _VARIANT_BRIEF_COPY_KEYS:
        if key in variant:
            scoped[key] = variant[key]
    return scoped


def _normalize_generated_brief(raw_brief: Any) -> dict[str, Any]:
    """Normalize AI-generated interviewer_brief, flattening variant 1 to top-level defaults."""
    default_brief = {
        "hidden_context": {
            "scale_targets": "Establish DAU, QPS, latency SLA, and fault tolerance targets."
        },
        "expected_components": ["API Gateway", "Core Service", "Primary Storage"],
        "over_engineering_traps": [],
        "defence_questions": [
            "How does your design degrade gracefully when downstream storage slows down?"
        ],
    }
    if not isinstance(raw_brief, dict):
        return default_brief
    brief = dict(raw_brief)
    variants = _extract_brief_variants(brief)
    if variants:
        brief["variants"] = variants
        primary = variants[0]
        for key in _VARIANT_BRIEF_COPY_KEYS:
            if key in primary and key not in brief:
                brief[key] = primary[key]
    return brief


def _seed_variant_index(challenge_slug: str, seed: str, variant_count: int) -> int:
    digest = hashlib.sha256(f"{challenge_slug}:{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % variant_count


def _select_session_variant(
    challenge: SystemDesignChallengeModel,
    *,
    brief_seed: str | None = None,
    variant_id: str | None = None,
    last_variant_id: str | None = None,
) -> tuple[str, str, str, dict[str, Any]]:
    """Resolve (brief_seed, variant_id, selection_mode, session_brief) deterministically."""
    cleaned_seed = (brief_seed or "").strip().lower() or None
    cleaned_variant_id = (variant_id or "").strip() or None
    variants = _extract_brief_variants(challenge.interviewer_brief)

    if cleaned_variant_id is not None:
        resolved_seed = cleaned_seed or secrets.token_hex(4)
        if not variants:
            if cleaned_variant_id != "default":
                raise ValueError(
                    f"Variant '{cleaned_variant_id}' is not available for challenge '{challenge.title}'."
                )
            return (
                resolved_seed,
                "default",
                "explicit",
                _build_session_brief(challenge, None),
            )
        chosen = next(
            (v for v in variants if v["variant_id"] == cleaned_variant_id), None
        )
        if chosen is None:
            available = ", ".join(v["variant_id"] for v in variants)
            raise ValueError(
                f"Invalid variant_id '{cleaned_variant_id}' for '{challenge.title}'. Available: {available}."
            )
        return (
            resolved_seed,
            chosen["variant_id"],
            "explicit",
            _build_session_brief(challenge, chosen),
        )

    if not variants:
        resolved_seed = cleaned_seed or secrets.token_hex(4)
        return (
            resolved_seed,
            "default",
            "random",
            _build_session_brief(challenge, None),
        )

    if cleaned_seed is not None:
        idx = _seed_variant_index(challenge.slug, cleaned_seed, len(variants))
        chosen = variants[idx]
        return (
            cleaned_seed,
            chosen["variant_id"],
            "random",
            _build_session_brief(challenge, chosen),
        )

    # Fresh random roll: pick a candidate seed whose deterministic hash avoids
    # repeating the immediately preceding variant on this challenge when >1 exist.
    resolved_seed = secrets.token_hex(4)
    chosen = variants[_seed_variant_index(challenge.slug, resolved_seed, len(variants))]
    if len(variants) > 1 and last_variant_id:
        for _ in range(16):
            if chosen["variant_id"] != last_variant_id:
                break
            resolved_seed = secrets.token_hex(4)
            chosen = variants[
                _seed_variant_index(challenge.slug, resolved_seed, len(variants))
            ]

    return (
        resolved_seed,
        chosen["variant_id"],
        "random",
        _build_session_brief(challenge, chosen),
    )


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


def _parse_strict_json_object(raw_text: str) -> dict[str, Any]:
    """Strictly parse a complete JSON object, rejecting empty or truncated LLM outputs."""
    text = str(raw_text or "")
    open_think_count = len(re.findall(r"<think>", text, flags=re.IGNORECASE))
    close_think_count = len(re.findall(r"</think>", text, flags=re.IGNORECASE))
    if open_think_count > close_think_count:
        raise ValueError(
            "Truncated model response: reasoning block (<think>) was not closed."
        )

    cleaned = strip_reasoning_tags(text).strip()
    if not cleaned:
        raise ValueError("Empty response cannot be parsed as JSON.")

    # Direct strict JSON check first
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Closed markdown JSON fences (e.g. from Frontier copy/paste)
    complete_blocks = re.findall(
        r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE
    )
    for block in complete_blocks:
        try:
            candidate = json.loads(block.strip())
            if isinstance(candidate, dict):
                return candidate
        except json.JSONDecodeError:
            continue

    # Detect unclosed markdown fence (truncated output)
    if cleaned.count("```") % 2 == 1 and not complete_blocks:
        raise ValueError("Truncated markdown JSON code block (missing closing fence).")

    # Balanced outermost JSON object extraction (supports surrounding prose)
    first_brace = cleaned.find("{")
    if first_brace == -1:
        raise ValueError("Could not find a JSON object in model response.")

    depth = 0
    in_string = False
    escape = False
    end_idx = -1
    for idx in range(first_brace, len(cleaned)):
        ch = cleaned[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end_idx = idx
                break

    if end_idx == -1 or depth != 0:
        raise ValueError(
            "Truncated or incomplete JSON object in model response (unclosed braces)."
        )

    try:
        candidate = json.loads(cleaned[first_brace : end_idx + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON object in model response: {exc}") from exc

    if not isinstance(candidate, dict):
        raise ValueError("Top-level parsed JSON value must be an object.")
    return candidate


_extract_json_object = _parse_strict_json_object


REQUIREMENTS_EXTRACTION_PROMPT = """You are extracting structured requirements from a System Design interview requirements-discovery conversation between a Candidate and a Stakeholder.

STRICT GROUNDING RULES:
1. Extract ONLY items that were explicitly discussed, clarified, assumed, or left open in the conversation below or already recorded in the existing ledger.
2. Do NOT copy hidden metrics or unmentioned requirements from external knowledge.
3. DISTINGUISH CONFIRMED VS ASSUMED VS UNRESOLVED:
   - Put confirmed business answers and agreed requirements into `functional_requirements`, `non_functional_requirements`, `scale_estimates`, and `out_of_scope`.
   - Put candidate-proposed or stakeholder-offered baseline assumptions (not yet confirmed as hard business requirements) into `assumptions`.
   - Put open/unspecified questions or unresolved trade-offs awaiting confirmation into `unresolved_questions`.
4. Preserve still-valid items from the existing ledger unless contradicted, resolved, or refined by later turns.
5. Respond ONLY with a valid JSON object matching this exact schema (no markdown fences):
{{
  "functional_requirements": ["<confirmed functional item>"],
  "non_functional_requirements": ["<confirmed SLA/availability/consistency/privacy requirement>"],
  "scale_estimates": {{
    "<metric_name>": "<concrete estimate string>"
  }},
  "out_of_scope": ["<excluded feature>"],
  "assumptions": ["<explicitly labeled assumption>"],
  "unresolved_questions": ["<open or unspecified question>"],
  "notes": "<concise summary note>"
}}

Challenge: {challenge_title}

Existing Ledger:
{existing_ledger_json}

Requirements Transcript:
{transcript_text}
"""

LIVE_LEDGER_SYNC_INSTRUCTION = """
LIVE REQUIREMENTS LEDGER SYNC:
After writing your concise, natural stakeholder reply for the candidate, append a `<ledger_json>` XML block at the very end updating the structured requirements ledger with everything discovered, assumed, or left unresolved up through this turn (preserve valid entries already present in CURRENT REQUIREMENTS LEDGER and do not leak unasked hidden brief details).
Format EXACTLY:
<ledger_json>{"functional_requirements":[],"non_functional_requirements":[],"scale_estimates":{},"out_of_scope":[],"assumptions":[],"unresolved_questions":[],"notes":""}</ledger_json>"""


def _merge_unique_str_lists(existing: list[str], additions: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*existing, *additions]:
        cleaned = str(item or "").strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            merged.append(cleaned)
    return merged


def _build_merged_ledger_dict(
    existing_ledger: dict[str, Any],
    parsed: dict[str, Any],
    *,
    merge_with_existing: bool = True,
) -> dict[str, Any]:
    """Validate and merge extracted ledger fields while preserving user lock state."""
    ext_func = _normalize_string_list(parsed.get("functional_requirements"))
    ext_nfr = _normalize_string_list(parsed.get("non_functional_requirements"))
    ext_scale = _normalize_scale_dict(parsed.get("scale_estimates"))
    ext_oos = _normalize_string_list(parsed.get("out_of_scope"))
    ext_assump = _normalize_string_list(parsed.get("assumptions"))
    ext_unres = _normalize_string_list(parsed.get("unresolved_questions"))

    if merge_with_existing and isinstance(existing_ledger, dict):
        ext_func = _merge_unique_str_lists(
            _normalize_string_list(existing_ledger.get("functional_requirements")),
            ext_func,
        )
        ext_nfr = _merge_unique_str_lists(
            _normalize_string_list(existing_ledger.get("non_functional_requirements")),
            ext_nfr,
        )
        merged_scale = _normalize_scale_dict(existing_ledger.get("scale_estimates"))
        merged_scale.update(ext_scale)
        ext_scale = merged_scale
        ext_oos = _merge_unique_str_lists(
            _normalize_string_list(existing_ledger.get("out_of_scope")), ext_oos
        )
        ext_assump = _merge_unique_str_lists(
            _normalize_string_list(existing_ledger.get("assumptions")), ext_assump
        )
        ext_unres = _merge_unique_str_lists(
            _normalize_string_list(existing_ledger.get("unresolved_questions")),
            ext_unres,
        )

    ledger = RequirementsLedgerSchema(
        functional_requirements=ext_func,
        non_functional_requirements=ext_nfr,
        scale_estimates=ext_scale,
        out_of_scope=ext_oos,
        assumptions=ext_assump,
        unresolved_questions=ext_unres,
        notes=str(parsed.get("notes") or existing_ledger.get("notes") or "").strip(),
        is_locked=bool((existing_ledger or {}).get("is_locked", False)),
    )
    return ledger.model_dump()


_LEDGER_JSON_BLOCK_RE = re.compile(
    r"<ledger_json>\s*(.*?)\s*</ledger_json>",
    re.IGNORECASE | re.DOTALL,
)
_LEDGER_JSON_UNCLOSED_RE = re.compile(
    r"<ledger_json>[\s\S]*$",
    re.IGNORECASE,
)


def _split_reply_and_ledger_patch(
    raw_reply: str, existing_ledger: dict[str, Any]
) -> tuple[str, dict[str, Any] | None]:
    """Strip any `<ledger_json>` trailer from the stakeholder reply and return merged ledger dict if valid."""
    text = str(raw_reply or "").strip()
    match = _LEDGER_JSON_BLOCK_RE.search(text)
    parsed_ledger: dict[str, Any] | None = None
    if match:
        candidate_json = match.group(1).strip()
        try:
            parsed_obj = _parse_strict_json_object(candidate_json)
            parsed_ledger = _build_merged_ledger_dict(
                existing_ledger, parsed_obj, merge_with_existing=True
            )
        except ValueError as exc:
            logger.debug("Skipping malformed inline <ledger_json> trailer: %s", exc)
        text = _LEDGER_JSON_BLOCK_RE.sub("", text).strip()
    else:
        text = _LEDGER_JSON_UNCLOSED_RE.sub("", text).strip()
    return text, parsed_ledger


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


_PLACEHOLDER_STRINGS = {"n/a", "na", "none", "tbd", "todo", "null", "-", "..."}
_RATING_TIERS = {
    "NEEDS_PRACTICE": 0,
    "DEVELOPING": 1,
    "INTERVIEW_READY": 2,
    "STRONG_HIRE": 3,
}


def _derive_readiness_rating(overall_score: float) -> str:
    if overall_score >= 88.0:
        return "STRONG_HIRE"
    if overall_score >= 70.0:
        return "INTERVIEW_READY"
    if overall_score >= 50.0:
        return "DEVELOPING"
    return "NEEDS_PRACTICE"


def _is_session_coached(session: SystemDesignSessionModel | None) -> bool:
    """Return True when the learner used Reveal Requirements, Hints, Required Bank, or Coach."""
    if not session:
        return False
    guidance = session.diagram_guidance or {}
    if (
        guidance.get("is_coached")
        or guidance.get("requirements_revealed")
        or guidance.get("revealed_all_bank")
        or int(guidance.get("hints_used_count") or 0) > 0
        or bool(guidance.get("coach_messages"))
    ):
        return True
    for turn in (session.requirements_transcript or []) + (
        session.defence_transcript or []
    ):
        if isinstance(turn, dict) and turn.get("assisted"):
            return True
    return False


def _apply_guidance_penalty(
    eval_dict: dict[str, Any],
    diagram_guidance: dict[str, Any] | None,
    session: SystemDesignSessionModel | None = None,
) -> dict[str, Any]:
    """Attach unpenalized rubric score, Solo/Coached status, and Mastery XP."""
    updated = dict(eval_dict)
    raw_val = (
        updated.get("raw_score")
        if updated.get("raw_score") is not None
        else updated.get("overall_score", 0.0)
    )
    raw_score = round(max(0.0, min(100.0, float(raw_val))), 1)
    is_coached = (
        _is_session_coached(session)
        if session is not None
        else bool(
            (diagram_guidance or {}).get("is_coached")
            or (diagram_guidance or {}).get("requirements_revealed")
            or (diagram_guidance or {}).get("revealed_all_bank")
            or int((diagram_guidance or {}).get("hints_used_count") or 0) > 0
            or bool((diagram_guidance or {}).get("coach_messages"))
        )
    )
    updated["raw_score"] = raw_score
    updated["guidance_penalty"] = 0.0
    updated["overall_score"] = raw_score
    updated["readiness_rating"] = _derive_readiness_rating(raw_score)
    updated["assistance_mode"] = "COACHED" if is_coached else "SOLO"
    updated["xp_earned"] = 100 if is_coached else 150
    return updated


def _compute_deterministic_overall_score(scores: list[RubricDimensionScore]) -> float:
    """Deterministic 0..100 overall score: sum(12 integer scores 1..5) / 60 * 100."""
    max_points = len(DEFAULT_RUBRIC_DIMENSIONS) * 5
    return round((sum(item.score for item in scores) / max_points) * 100.0, 1)


def _validate_final_evaluation_payload(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Strictly validate Stage F evaluation output against the 12-dimension 1..5 rubric.

    Never clamps invalid scores, never divides 1..10 scores heuristically, and never
    backfills missing dimensions or empty evidence/advice.
    """
    if not isinstance(raw_data, dict):
        raise ValueError("Final evaluation payload must be a JSON object.")

    raw_scores = raw_data.get("rubric_scores")
    if not isinstance(raw_scores, list):
        raise ValueError("rubric_scores must be a list of 12 dimension objects.")

    canonical_by_lower = {dim.lower(): dim for dim in DEFAULT_RUBRIC_DIMENSIONS}
    scores_by_dim: dict[str, RubricDimensionScore] = {}

    for idx, item in enumerate(raw_scores):
        if not isinstance(item, dict):
            raise ValueError(f"rubric_scores[{idx}] must be an object.")

        raw_dim = str(item.get("dimension") or "").strip()
        canonical_dim = canonical_by_lower.get(raw_dim.lower())
        if canonical_dim is None:
            raise ValueError(
                f"Unknown rubric dimension '{raw_dim}'. Expected one of the 12 canonical dimensions."
            )
        if canonical_dim in scores_by_dim:
            raise ValueError(f"Duplicate rubric dimension '{canonical_dim}'.")

        raw_score = item.get("score")
        if isinstance(raw_score, bool) or not isinstance(raw_score, int):
            raise ValueError(
                f"Dimension '{canonical_dim}' has non-integer score {raw_score!r}; expected integer 1..5."
            )
        if raw_score < 1 or raw_score > 5:
            raise ValueError(
                f"Dimension '{canonical_dim}' score {raw_score} is out of range; expected integer 1..5."
            )

        evidence_text = str(item.get("evidence") or "").strip()
        if len(evidence_text) < 5 or evidence_text.lower() in _PLACEHOLDER_STRINGS:
            raise ValueError(
                f"Dimension '{canonical_dim}' is missing concrete evidence (>= 5 chars)."
            )

        critique_text = str(item.get("critique") or item.get("rationale") or "").strip()
        if len(critique_text) < 5 or critique_text.lower() in _PLACEHOLDER_STRINGS:
            raise ValueError(
                f"Dimension '{canonical_dim}' is missing improvement advice/critique (>= 5 chars)."
            )

        scores_by_dim[canonical_dim] = RubricDimensionScore(
            dimension=canonical_dim,
            score=raw_score,
            evidence=evidence_text,
            critique=critique_text,
        )

    missing_dims = [
        dim for dim in DEFAULT_RUBRIC_DIMENSIONS if dim not in scores_by_dim
    ]
    if missing_dims:
        raise ValueError(
            f"Incomplete evaluation: missing {len(missing_dims)} required rubric dimension(s): "
            + ", ".join(missing_dims)
        )

    ordered_scores = [scores_by_dim[dim] for dim in DEFAULT_RUBRIC_DIMENSIONS]
    computed_overall = _compute_deterministic_overall_score(ordered_scores)

    raw_overall = raw_data.get("overall_score")
    if raw_overall is not None:
        if isinstance(raw_overall, bool) or not isinstance(raw_overall, (int, float)):
            raise ValueError(
                f"Invalid overall_score {raw_overall!r}; expected numeric score in 0..100."
            )
        numeric_overall = float(raw_overall)
        if numeric_overall < 0.0 or numeric_overall > 100.0:
            raise ValueError(f"overall_score {numeric_overall} violates 0..100 range.")
        if abs(numeric_overall - computed_overall) > 15.0:
            raise ValueError(
                f"Contradictory overall_score ({numeric_overall}) vs rubric dimensions average "
                f"({computed_overall} computed from 12 dimensions)."
            )

    derived_rating = _derive_readiness_rating(computed_overall)
    raw_rating = str(raw_data.get("readiness_rating") or "").strip().upper()
    if raw_rating:
        if raw_rating not in VALID_READINESS_RATINGS:
            raise ValueError(
                f"Invalid readiness_rating '{raw_rating}'; expected one of {VALID_READINESS_RATINGS}."
            )
        if abs(_RATING_TIERS[raw_rating] - _RATING_TIERS[derived_rating]) >= 2:
            raise ValueError(
                f"Contradictory readiness_rating '{raw_rating}' for deterministic score {computed_overall}/100 ({derived_rating})."
            )

    executive_summary = str(raw_data.get("executive_summary") or "").strip()
    if len(executive_summary) < 10:
        raise ValueError(
            "Final evaluation executive_summary must be at least 10 characters."
        )

    key_strengths = _normalize_string_list(raw_data.get("key_strengths"))
    critical_gaps = _normalize_string_list(raw_data.get("critical_gaps"))
    recommended_next_steps = _normalize_string_list(
        raw_data.get("recommended_next_steps")
    )
    if not key_strengths:
        raise ValueError(
            "Final evaluation must include at least one key_strengths item."
        )
    if not recommended_next_steps:
        raise ValueError(
            "Final evaluation must include at least one recommended_next_steps item."
        )

    validated = FinalEvaluationSchema(
        overall_score=computed_overall,
        readiness_rating=derived_rating,  # type: ignore[arg-type]
        executive_summary=executive_summary,
        rubric_scores=ordered_scores,
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
        stmt = select(SystemDesignChallengeModel).where(
            SystemDesignChallengeModel.is_archived.is_(False)
        )
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
                SystemDesignChallengeModel.id == int(slug_or_id),
                SystemDesignChallengeModel.is_archived.is_(False),
            )
        else:
            stmt = select(SystemDesignChallengeModel).where(
                SystemDesignChallengeModel.slug == str(slug_or_id),
                SystemDesignChallengeModel.is_archived.is_(False),
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
    async def _list_active_challenge_summaries(
        db: AsyncSession,
    ) -> list[dict[str, str]]:
        """Return active (non-archived) challenge titles, slugs, and short summaries."""
        stmt = (
            select(SystemDesignChallengeModel)
            .where(SystemDesignChallengeModel.is_archived.is_(False))
            .order_by(SystemDesignChallengeModel.id.asc())
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "slug": str(row.slug),
                "title": str(row.title),
                "prompt_summary": str(row.prompt_summary or "").strip(),
            }
            for row in rows
        ]

    @staticmethod
    async def _assemble_challenge_prompt_context(
        db: AsyncSession,
        *,
        topic: str = "",
        application_id: int | None = None,
        difficulty: str = "MEDIUM",
        extra_context: str = "",
        use_web_search: bool = False,
        allow_duplicate: bool = False,
    ) -> dict[str, Any]:
        """Build shared rich role/notes/anti-duplication context for Local AI or Frontier Chat."""
        await SystemDesignService._ensure_challenges_seeded(db)
        topic_text = str(topic or "").strip()
        extra_text = str(extra_context or "").strip()
        norm_difficulty = str(difficulty or "MEDIUM").strip().upper() or "MEDIUM"
        app_context_parts: list[str] = []
        context_signals: list[str] = []
        search_seed = topic_text
        app_slug_hint = "custom"

        if application_id is not None:
            app_stmt = (
                select(ApplicationModel)
                .options(
                    selectinload(ApplicationModel.company),
                    selectinload(ApplicationModel.job_posting),
                    selectinload(ApplicationModel.events),
                )
                .where(ApplicationModel.id == int(application_id))
            )
            application = (await db.execute(app_stmt)).scalar_one_or_none()
            if not application:
                raise ValueError(f"Application {application_id} not found.")
            company = application.company
            company_name = company.name if company else "Target Company"
            role_title = application.position or "Software Engineer"
            app_slug_hint = _slugify(f"{company_name}-{role_title}")
            search_seed = f"{company_name} {role_title} {topic_text}".strip()
            app_context_parts.append(
                f"Target Role: {role_title} at {company_name} (status: {application.status})"
            )

            if application.notes and application.notes.strip():
                context_signals.append("Application Notes")
                app_context_parts.append(
                    "Candidate Application Notes (use for interview clues only; do not copy private details verbatim):\n"
                    + application.notes.strip()[:1200]
                )

            posting = application.job_posting
            if posting:
                has_posting_signal = False
                skills = posting.required_skills or []
                if skills:
                    has_posting_signal = True
                    app_context_parts.append(
                        f"Required Skills: {', '.join(str(s) for s in skills[:15])}"
                    )
                if posting.structured_spec and isinstance(
                    posting.structured_spec, dict
                ):
                    has_posting_signal = True
                    app_context_parts.append(
                        "Structured Job Spec:\n"
                        + json.dumps(posting.structured_spec, ensure_ascii=False)[:1000]
                    )
                if (
                    posting.description_markdown
                    and posting.description_markdown.strip()
                ):
                    has_posting_signal = True
                    app_context_parts.append(
                        "Job Description Excerpt:\n"
                        + posting.description_markdown.strip()[:1800]
                    )
                if has_posting_signal:
                    context_signals.append("Job Posting & Skills")

            if company:
                company_bits: list[str] = []
                if company.notes and company.notes.strip():
                    company_bits.append(f"Company Notes: {company.notes.strip()[:800]}")
                pros_items = _normalize_string_list(company.pros)
                if pros_items:
                    company_bits.append(
                        f"Engineering Highlights: {', '.join(pros_items)[:500]}"
                    )
                if company.company_research and isinstance(
                    company.company_research, dict
                ):
                    company_bits.append(
                        "Company Research: "
                        + json.dumps(company.company_research, ensure_ascii=False)[
                            :1000
                        ]
                    )
                if company_bits:
                    context_signals.append("Company Research")
                    app_context_parts.append("\n".join(company_bits))

            if application.match_analysis_payload and isinstance(
                application.match_analysis_payload, dict
            ):
                context_signals.append("Match Gap Analysis")
                app_context_parts.append(
                    "Candidate Match / Focus Signals:\n"
                    + json.dumps(
                        application.match_analysis_payload, ensure_ascii=False
                    )[:900]
                )

            events = sorted(
                list(application.events or []),
                key=lambda ev: (
                    ev.email_received_at.timestamp() if ev.email_received_at else 0.0,
                    ev.id or 0,
                ),
                reverse=True,
            )
            email_clues: list[str] = []
            for ev in events:
                subj = str(ev.email_subject or "").strip()
                summ = str(ev.email_summary or "").strip()
                if subj or summ:
                    label = f"[{ev.email_event_type or 'EMAIL'}] {subj}: {summ[:240]}".strip()
                    email_clues.append(f"- {label}")
                if len(email_clues) >= 5:
                    break
            if email_clues:
                context_signals.append("Interview Email Clues")
                app_context_parts.append(
                    "Recent Application / Interview Email Clues:\n"
                    + "\n".join(email_clues)
                )

        if extra_text:
            context_signals.append("Extra Focus Clues")

        if not topic_text and not app_context_parts and not extra_text:
            raise ValueError(
                "Provide either a Topic / Scenario Focus or link a tracked job application (application_id)."
            )

        existing_challenges = (
            await SystemDesignService._list_active_challenge_summaries(db)
        )

        web_snippets = ""
        if use_web_search and search_seed:
            web_snippets = await _fetch_web_grounding_snippets(
                db,
                f"{search_seed} system design architecture engineering blog scale",
            )
            if web_snippets:
                context_signals.append("Web Grounding")

        sys_prompt = CUSTOM_CHALLENGE_GENERATE_PROMPT.format(difficulty=norm_difficulty)
        user_sections: list[str] = []
        if topic_text:
            user_sections.append(f"Requested Topic / Scenario:\n{topic_text}")
        if app_context_parts:
            user_sections.append(
                "Job Application Context:\n" + "\n\n".join(app_context_parts)
            )
        if extra_text:
            user_sections.append(
                "Candidate Extra Focus / Interviewer Clues:\n" + extra_text
            )
        if web_snippets:
            user_sections.append(
                "Recent Web Search Context (ground engineering constraints cleanly):\n"
                + web_snippets
            )
        if existing_challenges:
            dedup_lines = [
                f"- {item['title']} — {item['prompt_summary'][:140]}"
                if item["prompt_summary"]
                else f"- {item['title']}"
                for item in existing_challenges
            ]
            user_sections.append(
                "EXISTING CHALLENGES — DO NOT DUPLICATE (choose a genuinely distinct system design domain & bottleneck):\n"
                + "\n".join(dedup_lines)
            )

        return {
            "topic_text": topic_text,
            "extra_context": extra_text,
            "difficulty": norm_difficulty,
            "allow_duplicate": bool(allow_duplicate),
            "app_slug_hint": app_slug_hint,
            "context_signals": context_signals,
            "existing_challenges": existing_challenges,
            "sys_prompt": sys_prompt,
            "user_prompt": "\n\n".join(user_sections),
        }

    @staticmethod
    async def prepare_challenge_gen_context(
        db: AsyncSession, payload_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 1 for SYSTEM_DESIGN_CHALLENGE_GEN: validate input, load app context, and fetch web snippets."""
        app_id = payload_dict.get("application_id")
        return await SystemDesignService._assemble_challenge_prompt_context(
            db,
            topic=str(payload_dict.get("topic") or ""),
            application_id=int(app_id) if app_id is not None else None,
            difficulty=str(payload_dict.get("difficulty") or "MEDIUM"),
            extra_context=str(payload_dict.get("extra_context") or ""),
            use_web_search=bool(payload_dict.get("use_web_search", False)),
            allow_duplicate=bool(payload_dict.get("allow_duplicate", False)),
        )

    @staticmethod
    async def run_challenge_gen_inference(
        db: AsyncSession, prepared_ctx: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 2 for SYSTEM_DESIGN_CHALLENGE_GEN: invoke AI model, validate, and repair once if needed."""
        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(
            db, task_type="SYSTEM_DESIGN_INTERVIEWER"
        )
        existing_challenges = list(prepared_ctx.get("existing_challenges") or [])
        allow_duplicate = bool(prepared_ctx.get("allow_duplicate", False))
        messages: list[Any] = [
            SystemMessage(content=str(prepared_ctx["sys_prompt"])),
            HumanMessage(content=str(prepared_ctx["user_prompt"])),
        ]

        last_error: ValueError | None = None
        for attempt in range(2):
            llm_res = await _invoke_llm_adaptive(
                chat_model,
                messages,
                tracer,
                db,
                task_type="SYSTEM_DESIGN_INTERVIEWER",
            )
            raw_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
            try:
                parsed = _parse_strict_json_object(raw_text)
                _validate_generated_challenge_payload(parsed)
                if not allow_duplicate:
                    dup = _find_similar_challenge(
                        str(parsed.get("title") or ""), existing_challenges
                    )
                    if dup:
                        raise DuplicateChallengeError(
                            f"Generated challenge '{parsed.get('title')}' closely overlaps existing challenge '{dup['title']}'.",
                            existing_title=dup["title"],
                            existing_slug=dup["slug"],
                        )
                return {
                    "parsed": parsed,
                    "provider_telemetry": get_model_telemetry_metadata(
                        chat_model, "SYSTEM_DESIGN_INTERVIEWER"
                    ),
                }
            except ValueError as err:
                last_error = err
                if attempt == 0:
                    messages.append(AIMessage(content=raw_text or "(empty response)"))
                    messages.append(
                        HumanMessage(
                            content=(
                                f"REPAIR REQUIRED: {err}\n"
                                "Return a complete, valid JSON challenge object matching the schema, "
                                "with 3 distinct variants and a title/domain that does NOT overlap any existing challenge."
                            )
                        )
                    )
                    continue
                raise err

        assert last_error is not None
        raise last_error

    @staticmethod
    async def _persist_validated_challenge(
        db: AsyncSession,
        parsed: dict[str, Any],
        *,
        topic_text: str = "",
        difficulty: str = "MEDIUM",
        allow_duplicate: bool = False,
        default_tags: list[str] | None = None,
    ) -> SystemDesignChallengeModel:
        """Validate, enforce uniqueness against active DB challenges, and persist row."""
        await SystemDesignService._ensure_challenges_seeded(db)
        _validate_generated_challenge_payload(parsed)
        title = str(
            parsed.get("title")
            or (
                f"Design: {topic_text[:60]}"
                if topic_text
                else "Tailored Role System Design"
            )
        ).strip()

        if not allow_duplicate:
            existing = await SystemDesignService._list_active_challenge_summaries(db)
            dup = _find_similar_challenge(title, existing)
            if dup:
                raise DuplicateChallengeError(
                    f"Challenge '{title}' closely overlaps existing challenge '{dup['title']}'. Pass allow_duplicate=True or adjust your topic to create anyway.",
                    existing_title=dup["title"],
                    existing_slug=dup["slug"],
                )

        slug = await SystemDesignService._unique_challenge_slug(db, title)
        raw_brief = parsed.get("interviewer_brief")
        interviewer_brief = _normalize_generated_brief(raw_brief)

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
            tags=_normalize_string_list(parsed.get("tags"))
            or list(default_tags or ["ai-generated"]),
            interviewer_brief=interviewer_brief,
            is_builtin=False,
        )
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)
        return challenge

    @staticmethod
    async def persist_generated_challenge(
        db: AsyncSession,
        prepared_ctx: dict[str, Any],
        parsed: dict[str, Any],
    ) -> SystemDesignChallengeModel:
        """Step 3 for SYSTEM_DESIGN_CHALLENGE_GEN: persist the generated challenge row."""
        return await SystemDesignService._persist_validated_challenge(
            db,
            parsed,
            topic_text=str(prepared_ctx.get("topic_text") or "").strip(),
            difficulty=str(prepared_ctx.get("difficulty") or "MEDIUM").strip().upper(),
            allow_duplicate=bool(prepared_ctx.get("allow_duplicate", False)),
            default_tags=["ai-generated"],
        )

    @staticmethod
    async def prepare_frontier_challenge_prompt(
        db: AsyncSession, payload: SystemDesignChallengeGenerateRequest
    ) -> ChallengeFrontierPromptResponse:
        """Assemble a copyable Markdown prompt for external Frontier models (Claude/ChatGPT/Gemini)."""
        ctx = await SystemDesignService._assemble_challenge_prompt_context(
            db,
            topic=payload.topic,
            application_id=payload.application_id,
            difficulty=payload.difficulty,
            extra_context=payload.extra_context,
            use_web_search=payload.use_web_search,
            allow_duplicate=payload.allow_duplicate,
        )
        existing_titles = [item["title"] for item in ctx["existing_challenges"]]
        markdown_prompt = "\n\n".join(
            [
                "# Tailored System Design Challenge Generator Prompt",
                "Copy and paste this entire prompt into Claude, ChatGPT, or Gemini. Then copy the returned JSON back into Job Tracker's **Import Challenge JSON** panel.",
                "---",
                "## System Instructions & Required JSON Schema",
                ctx["sys_prompt"],
                "---",
                "## Role, Application & Anti-Duplication Context",
                ctx["user_prompt"],
            ]
        )
        slug_base = _slugify(ctx["topic_text"] or ctx["app_slug_hint"] or "challenge")
        return ChallengeFrontierPromptResponse(
            filename=f"{slug_base}-frontier-challenge-prompt.md",
            markdown_prompt=markdown_prompt,
            context_signals=ctx["context_signals"],
            existing_challenge_titles=existing_titles,
        )

    @staticmethod
    async def import_frontier_challenge(
        db: AsyncSession, payload: ImportFrontierChallengeRequest
    ) -> SystemDesignChallengeModel:
        """Validate and persist a challenge JSON response produced by an external frontier chat."""
        parsed = _parse_strict_json_object(payload.raw_response)
        difficulty = (
            str(parsed.get("difficulty") or payload.difficulty or "MEDIUM")
            .strip()
            .upper()
        )
        return await SystemDesignService._persist_validated_challenge(
            db,
            parsed,
            difficulty=difficulty,
            allow_duplicate=bool(payload.allow_duplicate),
            default_tags=["frontier-imported"],
        )

    @staticmethod
    async def generate_custom_challenge(
        db: AsyncSession, payload: SystemDesignChallengeGenerateRequest
    ) -> SystemDesignChallengeModel:
        """Use the persistent queue worker pipeline to generate a tailored challenge."""
        from app.services.evaluation_worker import process_evaluation_task

        payload_dict = payload.model_dump()
        task = IntakeEvaluationTaskModel(
            task_type="SYSTEM_DESIGN_CHALLENGE_GEN",
            title_hint=f"Custom Challenge: {(payload.topic or 'Tailored Scenario').strip()[:80]}",
            status="QUEUED",
            stage="QUEUED",
            raw_text=(payload.topic or "")[:500] or None,
            result_json={
                "request_payload": payload_dict,
            },
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        await process_evaluation_task(task.id, db=db)
        await db.refresh(task)

        if task.status != "COMPLETED":
            err = task.error_message or "Challenge generation failed."
            lower = err.lower()
            if "closely overlaps existing challenge" in lower:
                raise DuplicateChallengeError(err)
            if (
                "not found" in lower
                or "provide either" in lower
                or "must be meaningful" in lower
                or "must include" in lower
                or "must define at least" in lower
                or "truncated" in lower
                or "json" in lower
            ):
                raise ValueError(err)
            raise RuntimeError(err)

        challenge_id = (task.result_json or {}).get("challenge_id")
        if challenge_id is None:
            raise RuntimeError("Challenge generation completed without challenge_id.")
        stmt = select(SystemDesignChallengeModel).where(
            SystemDesignChallengeModel.id == int(challenge_id)
        )
        challenge = (await db.execute(stmt)).scalar_one_or_none()
        if not challenge:
            raise RuntimeError(f"Generated challenge {challenge_id} not found.")
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
        if payload.tags is not None:
            normalized_tags = _normalize_string_list(payload.tags)
            challenge.tags = normalized_tags or ["custom"]

        # Only custom challenges permit editing expected_components and scale_notes;
        # built-in interviewer briefs remain protected from candidate edits/exposure.
        if not challenge.is_builtin:
            brief = dict(challenge.interviewer_brief or {})
            if payload.expected_components is not None:
                brief["expected_components"] = _normalize_string_list(
                    payload.expected_components
                )
            if payload.scale_notes is not None:
                hidden = dict(brief.get("hidden_context") or {})
                cleaned_scale = payload.scale_notes.strip()
                if cleaned_scale:
                    hidden["scale_notes"] = cleaned_scale
                else:
                    hidden.pop("scale_notes", None)
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
        """Archive built-in or session-referenced challenges; delete unused custom challenges."""
        challenge = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.id == challenge_id
                )
            )
        ).scalar_one_or_none()
        if not challenge:
            raise ValueError(f"System design challenge {challenge_id} not found.")

        linked_count = (
            await db.execute(
                select(func.count())
                .select_from(SystemDesignSessionModel)
                .where(SystemDesignSessionModel.challenge_id == challenge_id)
            )
        ).scalar_one()

        # Protect session history and diagrams on deletion: archive any challenge with
        # existing sessions (and always archive built-in challenges so reset restores them).
        if challenge.is_builtin or linked_count > 0:
            challenge.is_archived = True
            await db.commit()
            return

        await db.delete(challenge)
        await db.commit()

    @staticmethod
    def _get_session_brief(session: SystemDesignSessionModel) -> dict[str, Any]:
        """Return the isolated per-session brief, with safe fallback for legacy rows."""
        if isinstance(session.session_brief, dict) and session.session_brief:
            return session.session_brief
        challenge = session.challenge
        if not challenge or not isinstance(challenge.interviewer_brief, dict):
            return {}
        variants = _extract_brief_variants(challenge.interviewer_brief)
        if variants:
            target = (
                next(
                    (v for v in variants if v.get("variant_id") == session.variant_id),
                    None,
                )
                or variants[0]
            )
            return _build_session_brief(challenge, target)
        return dict(challenge.interviewer_brief)

    @staticmethod
    async def start_session(
        db: AsyncSession,
        challenge_id: int,
        application_id: int | None = None,
        mode: str = "ADAPTIVE",
        brief_seed: str | None = None,
        variant_id: str | None = None,
    ) -> SystemDesignSessionModel:
        if mode not in MODE_INSTRUCTIONS:
            raise ValueError(
                f"Invalid mode '{mode}'. Expected ADAPTIVE, INTERVIEW, or PRACTICE."
            )

        await SystemDesignService._ensure_challenges_seeded(db)
        challenge = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.id == challenge_id,
                    SystemDesignChallengeModel.is_archived.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not challenge:
            raise ValueError(f"System design challenge {challenge_id} not found.")

        last_variant_id = (
            await db.execute(
                select(SystemDesignSessionModel.variant_id)
                .where(SystemDesignSessionModel.challenge_id == challenge.id)
                .order_by(SystemDesignSessionModel.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        resolved_seed, resolved_variant_id, selection_mode, session_brief = (
            _select_session_variant(
                challenge,
                brief_seed=brief_seed,
                variant_id=variant_id,
                last_variant_id=last_variant_id,
            )
        )

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
            brief_seed=resolved_seed,
            variant_id=resolved_variant_id,
            variant_selection_mode=selection_mode,
            session_brief=session_brief,
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
    async def _get_session_for_update(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        """Fetch session row with PostgreSQL FOR UPDATE lock to serialize transitions."""
        stmt = (
            select(SystemDesignSessionModel)
            .options(selectinload(SystemDesignSessionModel.challenge))
            .where(SystemDesignSessionModel.id == session_id)
            .with_for_update(of=SystemDesignSessionModel)
        )
        session = (await db.execute(stmt)).scalar_one_or_none()
        if not session:
            raise ValueError(f"System design session {session_id} not found.")
        return session

    @staticmethod
    def _ensure_session_mutable(session: SystemDesignSessionModel) -> None:
        if session.status in ("COMPLETED", "ABANDONED") or session.stage == "COMPLETED":
            raise ValueError(
                f"System design session {session.id} is already {session.status} and cannot be modified."
            )

    @staticmethod
    def _has_substantive_ledger_content(ledger: dict[str, Any] | None) -> bool:
        data = ledger or {}
        return bool(
            data.get("functional_requirements")
            or data.get("non_functional_requirements")
            or data.get("scale_estimates")
        )

    @staticmethod
    def _ensure_requirements_locked(session: SystemDesignSessionModel) -> None:
        ledger = session.requirements_ledger or {}
        if not ledger.get("is_locked"):
            raise ValueError(
                "Requirements ledger must be locked before proceeding to architecture design or review."
            )
        if not SystemDesignService._has_substantive_ledger_content(ledger):
            raise ValueError(
                "Requirements ledger must contain at least one requirement or scale estimate before locking."
            )

    @staticmethod
    def _ensure_diagram_uploaded(session: SystemDesignSessionModel) -> None:
        if not (session.diagrams_metadata or []):
            raise ValueError(
                "At least one uploaded architecture diagram is required before this stage."
            )

    @staticmethod
    def _ensure_review_completed(session: SystemDesignSessionModel) -> None:
        if not (session.architecture_reviews or []):
            raise ValueError(
                "A completed architecture review is required before entering defence or evaluation."
            )

    @staticmethod
    def _ensure_defence_participated(session: SystemDesignSessionModel) -> None:
        has_candidate_turn = any(
            t.get("role") == "candidate" and str(t.get("content") or "").strip()
            for t in (session.defence_transcript or [])
        )
        if not has_candidate_turn:
            raise ValueError(
                "Candidate participation in Stage E (Interactive Defence) is required before final evaluation."
            )

    @staticmethod
    async def attach_active_queue_tasks(
        db: AsyncSession, sessions: list[SystemDesignSessionModel]
    ) -> list[SystemDesignSessionModel]:
        """Attach the latest active (QUEUED/PROCESSING/RUNNING) or failed queue task metadata to sessions."""
        if not sessions:
            return sessions
        session_id_strs = [str(s.id) for s in sessions]
        stmt = (
            select(IntakeEvaluationTaskModel)
            .where(
                IntakeEvaluationTaskModel.task_type.in_(
                    ["SYSTEM_DESIGN_REVIEW", "SYSTEM_DESIGN_EVALUATION"]
                ),
                IntakeEvaluationTaskModel.result_json["session_id"].astext.in_(
                    session_id_strs
                ),
            )
            .order_by(IntakeEvaluationTaskModel.id.desc())
        )
        tasks = (await db.execute(stmt)).scalars().all()
        latest_by_session: dict[int, IntakeEvaluationTaskModel] = {}
        for task in tasks:
            sid_raw = (task.result_json or {}).get("session_id")
            if sid_raw is None:
                continue
            sid = int(sid_raw)
            if sid not in latest_by_session:
                latest_by_session[sid] = task

        for session in sessions:
            latest = latest_by_session.get(int(session.id))
            if latest and latest.status in (
                "QUEUED",
                "PROCESSING",
                "RUNNING",
                "FAILED",
            ):
                result_json = (
                    latest.result_json if isinstance(latest.result_json, dict) else {}
                )
                checkpoint = (
                    result_json.get("_checkpoint")
                    if isinstance(result_json.get("_checkpoint"), dict)
                    else {}
                )
                telemetry = (
                    checkpoint.get("provider_telemetry")
                    if isinstance(checkpoint.get("provider_telemetry"), dict)
                    else {}
                )
                provider_label = telemetry.get("last_used_provider") or telemetry.get(
                    "primary_provider"
                )
                session.active_task_id = int(latest.id)
                session.active_task_status = str(latest.status)
                session.active_task_stage = str(latest.stage)
                session.active_task_type = str(latest.task_type)
                session.active_task_error = (
                    str(latest.error_message)
                    if latest.status == "FAILED" and latest.error_message
                    else None
                )
                session.active_task_attempt_count = int(
                    checkpoint.get("attempt_count") or 0
                )
                session.active_task_completed_steps = [
                    str(s) for s in (checkpoint.get("completed_steps") or [])
                ]
                session.active_task_provider = (
                    str(provider_label) if provider_label else None
                )
            else:
                session.active_task_id = None
                session.active_task_status = None
                session.active_task_stage = None
                session.active_task_type = None
                session.active_task_error = None
                session.active_task_attempt_count = 0
                session.active_task_completed_steps = []
                session.active_task_provider = None
        return sessions

    @staticmethod
    async def _ensure_no_active_queue_task(db: AsyncSession, session_id: int) -> None:
        stmt = (
            select(IntakeEvaluationTaskModel)
            .where(
                IntakeEvaluationTaskModel.task_type.in_(
                    ["SYSTEM_DESIGN_REVIEW", "SYSTEM_DESIGN_EVALUATION"]
                ),
                IntakeEvaluationTaskModel.status.in_(
                    ["QUEUED", "PROCESSING", "RUNNING"]
                ),
                IntakeEvaluationTaskModel.result_json["session_id"].astext
                == str(session_id),
            )
            .order_by(IntakeEvaluationTaskModel.id.desc())
        )
        active = (await db.execute(stmt)).scalars().first()
        if active is not None:
            raise ValueError(
                f"Background task {active.id} ({active.task_type}) is already {active.status} for this session."
            )

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: int) -> None:
        session = await SystemDesignService.get_session(db, session_id)
        await db.delete(session)
        await db.commit()

        session_dir = _get_storage_root() / f"session_{session_id}"
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
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        session.mode = mode
        if isinstance(session.diagram_guidance, dict) and session.diagram_guidance:
            guidance = dict(session.diagram_guidance)
            guidance["penalty_points"] = compute_diagram_hint_penalty(
                int(guidance.get("hints_used_count") or 0),
                bool(guidance.get("revealed_all_bank") or False),
                mode=mode,
            )
            guidance["is_practice_run"] = mode == "PRACTICE"
            session.diagram_guidance = guidance
            flag_modified(session, "diagram_guidance")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def send_requirements_message(
        db: AsyncSession,
        session_id: int,
        message_text: str,
        request_hint: bool = False,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        if session.stage != "REQUIREMENTS":
            raise ValueError(
                f"Requirements conversation is only allowed during REQUIREMENTS stage (current stage: {session.stage})."
            )
        if (session.requirements_ledger or {}).get("is_locked"):
            raise ValueError(
                "Requirements ledger is locked; unlock it before sending further requirements messages."
            )
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
            hidden_brief_json=json.dumps(
                SystemDesignService._get_session_brief(session), indent=2
            ),
            stage=session.stage,
            requirements_ledger_json=json.dumps(
                session.requirements_ledger or {}, indent=2
            ),
        )
        sys_prompt = f"{sys_prompt.rstrip()}\n{LIVE_LEDGER_SYNC_INSTRUCTION}"

        messages = _build_chat_messages(sys_prompt, transcript)

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(
            db, task_type="SYSTEM_DESIGN_INTERVIEWER"
        )
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            messages,
            tracer,
            db,
            task_type="SYSTEM_DESIGN_INTERVIEWER",
        )
        raw_reply_text = strip_reasoning_tags(_extract_text_content(llm_res.content))
        reply_text, updated_ledger = _split_reply_and_ledger_patch(
            raw_reply_text, session.requirements_ledger or {}
        )
        if not reply_text:
            reply_text = "I can share details on expected traffic, creation volume, retention/TTL, privacy, analytics, or latency SLAs—which requirement would you like to clarify first?"

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
        if updated_ledger is not None:
            session.requirements_ledger = updated_ledger
            flag_modified(session, "requirements_ledger")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def extract_requirements_ledger(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        if session.stage != "REQUIREMENTS":
            raise ValueError(
                f"Requirements ledger extraction is only allowed during REQUIREMENTS stage (current stage: {session.stage})."
            )
        if (session.requirements_ledger or {}).get("is_locked"):
            raise ValueError(
                "Requirements ledger is locked; unlock it before re-extracting requirements."
            )
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
            task_type="SYSTEM_DESIGN_INTERVIEWER",
        )

        raw_text = _extract_text_content(llm_res.content)
        parsed = _parse_strict_json_object(raw_text)
        session.requirements_ledger = _build_merged_ledger_dict(
            existing_ledger, parsed, merge_with_existing=False
        )
        flag_modified(session, "requirements_ledger")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def update_requirements_ledger(
        db: AsyncSession,
        session_id: int,
        payload: RequirementsLedgerUpdateRequest,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)

        if session.stage not in ("REQUIREMENTS", "DESIGN"):
            raise ValueError(
                f"Cannot modify requirements ledger once session reached {session.stage} stage."
            )
        if session.stage == "DESIGN" and (session.diagrams_metadata or []):
            raise ValueError(
                "Cannot modify or unlock the requirements ledger after a diagram has been uploaded."
            )

        ledger = RequirementsLedgerSchema(
            functional_requirements=_normalize_string_list(
                payload.functional_requirements
            ),
            non_functional_requirements=_normalize_string_list(
                payload.non_functional_requirements
            ),
            scale_estimates=_normalize_scale_dict(payload.scale_estimates),
            out_of_scope=_normalize_string_list(payload.out_of_scope),
            assumptions=_normalize_string_list(getattr(payload, "assumptions", [])),
            unresolved_questions=_normalize_string_list(
                getattr(payload, "unresolved_questions", [])
            ),
            notes=payload.notes.strip(),
            is_locked=payload.is_locked,
        )
        ledger_dict = ledger.model_dump()
        if (
            payload.is_locked
            and not SystemDesignService._has_substantive_ledger_content(ledger_dict)
        ):
            raise ValueError(
                "Add at least one functional requirement, non-functional requirement, or scale estimate before locking the ledger."
            )

        session.requirements_ledger = ledger_dict

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
    async def reveal_requirements_ledger(
        db: AsyncSession, session_id: int, lock_and_proceed: bool = False
    ) -> SystemDesignSessionModel:
        """Populate Stage 1 Requirements Ledger directly from the session brief so learners can inspect or jump to diagramming."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        if session.stage != "REQUIREMENTS":
            raise ValueError(
                f"Requirements can only be revealed during REQUIREMENTS stage (current stage: {session.stage})."
            )

        brief = SystemDesignService._get_session_brief(session)
        existing_ledger = dict(session.requirements_ledger or {})
        raw_scales = brief.get("scale_estimates")
        scale_dict = (
            {str(k): str(v) for k, v in raw_scales.items()}
            if isinstance(raw_scales, dict)
            else {}
        )
        raw_hidden = brief.get("hidden_context") or {}
        if isinstance(raw_hidden, dict) and raw_hidden.get("scale_notes"):
            scale_dict.setdefault("scale_notes", str(raw_hidden["scale_notes"]))

        brief_patch = {
            "functional_requirements": [
                str(x).strip()
                for x in (brief.get("functional_requirements") or [])
                if str(x).strip()
            ],
            "non_functional_requirements": [
                str(x).strip()
                for x in (brief.get("non_functional_requirements") or [])
                if str(x).strip()
            ],
            "scale_estimates": scale_dict,
            "out_of_scope": [
                str(x).strip()
                for x in (brief.get("out_of_scope") or [])
                if str(x).strip()
            ],
            "assumptions": [
                str(x).strip()
                for x in (brief.get("constraints") or brief.get("assumptions") or [])
                if str(x).strip()
            ],
            "unresolved_questions": [],
        }
        merged_ledger = _build_merged_ledger_dict(
            existing_ledger, brief_patch, merge_with_existing=True
        )

        guidance = dict(session.diagram_guidance or {})
        guidance["requirements_revealed"] = True
        guidance["is_coached"] = True
        session.diagram_guidance = guidance
        flag_modified(session, "diagram_guidance")

        if lock_and_proceed and SystemDesignService._has_substantive_ledger_content(
            merged_ledger
        ):
            merged_ledger["is_locked"] = True
            session.stage = "DESIGN"
        else:
            merged_ledger["is_locked"] = bool(existing_ledger.get("is_locked", False))

        session.requirements_ledger = merged_ledger
        session.updated_at = datetime.now(UTC)
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
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Diagram upload is only permitted after locking requirements (current stage: {session.stage})."
            )

        diagrams = list(session.diagrams_metadata or [])
        version = max((int(d.get("version", 0)) for d in diagrams), default=0) + 1
        filename = f"v{version}.{ext}"

        session_dir = _ensure_writable_session_dir(session_id)
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
        flag_modified(session, "diagrams_metadata")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def submit_canvas_diagram(
        db: AsyncSession,
        session_id: int,
        payload: CanvasDiagramSubmitRequest,
    ) -> SystemDesignSessionModel:
        """Normalize and persist an interactive Canvas Builder revision as vN.flow.json."""
        if not payload.nodes:
            raise ValueError(
                "Canvas diagram must include at least one architecture component before saving."
            )

        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Canvas diagram submission requires locking requirements first (current stage: {session.stage})."
            )

        normalized = normalize_flow_payload(payload.model_dump())
        if not normalized["nodes"]:
            raise ValueError(
                "Canvas diagram must include at least one valid component."
            )
        flow_summary = summarize_diagram_flow(normalized)
        disk_payload = {
            **normalized,
            "flow_summary": flow_summary,
        }
        serialized_bytes = json.dumps(disk_payload, indent=2).encode("utf-8")

        diagrams = list(session.diagrams_metadata or [])
        version = max((int(d.get("version", 0)) for d in diagrams), default=0) + 1
        filename = f"v{version}.flow.json"

        session_dir = _ensure_writable_session_dir(session_id)
        (session_dir / filename).write_bytes(serialized_bytes)

        entry = DiagramRevisionRead(
            version=version,
            filename=filename,
            mime_type="application/json",
            size_bytes=len(serialized_bytes),
            notes=normalized["notes"],
            uploaded_at=datetime.now(UTC).isoformat(),
            diagram_kind="canvas",
            node_count=int(flow_summary["node_count"]),
            edge_count=int(flow_summary["edge_count"]),
            components_preview=[str(n["label"]) for n in normalized["nodes"][:8]],
        ).model_dump()
        diagrams.append(entry)

        session.diagrams_metadata = diagrams
        flag_modified(session, "diagrams_metadata")
        guidance = dict(session.diagram_guidance or {})
        guidance["cloud_provider"] = normalized.get("cloud_provider", "generic")
        session.diagram_guidance = guidance
        flag_modified(session, "diagram_guidance")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def get_diagram_flow(
        db: AsyncSession, session_id: int, version: int
    ) -> dict[str, Any]:
        """Return stored Flow JSON payload for an interactive canvas diagram revision."""
        file_path, mime_type, _ = await SystemDesignService.get_diagram_file(
            db, session_id, version
        )
        if mime_type != "application/json":
            raise ValueError(
                f"Diagram revision v{version} is an uploaded image and does not contain editable canvas flow JSON."
            )
        return json.loads(file_path.read_text(encoding="utf-8"))

    @staticmethod
    async def request_diagram_hint(
        db: AsyncSession,
        session_id: int,
        payload: DiagramHintRequest,
    ) -> DiagramHintResponse:
        """Unlock component/path/topology coaching aligned with the challenge brief and locked ledger (0-pt deduction)."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Diagram coaching hints are available during the Design stage (current stage: {session.stage})."
            )

        is_practice = True
        brief = SystemDesignService._get_session_brief(session)
        blueprint = resolve_challenge_blueprint(
            brief, session.requirements_ledger or {}
        )
        required_specs = list(blueprint.get("required_components") or [])
        expected_paths = list(blueprint.get("expected_paths") or [])

        guidance = dict(session.diagram_guidance or {})
        hints_used_count = int(guidance.get("hints_used_count") or 0)
        revealed_all_bank = bool(guidance.get("revealed_all_bank") or False)

        already_revealed: list[dict[str, Any]] = []
        spec_by_key = {
            f"{str(spec.get('type_id') or '')}:{str(spec.get('label') or '').lower()}": spec
            for spec in required_specs
        }
        spec_by_type = {
            str(spec.get("type_id") or ""): spec
            for spec in required_specs
            if spec.get("type_id") and spec.get("type_id") != "custom"
        }

        for item in guidance.get("revealed_components") or []:
            if not isinstance(item, dict):
                continue
            enriched = dict(item)
            key = f"{str(enriched.get('type_id') or '')}:{str(enriched.get('label') or '').lower()}"
            matched_spec = spec_by_key.get(key) or spec_by_type.get(
                str(enriched.get("type_id") or "")
            )
            if matched_spec:
                enriched.setdefault(
                    "why_required", matched_spec.get("why_required", "")
                )
                enriched.setdefault(
                    "config_checklist", matched_spec.get("config_checklist", [])
                )
            already_revealed.append(enriched)

        revealed_keys = {
            f"{str(item.get('type_id') or '')}:{str(item.get('name') or item.get('label') or '').strip().lower()}"
            for item in already_revealed
        }
        revealed_types = {
            str(item.get("type_id") or "")
            for item in already_revealed
            if item.get("type_id") and item.get("type_id") != "custom"
        }

        def _is_already_revealed(spec: dict[str, Any]) -> bool:
            tid = str(spec.get("type_id") or "")
            key = f"{tid}:{str(spec.get('name') or spec.get('label') or '').strip().lower()}"
            if tid and tid != "custom" and tid in revealed_types:
                return True
            return key in revealed_keys

        current_nodes = [
            n for n in (payload.current_nodes or []) if isinstance(n, dict)
        ]
        current_edges = [
            e for e in (payload.current_edges or []) if isinstance(e, dict)
        ]
        flow_snapshot = {
            "nodes": current_nodes,
            "edges": current_edges,
            "notes": payload.current_notes or "",
        }

        unplaced_specs = [
            spec
            for spec in required_specs
            if not any(
                node_matches_expected(node, spec["name"])
                or (
                    spec["type_id"] != "custom"
                    and node.get("type_id") == spec["type_id"]
                )
                for node in current_nodes
            )
        ]
        unrevealed_candidates = [
            spec for spec in unplaced_specs if not _is_already_revealed(spec)
        ]

        newly_revealed: list[RevealedComponentHint] = []
        topology_feedback: dict[str, Any] | None = None
        next_connection_hint: dict[str, Any] | None = None
        returned_paths: list[dict[str, Any]] = []
        message = ""

        if not required_specs and payload.hint_mode in ("next_component", "reveal_all"):
            message = "No fixed component checklist is defined for this challenge — use canonical blocks or + Custom Block freely."
        elif payload.hint_mode == "next_component":
            topology_feedback = evaluate_canvas_topology(
                flow_snapshot, blueprint, brief
            )
            returned_paths = (
                topology_feedback.get("path_milestones") or expected_paths
                if revealed_all_bank
                else guidance.get("expected_paths", [])
            )
            if unrevealed_candidates:
                target_spec = unrevealed_candidates[0]
                already_revealed.append(dict(target_spec))
                revealed_keys.add(
                    f"{target_spec['type_id']}:{str(target_spec.get('name') or '').strip().lower()}"
                )
                if target_spec["type_id"] != "custom":
                    revealed_types.add(target_spec["type_id"])
                hints_used_count += 1
                newly_revealed.append(RevealedComponentHint(**target_spec))
                message = f"Unlocked guided block: {target_spec['label']}."
            elif unplaced_specs:
                message = (
                    "All expected components are already unlocked in your guided bank."
                )
            else:
                message = "Every expected component is already placed on your canvas."
        elif payload.hint_mode == "reveal_all":
            revealed_all_bank = True
            for target_spec in required_specs:
                if not _is_already_revealed(target_spec):
                    already_revealed.append(dict(target_spec))
                    revealed_keys.add(
                        f"{target_spec['type_id']}:{str(target_spec.get('name') or '').strip().lower()}"
                    )
                    if target_spec["type_id"] != "custom":
                        revealed_types.add(target_spec["type_id"])
                    newly_revealed.append(RevealedComponentHint(**target_spec))
            topology_feedback = evaluate_canvas_topology(
                flow_snapshot, blueprint, brief
            )
            returned_paths = topology_feedback.get("path_milestones") or expected_paths
            if newly_revealed:
                message = f"Unlocked all {len(required_specs)} recommended components & path checklist."
            else:
                message = f"Synced {len(required_specs)}-block reference bank & path checklist."
        elif payload.hint_mode == "check_topology":
            topology_feedback = evaluate_canvas_topology(
                flow_snapshot, blueprint, brief
            )
            returned_paths = topology_feedback.get("path_milestones") or expected_paths
            finding_count = len(topology_feedback.get("findings") or [])
            if finding_count == 0:
                message = "Topology check passed! All core paths and resilience notes look solid."
            else:
                message = f"Topology check found {finding_count} item(s) to review before Analyze."
        elif payload.hint_mode == "next_connection":
            topology_feedback = evaluate_canvas_topology(
                flow_snapshot, blueprint, brief
            )
            next_connection_hint = topology_feedback.get("next_connection_hint")
            returned_paths = topology_feedback.get("path_milestones") or expected_paths
            if next_connection_hint:
                hints_used_count += 1
                message = (
                    f"Next suggested wire: {next_connection_hint['source_label']} -> "
                    f"{next_connection_hint['target_label']} ({next_connection_hint['suggested_label']})."
                )
            else:
                message = "All reference Read, Write, and Async connections are already wired!"

        penalty_points = compute_diagram_hint_penalty(
            hints_used_count, revealed_all_bank, mode=session.mode
        )
        req_cloud = normalize_cloud_provider(
            getattr(payload, "cloud_provider", None) or guidance.get("cloud_provider")
        )
        updated_guidance = {
            **guidance,
            "cloud_provider": req_cloud,
            "hints_used_count": hints_used_count,
            "revealed_all_bank": revealed_all_bank,
            "revealed_components": already_revealed,
            "expected_paths": returned_paths
            if returned_paths
            else guidance.get("expected_paths", []),
            "coach_messages": list(guidance.get("coach_messages") or []),
            "last_topology_feedback": (
                topology_feedback
                if topology_feedback is not None
                else guidance.get("last_topology_feedback")
            ),
            "is_coached": True,
            "is_practice_run": True,
            "penalty_points": penalty_points,
        }
        session.diagram_guidance = updated_guidance
        session.updated_at = datetime.now(UTC)
        flag_modified(session, "diagram_guidance")
        await db.commit()

        refreshed = await SystemDesignService.get_session(db, session_id)
        remaining_count = sum(
            1 for spec in unplaced_specs if not _is_already_revealed(spec)
        )
        return DiagramHintResponse(
            newly_revealed=newly_revealed,
            revealed_components=already_revealed,
            expected_paths=updated_guidance["expected_paths"],
            topology_feedback=topology_feedback,
            next_connection_hint=next_connection_hint,
            is_coached=True,
            is_practice_run=is_practice,
            hints_used_count=hints_used_count,
            revealed_all_bank=revealed_all_bank,
            penalty_points=penalty_points,
            remaining_expected_count=remaining_count,
            message=message,
            session=SystemDesignSessionRead.model_validate(refreshed).model_dump(
                mode="json"
            ),
        )

    @staticmethod
    async def send_diagram_coach_message(
        db: AsyncSession,
        session_id: int,
        payload: DiagramCoachChatRequest,
    ) -> DiagramCoachChatResponse:
        """Interactive Studio Coach chat with optional click-to-apply canvas actions."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Studio Coach chat is available during the Design stage (current stage: {session.stage})."
            )

        user_message = (payload.message or "").strip()
        if not user_message:
            raise ValueError("Coach message cannot be empty.")

        challenge = session.challenge
        brief = SystemDesignService._get_session_brief(session)
        blueprint = resolve_challenge_blueprint(
            brief, session.requirements_ledger or {}
        )
        current_nodes = [
            n for n in (payload.current_nodes or []) if isinstance(n, dict)
        ]
        current_edges = [
            e for e in (payload.current_edges or []) if isinstance(e, dict)
        ]
        cloud_provider = normalize_cloud_provider(
            getattr(payload, "cloud_provider", None)
            or (session.diagram_guidance or {}).get("cloud_provider")
        )
        cloud_provider_map = {p["id"]: p["label"] for p in CLOUD_PROVIDERS}
        cloud_provider_label = cloud_provider_map.get(
            cloud_provider, "Generic (Cloud-Agnostic)"
        )
        flow_snapshot = {
            "cloud_provider": cloud_provider,
            "nodes": current_nodes,
            "edges": current_edges,
            "notes": payload.current_notes or "",
        }
        topology_feedback = evaluate_canvas_topology(flow_snapshot, blueprint, brief)
        action_dicts = build_coach_canvas_actions(
            blueprint,
            flow_snapshot,
            user_message=user_message,
            cloud_provider=cloud_provider,
        )
        suggested_actions = [CoachCanvasAction(**act) for act in action_dicts]

        guidance = dict(session.diagram_guidance or {})
        coach_history = list(guidance.get("coach_messages") or [])
        now_iso = datetime.now(UTC).isoformat()
        coach_history.append(
            {"role": "user", "content": user_message, "timestamp": now_iso}
        )

        # Build concise architectural context so the LLM coach gives grounded, cloud-aware guidance
        compact_canvas = {
            "cloud_provider": cloud_provider_label,
            "nodes": [
                {
                    "type_id": n.get("type_id") or (n.get("data") or {}).get("type_id"),
                    "label": n.get("label") or (n.get("data") or {}).get("label"),
                    "generic_label": n.get("generic_label")
                    or (n.get("data") or {}).get("generic_label"),
                    "tech_stack": n.get("tech_stack")
                    or (n.get("data") or {}).get("tech_stack"),
                }
                for n in current_nodes
            ],
            "edges": [
                {
                    "source": e.get("source"),
                    "target": e.get("target"),
                    "protocol": e.get("protocol")
                    or (e.get("data") or {}).get("protocol"),
                    "delivery_mode": e.get("delivery_mode")
                    or (e.get("data") or {}).get("delivery_mode"),
                    "label": e.get("label") or (e.get("data") or {}).get("text_label"),
                }
                for e in current_edges
            ],
            "notes": payload.current_notes or "",
        }
        sys_prompt = await _format_prompt_from_db(
            db,
            "system_design_coach",
            DEFAULT_PROMPTS["system_design_coach"],
            challenge_title=challenge.title,
            cloud_provider_label=cloud_provider_label,
            requirements_ledger_json=json.dumps(
                session.requirements_ledger or {}, indent=2
            ),
            blueprint_summary_json=json.dumps(
                {
                    "required_components": [
                        {
                            "type_id": c.get("type_id"),
                            "label": c.get("label"),
                            "why_required": c.get("why_required"),
                        }
                        for c in (blueprint.get("required_components") or [])
                    ],
                    "expected_paths": blueprint.get("expected_paths") or [],
                },
                indent=2,
            ),
            canvas_flow_json=json.dumps(compact_canvas, indent=2),
            topology_feedback_json=json.dumps(topology_feedback, indent=2),
            available_actions_json=json.dumps(action_dicts, indent=2),
        )
        llm_messages = [SystemMessage(content=sys_prompt)]
        for turn in coach_history[-8:]:
            role = str(turn.get("role") or "user")
            content = str(turn.get("content") or "").strip()
            if not content:
                continue
            if role in ("coach", "assistant"):
                llm_messages.append(AIMessage(content=content))
            else:
                llm_messages.append(HumanMessage(content=content))

        reply_text = ""
        try:
            tracer = PostgresTracer()
            chat_model = await get_task_chat_model(
                db, task_type="SYSTEM_DESIGN_INTERVIEWER"
            )
            llm_res = await _invoke_llm_adaptive(
                chat_model,
                llm_messages,
                tracer,
                db,
                task_type="SYSTEM_DESIGN_INTERVIEWER",
            )
            reply_text = strip_reasoning_tags(
                _extract_text_content(llm_res.content)
            ).strip()
        except Exception as exc:
            logger.warning(
                "Studio Coach LLM call failed, using deterministic fallback: %s", exc
            )

        if not reply_text:
            missing = topology_feedback.get("missing_components") or []
            next_hint = topology_feedback.get("next_connection_hint")
            parts = []
            if missing:
                names = ", ".join(
                    m.get("label", "") for m in missing[:3] if m.get("label")
                )
                parts.append(
                    f"Right now your canvas is missing key building blocks ({names}), though valid equivalent choices are always welcome."
                )
            if next_hint:
                parts.append(
                    f"Next clean wire: connect {next_hint.get('source_label')} -> {next_hint.get('target_label')} ({next_hint.get('suggested_label')})."
                )
            if suggested_actions:
                parts.append(
                    f"You can click '{suggested_actions[0].title}' below to apply this increment directly to your canvas."
                )
            reply_text = " ".join(parts) or (
                "Your core topology covers the primary flows! Make sure your Canvas Notes capture TTL/retention, capacity math, and failover strategy."
            )

        coach_history.append(
            {
                "role": "coach",
                "content": reply_text,
                "actions": [a.model_dump(mode="json") for a in suggested_actions],
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        coach_history = coach_history[-24:]

        hints_used_count = int(guidance.get("hints_used_count") or 0) + 1
        revealed_all_bank = bool(guidance.get("revealed_all_bank") or False)
        path_milestones = (
            topology_feedback.get("path_milestones")
            or blueprint.get("expected_paths")
            or []
        )
        updated_guidance = {
            **guidance,
            "cloud_provider": cloud_provider,
            "hints_used_count": hints_used_count,
            "revealed_all_bank": revealed_all_bank,
            "revealed_components": list(guidance.get("revealed_components") or []),
            "expected_paths": path_milestones,
            "coach_messages": coach_history,
            "last_topology_feedback": topology_feedback,
            "is_coached": True,
            "is_practice_run": True,
            "penalty_points": 0.0,
        }
        session.diagram_guidance = updated_guidance
        session.updated_at = datetime.now(UTC)
        flag_modified(session, "diagram_guidance")
        await db.commit()

        refreshed = await SystemDesignService.get_session(db, session_id)
        return DiagramCoachChatResponse(
            reply=reply_text,
            suggested_actions=suggested_actions,
            coach_messages=coach_history,
            topology_feedback=topology_feedback,
            expected_paths=path_milestones,
            is_coached=True,
            session=SystemDesignSessionRead.model_validate(refreshed).model_dump(
                mode="json"
            ),
        )

    @staticmethod
    def _collect_canvas_flow_summaries(
        session_id: int, diagrams: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Read saved Flow JSON files for canvas revisions without failing if missing."""
        session_dir = (_get_storage_root() / f"session_{session_id}").resolve()
        summaries: list[dict[str, Any]] = []
        for entry in diagrams or []:
            if not isinstance(entry, dict):
                continue
            kind = str(
                entry.get("diagram_kind")
                or (
                    "canvas"
                    if entry.get("mime_type") == "application/json"
                    else "image"
                )
            )
            if kind != "canvas":
                continue
            fname = str(entry.get("filename") or "")
            if not fname:
                continue
            fpath = (session_dir / fname).resolve()
            if not fpath.is_relative_to(session_dir) or not fpath.is_file():
                continue
            try:
                payload = json.loads(fpath.read_text(encoding="utf-8"))
                summaries.append(
                    {
                        "version": int(entry.get("version", 0)),
                        "notes": str(entry.get("notes") or ""),
                        "flow_summary": payload.get("flow_summary")
                        or summarize_diagram_flow(payload),
                    }
                )
            except Exception as exc:
                logger.warning(
                    "Unable to read canvas flow JSON %s for session %s: %s",
                    fpath,
                    session_id,
                    exc,
                )
        return summaries

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

        session_dir = (_get_storage_root() / f"session_{session_id}").resolve()
        file_path = (session_dir / str(entry["filename"])).resolve()
        if not file_path.is_relative_to(session_dir) or not file_path.is_file():
            raise ValueError(
                f"Diagram file for revision v{version} is missing on disk."
            )
        return (file_path, str(entry["mime_type"]), str(entry["filename"]))

    @staticmethod
    async def prepare_diagram_review_context(
        db: AsyncSession,
        session_id: int,
        diagram_version: int | None = None,
        use_web_search: bool = False,
    ) -> dict[str, Any]:
        """Step 1 for SYSTEM_DESIGN_REVIEW: validate session, resolve diagram file path, and build prompt."""
        session = await SystemDesignService.get_session(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Architecture review requires DESIGN stage or later (current stage: {session.stage})."
            )
        challenge = session.challenge
        diagrams = list(session.diagrams_metadata or [])

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
        diagram_kind = str(
            target_entry.get("diagram_kind")
            or ("canvas" if str(mime_type) == "application/json" else "image")
        )

        session_brief = SystemDesignService._get_session_brief(session)
        resolved_blueprint = resolve_challenge_blueprint(
            session_brief, session.requirements_ledger or {}
        )
        blueprint_summary = [
            {
                "label": comp["label"],
                "why_required": comp.get("why_required", ""),
            }
            for comp in resolved_blueprint.get("required_components", [])
        ]

        base_prompt = await _format_prompt_from_db(
            db,
            "system_design_reviewer",
            DEFAULT_PROMPTS["system_design_reviewer"],
            challenge_title=challenge.title,
            requirements_ledger_json=json.dumps(
                session.requirements_ledger or {}, indent=2
            ),
            hidden_brief_json=json.dumps(session_brief, indent=2),
            candidate_notes=str(target_entry.get("notes") or "None provided."),
        )
        blueprint_note = (
            "\n\nALIGNED SESSION BLUEPRINT (SHARED WITH CANDIDATE GUIDED BANK):\n"
            + json.dumps(blueprint_summary, indent=2)
        )
        canvas_note = ""
        if diagram_kind == "canvas":
            cloud_label = "Generic (Cloud-Agnostic)"
            try:
                flow_data = json.loads(file_path.read_text(encoding="utf-8"))
                c_id = normalize_cloud_provider(flow_data.get("cloud_provider"))
                cloud_label = next(
                    (p["label"] for p in CLOUD_PROVIDERS if p["id"] == c_id),
                    cloud_label,
                )
            except Exception:
                pass
            canvas_note = (
                f"\n\nCANVAS FLOW JSON INPUT (CLOUD LENS: {cloud_label}):\n"
                "The candidate built this architecture in the interactive Canvas Builder and supplied exact "
                "component nodes, cloud/tech stacks, directed connections (protocol + sync/async), and topology diagnostics. "
                "When a specific cloud lens is chosen, evaluate whether the chosen managed services fit the scale & requirements cleanly. "
                "Because structure and connections are unambiguous, leave `visual_clarifications_needed` empty unless "
                "a node's notes/purpose itself is unclear."
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

        sys_prompt = f"{base_prompt.strip()}{blueprint_note}{canvas_note}{web_section}\n\n{ARCHITECTURE_REVIEW_JSON_INSTRUCTIONS}"
        return {
            "session_id": session_id,
            "target_version": target_version,
            "diagram_kind": diagram_kind,
            "file_path": str(file_path),
            "mime_type": str(mime_type),
            "sys_prompt": sys_prompt,
            "resolved_blueprint": resolved_blueprint,
            "session_brief": session_brief,
        }

    @staticmethod
    async def run_diagram_vlm_inference(
        db: AsyncSession, prepared_ctx: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 2 for SYSTEM_DESIGN_REVIEW: analyze canvas Flow JSON (text LLM) or uploaded image (VLM)."""
        target_version = int(prepared_ctx["target_version"])
        file_path = Path(str(prepared_ctx["file_path"]))
        if not file_path.exists():
            raise FileNotFoundError(
                f"Diagram artifact for revision v{target_version} missing at {file_path}"
            )
        mime_type = str(prepared_ctx["mime_type"])
        diagram_kind = str(
            prepared_ctx.get("diagram_kind")
            or ("canvas" if mime_type == "application/json" else "image")
        )

        if diagram_kind == "canvas":
            flow_data = json.loads(file_path.read_text(encoding="utf-8"))
            flow_summary = flow_data.get("flow_summary") or summarize_diagram_flow(
                flow_data
            )
            blueprint = prepared_ctx.get("resolved_blueprint")
            topology_eval = (
                evaluate_canvas_topology(
                    flow_data,
                    blueprint,
                    prepared_ctx.get("session_brief"),
                )
                if isinstance(blueprint, dict)
                else {}
            )
            human_msg = HumanMessage(
                content=(
                    f"Inspect this structured interactive canvas architecture diagram (revision v{target_version}) "
                    "and return ONLY the JSON review object.\n\n"
                    f"TOPOLOGY SUMMARY:\n{json.dumps(flow_summary, indent=2)}\n\n"
                    f"DETERMINISTIC PRE-FLIGHT DIAGNOSTICS:\n{json.dumps(topology_eval.get('findings', []), indent=2)}\n\n"
                    f"FULL FLOW GRAPH:\n{json.dumps({'nodes': flow_data.get('nodes', []), 'edges': flow_data.get('edges', []), 'notes': flow_data.get('notes', '')}, indent=2)}"
                )
            )
        else:
            encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
            data_uri = f"data:{mime_type};base64,{encoded}"

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
            chat_model,
            [SystemMessage(content=str(prepared_ctx["sys_prompt"])), human_msg],
            tracer,
            db,
            task_type="SYSTEM_DESIGN_REVIEWER",
        )

        raw_text = _extract_text_content(llm_res.content)
        parsed = _parse_strict_json_object(raw_text)

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
        return {
            "review": review.model_dump(),
            "provider_telemetry": get_model_telemetry_metadata(
                chat_model, "SYSTEM_DESIGN_REVIEWER"
            ),
        }

    @staticmethod
    async def persist_architecture_review(
        db: AsyncSession, session_id: int, review_dict: dict[str, Any]
    ) -> SystemDesignSessionModel:
        """Step 3 for SYSTEM_DESIGN_REVIEW: lock session row, merge review, and seed defence prompt."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Architecture review requires DESIGN stage or later (current stage: {session.stage})."
            )
        target_version = int(review_dict["diagram_version"])

        reviews = [
            r
            for r in (session.architecture_reviews or [])
            if int(r.get("diagram_version", -1)) != target_version
        ]
        reviews.append(dict(review_dict))
        reviews.sort(key=lambda r: int(r.get("diagram_version", 0)))

        session.architecture_reviews = reviews
        if session.stage == "DESIGN":
            session.stage = "REVIEW"
        session.updated_at = datetime.now(UTC)
        flag_modified(session, "architecture_reviews")

        if not session.defence_transcript:
            brief_questions = _normalize_string_list(
                SystemDesignService._get_session_brief(session).get("defence_questions")
            )
            suggested = _normalize_string_list(
                review_dict.get("suggested_defence_topics")
            )
            opening_question = (
                suggested[0]
                if suggested
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
    async def analyze_diagram_architecture(
        db: AsyncSession,
        session_id: int,
        diagram_version: int | None = None,
        use_web_search: bool = False,
    ) -> SystemDesignSessionModel:
        prepared_ctx = await SystemDesignService.prepare_diagram_review_context(
            db,
            session_id=session_id,
            diagram_version=diagram_version,
            use_web_search=use_web_search,
        )
        inference_out = await SystemDesignService.run_diagram_vlm_inference(
            db, prepared_ctx
        )
        return await SystemDesignService.persist_architecture_review(
            db, session_id=session_id, review_dict=inference_out["review"]
        )

    @staticmethod
    async def enqueue_architecture_review(
        db: AsyncSession,
        session_id: int,
        diagram_version: int | None = None,
        use_web_search: bool = False,
    ) -> tuple[SystemDesignSessionModel, IntakeEvaluationTaskModel]:
        """Validate preconditions and enqueue Stage D architecture review task."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        if session.stage not in ("DESIGN", "REVIEW", "DEFENCE"):
            raise ValueError(
                f"Architecture review requires DESIGN stage or later (current stage: {session.stage})."
            )
        await SystemDesignService._ensure_no_active_queue_task(db, session_id)

        diagrams = list(session.diagrams_metadata or [])
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
            stage="QUEUED",
            raw_text=f"session_id={session_id}&diagram_version={target_version}",
            result_json={
                "session_id": session_id,
                "diagram_version": target_version,
                "use_web_search": bool(use_web_search),
            },
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        updated = await SystemDesignService.get_session(db, session_id)
        await SystemDesignService.attach_active_queue_tasks(db, [updated])
        return (updated, task)

    @staticmethod
    async def send_defence_message(
        db: AsyncSession,
        session_id: int,
        message_text: str,
        request_hint: bool = False,
        use_web_search: bool = False,
    ) -> SystemDesignSessionModel:
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        SystemDesignService._ensure_review_completed(session)
        if session.stage not in ("REVIEW", "DEFENCE"):
            raise ValueError(
                f"Interactive defence requires a completed architecture review (current stage: {session.stage})."
            )

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
            hidden_brief_json=json.dumps(
                SystemDesignService._get_session_brief(session), indent=2
            ),
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
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            messages,
            tracer,
            db,
            task_type="SYSTEM_DESIGN_INTERVIEWER",
        )
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
        if session.stage == "REVIEW":
            session.stage = "DEFENCE"
        flag_modified(session, "defence_transcript")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def prepare_final_evaluation_context(
        db: AsyncSession, session_id: int
    ) -> dict[str, Any]:
        """Step 1 for SYSTEM_DESIGN_EVALUATION: validate preconditions and assemble grading dossier."""
        session = await SystemDesignService.get_session(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        SystemDesignService._ensure_review_completed(session)
        SystemDesignService._ensure_defence_participated(session)
        if session.stage != "DEFENCE":
            raise ValueError(
                f"Final evaluation requires DEFENCE stage after answering defence prompts (current stage: {session.stage})."
            )
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
            hidden_brief_json=json.dumps(
                SystemDesignService._get_session_brief(session), indent=2
            ),
            dimensions_list="\n".join(f"- {dim}" for dim in DEFAULT_RUBRIC_DIMENSIONS),
        )
        sys_prompt += (
            f"\nCOACHING / HINT TELEMETRY: Candidate made {independent_turns_count} "
            f"independent turn(s) and {assisted_turns_count} assisted/hint-requested turn(s). "
            "Factor hint reliance fairly into discovery and trade-off independence scores."
        )

        diagrams_meta = list(session.diagrams_metadata or [])
        canvas_flows = SystemDesignService._collect_canvas_flow_summaries(
            session_id, diagrams_meta
        )
        diagram_guidance = dict(session.diagram_guidance or {})

        context_payload = {
            "mode": session.mode,
            "challenge_title": challenge.title,
            "initial_prompt": challenge.initial_prompt,
            "assisted_turns_count": assisted_turns_count,
            "independent_turns_count": independent_turns_count,
            "diagram_guidance": diagram_guidance,
            "requirements_transcript": session.requirements_transcript or [],
            "requirements_ledger": session.requirements_ledger or {},
            "diagram_revisions": diagrams_meta,
            "canvas_flows": canvas_flows,
            "architecture_reviews": session.architecture_reviews or [],
            "defence_transcript": session.defence_transcript or [],
        }
        return {
            "session_id": session_id,
            "sys_prompt": sys_prompt,
            "context_payload": context_payload,
        }

    @staticmethod
    async def run_final_evaluation_inference(
        db: AsyncSession, prepared_ctx: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 2 for SYSTEM_DESIGN_EVALUATION: invoke reviewer LLM, validate 12-dimension rubric, repair once if needed."""
        session_id = int(prepared_ctx["session_id"])
        sys_prompt = str(prepared_ctx["sys_prompt"])
        context_payload = dict(prepared_ctx["context_payload"])

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(db, task_type="SYSTEM_DESIGN_REVIEWER")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(
                    content=(
                        "Evaluate this complete System Design Lab session and return ONLY complete valid JSON:\n"
                        + json.dumps(context_payload, indent=2)
                    )
                ),
            ],
            tracer,
            db,
            task_type="SYSTEM_DESIGN_REVIEWER",
        )

        raw_text = _extract_text_content(llm_res.content)
        repair_used = False
        try:
            parsed = _parse_strict_json_object(raw_text)
            eval_dict = _validate_final_evaluation_payload(parsed)
        except ValueError as initial_err:
            logger.warning(
                "Stage F evaluation output failed strict validation for session %s (%s). Running one controlled repair retry.",
                session_id,
                initial_err,
            )
            repair_used = True
            repair_prompt = (
                "Your previous JSON evaluation failed strict validation and was rejected.\n"
                f"Validation Error: {initial_err}\n\n"
                "REPAIR INSTRUCTIONS:\n"
                "1. Output ONLY one complete valid JSON object (no markdown fences, no `<think>` reasoning).\n"
                "2. Include ALL 12 exact rubric dimension names in `rubric_scores`:\n"
                + "\n".join(f"- {dim}" for dim in DEFAULT_RUBRIC_DIMENSIONS)
                + "\n3. Every dimension `score` MUST be an integer from 1 to 5 (NEVER 1-10).\n"
                "4. `overall_score` MUST be 0..100 equal to `round((sum(all 12 scores) / 60) * 100, 1)`.\n"
                "5. Every dimension MUST include concrete `evidence` (>= 5 chars) and actionable `critique` advice (>= 5 chars).\n"
                "6. Keep every string concise (1 sentence) so the JSON completes cleanly.\n\n"
                f"Previous invalid output excerpt:\n{raw_text[:2500]}"
            )
            repair_res = await _invoke_llm_adaptive(
                chat_model,
                [
                    SystemMessage(content=sys_prompt),
                    HumanMessage(content=repair_prompt),
                ],
                tracer,
                db,
                task_type="SYSTEM_DESIGN_REVIEWER",
            )
            repaired_raw = _extract_text_content(repair_res.content)
            repaired_parsed = _parse_strict_json_object(repaired_raw)
            eval_dict = _validate_final_evaluation_payload(repaired_parsed)

        telemetry = get_model_telemetry_metadata(chat_model, "SYSTEM_DESIGN_REVIEWER")
        telemetry["repair_retry_used"] = repair_used
        return {
            "evaluation": eval_dict,
            "provider_telemetry": telemetry,
        }

    @staticmethod
    async def persist_final_evaluation(
        db: AsyncSession,
        session_id: int,
        eval_dict: dict[str, Any],
        *,
        idempotent_if_completed: bool = False,
    ) -> SystemDesignSessionModel:
        """Step 3 for SYSTEM_DESIGN_EVALUATION: lock session row and persist final scorecard."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        if (
            idempotent_if_completed
            and session.status == "COMPLETED"
            and session.final_evaluation is not None
        ):
            return await SystemDesignService.get_session(db, session_id)

        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        SystemDesignService._ensure_review_completed(session)
        SystemDesignService._ensure_defence_participated(session)
        if session.stage != "DEFENCE":
            raise ValueError(
                f"Final evaluation requires DEFENCE stage after answering defence prompts (current stage: {session.stage})."
            )

        adjusted_eval = _apply_guidance_penalty(
            eval_dict, session.diagram_guidance, session=session
        )
        now = datetime.now(UTC)
        session.final_evaluation = adjusted_eval
        session.overall_score = float(adjusted_eval["overall_score"])
        session.readiness_rating = str(adjusted_eval["readiness_rating"])
        session.stage = "COMPLETED"
        session.status = "COMPLETED"
        session.completed_at = now
        session.updated_at = now
        flag_modified(session, "final_evaluation")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)

    @staticmethod
    async def evaluate_session(
        db: AsyncSession, session_id: int
    ) -> SystemDesignSessionModel:
        """Synthesize and strictly validate the Stage F 12-dimension final scorecard."""
        prepared_ctx = await SystemDesignService.prepare_final_evaluation_context(
            db, session_id
        )
        inference_out = await SystemDesignService.run_final_evaluation_inference(
            db, prepared_ctx
        )
        return await SystemDesignService.persist_final_evaluation(
            db, session_id=session_id, eval_dict=inference_out["evaluation"]
        )

    @staticmethod
    async def enqueue_final_evaluation(
        db: AsyncSession, session_id: int
    ) -> tuple[SystemDesignSessionModel, IntakeEvaluationTaskModel]:
        """Validate all Stage F preconditions and enqueue an async IntakeEvaluationTaskModel."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        SystemDesignService._ensure_review_completed(session)
        SystemDesignService._ensure_defence_participated(session)
        if session.stage != "DEFENCE":
            raise ValueError(
                f"Final evaluation requires DEFENCE stage after answering defence prompts (current stage: {session.stage})."
            )
        await SystemDesignService._ensure_no_active_queue_task(db, session_id)

        task = IntakeEvaluationTaskModel(
            task_type="SYSTEM_DESIGN_EVALUATION",
            title_hint=f"System Design Evaluation: {session.challenge.title}",
            status="QUEUED",
            stage="QUEUED",
            raw_text=f"session_id={session_id}",
            result_json={
                "session_id": session_id,
                "challenge_slug": session.challenge.slug,
            },
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        updated = await SystemDesignService.get_session(db, session_id)
        await SystemDesignService.attach_active_queue_tasks(db, [updated])
        return (updated, task)

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
        canvas_flows = SystemDesignService._collect_canvas_flow_summaries(
            session.id, diagrams
        )
        diagram_guidance = dict(session.diagram_guidance or {})
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
            f"- **Scenario Seed / Variant**: #{session.brief_seed or 'legacy'} ({session.variant_id or 'default'})",
            f"- **Initial Prompt**: {challenge.initial_prompt}",
            "",
            "```json",
            json.dumps(SystemDesignService._get_session_brief(session), indent=2),
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
                    "canvas_flows": canvas_flows,
                    "diagram_guidance": diagram_guidance,
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
        """Parse and strictly validate an external frontier LLM scorecard back onto the session."""
        session = await SystemDesignService._get_session_for_update(db, session_id)
        SystemDesignService._ensure_session_mutable(session)
        SystemDesignService._ensure_requirements_locked(session)
        SystemDesignService._ensure_diagram_uploaded(session)
        SystemDesignService._ensure_review_completed(session)
        SystemDesignService._ensure_defence_participated(session)

        parsed = _parse_strict_json_object(raw_response)
        eval_dict = _validate_final_evaluation_payload(parsed)
        adjusted_eval = _apply_guidance_penalty(
            eval_dict, session.diagram_guidance, session=session
        )
        now = datetime.now(UTC)
        session.final_evaluation = adjusted_eval
        session.overall_score = float(adjusted_eval["overall_score"])
        session.readiness_rating = str(adjusted_eval["readiness_rating"])
        session.stage = "COMPLETED"
        session.status = "COMPLETED"
        session.completed_at = now
        session.updated_at = now
        flag_modified(session, "final_evaluation")
        await db.commit()
        return await SystemDesignService.get_session(db, session_id)
