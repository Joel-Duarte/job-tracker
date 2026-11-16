from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SystemDesignMode = Literal["ADAPTIVE", "INTERVIEW", "PRACTICE"]
SystemDesignStage = Literal["REQUIREMENTS", "DESIGN", "REVIEW", "DEFENCE", "COMPLETED"]
SystemDesignStatus = Literal["IN_PROGRESS", "COMPLETED", "ABANDONED"]


class ChallengeVariantSummary(BaseModel):
    """Candidate-safe summary of an available architectural variant profile."""

    variant_id: str
    title: str
    focus_summary: str = ""


def _extract_available_variants(brief: Any) -> list[dict[str, str]]:
    """Extract only candidate-safe variant labels from interviewer_brief['variants']."""
    if not isinstance(brief, dict):
        return []
    raw_variants = brief.get("variants")
    if not isinstance(raw_variants, list):
        return []
    summaries: list[dict[str, str]] = []
    for idx, item in enumerate(raw_variants, start=1):
        if not isinstance(item, dict):
            continue
        vid = str(item.get("variant_id") or f"variant-{idx}").strip()
        title = str(item.get("title") or f"Profile {idx}").strip()
        focus = str(item.get("focus_summary") or "").strip()
        if vid and title:
            summaries.append(
                {
                    "variant_id": vid,
                    "title": title,
                    "focus_summary": focus,
                }
            )
    return summaries


class SystemDesignChallengeRead(BaseModel):
    """Candidate-safe challenge projection.

    Explicitly omits ``interviewer_brief`` so hidden scale targets, expected
    architecture components, and scoring criteria never leak to candidates.
    For user-created custom challenges (``is_builtin=False``), exposes editable
    ``expected_components`` and ``scale_notes`` so the edit dialog preserves them.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    category: str
    difficulty: str
    prompt_summary: str
    initial_prompt: str
    tags: list[str] = Field(default_factory=list)
    is_builtin: bool
    is_archived: bool = False
    expected_components: list[str] = Field(default_factory=list)
    scale_notes: str = ""
    available_variants: list[ChallengeVariantSummary] = Field(default_factory=list)
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _populate_custom_editable_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            result = dict(value)
            is_builtin = bool(result.get("is_builtin", True))
            brief = result.get("interviewer_brief") or {}
            if "available_variants" not in result and "interviewer_brief" in result:
                result["available_variants"] = _extract_available_variants(brief)
            if is_builtin:
                result["expected_components"] = []
                result["scale_notes"] = ""
            elif "interviewer_brief" in result:
                hidden = brief.get("hidden_context") or {}
                if "expected_components" not in result:
                    result["expected_components"] = [
                        str(item)
                        for item in (brief.get("expected_components") or [])
                        if str(item).strip()
                    ]
                if "scale_notes" not in result:
                    result["scale_notes"] = str(hidden.get("scale_notes") or "")
            return result

        is_builtin = bool(getattr(value, "is_builtin", True))
        brief = getattr(value, "interviewer_brief", None) or {}
        available_variants = _extract_available_variants(brief)
        expected_components: list[str] = []
        scale_notes = ""
        if not is_builtin:
            hidden = brief.get("hidden_context") or {}
            expected_components = [
                str(item)
                for item in (brief.get("expected_components") or [])
                if str(item).strip()
            ]
            scale_notes = str(hidden.get("scale_notes") or "")

        return {
            "id": value.id,
            "slug": value.slug,
            "title": value.title,
            "category": value.category,
            "difficulty": value.difficulty,
            "prompt_summary": value.prompt_summary,
            "initial_prompt": value.initial_prompt,
            "tags": list(value.tags or []),
            "is_builtin": is_builtin,
            "is_archived": bool(getattr(value, "is_archived", False)),
            "expected_components": expected_components,
            "scale_notes": scale_notes,
            "available_variants": available_variants,
            "created_at": value.created_at,
        }


class RequirementsLedgerSchema(BaseModel):
    """Structured functional, non-functional, scale, scope, assumptions, and open-question ledger."""

    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    scale_estimates: dict[str, str] = Field(default_factory=dict)
    out_of_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    notes: str = ""
    is_locked: bool = False


class TranscriptTurnSchema(BaseModel):
    """Single message turn in Stage B requirements discovery or Stage E defence."""

    turn_index: int
    role: Literal["interviewer", "candidate"]
    content: str
    stage: str
    timestamp: str


class DiagramRevisionRead(BaseModel):
    """Metadata for a single diagram revision (image binary or flow JSON on disk)."""

    version: int
    filename: str
    mime_type: str
    size_bytes: int
    notes: str = ""
    uploaded_at: str
    diagram_kind: Literal["canvas", "image"] = "image"
    node_count: int | None = None
    edge_count: int | None = None
    components_preview: list[str] = Field(default_factory=list)


class DiagramFlowPosition(BaseModel):
    """2D canvas coordinates for a node."""

    x: float = 0.0
    y: float = 0.0


class DiagramFlowNode(BaseModel):
    """Single architecture component placed on the interactive canvas."""

    id: str = Field(..., min_length=1, max_length=100)
    type_id: str = Field(default="custom", max_length=80)
    label: str = Field(..., min_length=1, max_length=120)
    generic_label: str = Field(default="", max_length=120)
    cloud_provider: str = Field(default="generic", max_length=40)
    category: str = Field(default="compute_services", max_length=80)
    icon: str = Field(default="box", max_length=60)
    tech_stack: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=500)
    is_custom: bool = False
    position: DiagramFlowPosition = Field(default_factory=DiagramFlowPosition)


class DiagramFlowEdge(BaseModel):
    """Directed labeled data/request flow between two architecture components."""

    id: str = Field(default="", max_length=100)
    source: str = Field(..., min_length=1, max_length=100)
    target: str = Field(..., min_length=1, max_length=100)
    source_handle: str | None = Field(default=None, max_length=60)
    target_handle: str | None = Field(default=None, max_length=60)
    protocol: str = Field(default="", max_length=60)
    delivery_mode: Literal["sync", "async"] = "sync"
    label: str = Field(default="", max_length=160)


class CanvasDiagramSubmitRequest(BaseModel):
    """Payload submitted by the Stage 2 Interactive Canvas Builder."""

    cloud_provider: str = Field(default="generic", max_length=40)
    nodes: list[DiagramFlowNode] = Field(default_factory=list)
    edges: list[DiagramFlowEdge] = Field(default_factory=list)
    notes: str = Field(default="", max_length=4000)
    viewport: dict[str, Any] = Field(default_factory=dict)


class DiagramHintRequest(BaseModel):
    """Request for guided component/topology hints in the Design Studio."""

    hint_mode: Literal[
        "next_component",
        "reveal_all",
        "next_connection",
        "check_topology",
    ] = "next_component"
    cloud_provider: str = Field(default="generic", max_length=40)
    current_nodes: list[dict[str, Any]] = Field(default_factory=list)
    current_edges: list[dict[str, Any]] = Field(default_factory=list)
    current_notes: str = Field(default="", max_length=4000)


class RevealedComponentHint(BaseModel):
    """Unlocked component block revealed by diagram guidance."""

    name: str
    type_id: str
    label: str
    category: str
    icon: str
    hint_role: str
    why_required: str = ""
    config_checklist: list[str] = Field(default_factory=list)
    cloud_equivalents: dict[str, str] = Field(default_factory=dict)
    is_custom: bool = False


class CoachCanvasAction(BaseModel):
    """Executable non-destructive canvas placement/wiring suggestion from the Studio Coach."""

    id: str
    title: str
    description: str = ""
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


class DiagramHintResponse(BaseModel):
    """Response after unlocking component or topology guidance on a session."""

    newly_revealed: list[RevealedComponentHint] = Field(default_factory=list)
    revealed_components: list[dict[str, Any]] = Field(default_factory=list)
    expected_paths: list[dict[str, Any]] = Field(default_factory=list)
    reference_actions: list[CoachCanvasAction] = Field(default_factory=list)
    topology_feedback: dict[str, Any] | None = None
    next_connection_hint: dict[str, Any] | None = None
    is_practice_run: bool = False
    is_coached: bool = True
    hints_used_count: int = 0
    revealed_all_bank: bool = False
    penalty_points: float = 0.0
    remaining_expected_count: int = 0
    message: str = ""
    session: dict[str, Any] | None = None


class RequirementsRevealRequest(BaseModel):
    """Optional request payload for Stage 1 Reveal Requirements shortcut."""

    lock_and_proceed: bool = False


class DiagramCoachChatRequest(BaseModel):
    """Candidate message sent to the interactive Studio Coach alongside live canvas state."""

    message: str = Field(..., min_length=1, max_length=2000)
    cloud_provider: str = Field(default="generic", max_length=40)
    current_nodes: list[dict[str, Any]] = Field(default_factory=list)
    current_edges: list[dict[str, Any]] = Field(default_factory=list)
    current_notes: str = Field(default="", max_length=4000)


class DiagramCoachChatResponse(BaseModel):
    """Interactive Coach reply plus clickable Apply-to-Canvas architecture actions."""

    reply: str
    suggested_actions: list[CoachCanvasAction] = Field(default_factory=list)
    coach_messages: list[dict[str, Any]] = Field(default_factory=list)
    expected_paths: list[dict[str, Any]] = Field(default_factory=list)
    topology_feedback: dict[str, Any] | None = None
    is_coached: bool = True
    session: dict[str, Any] | None = None


class DiagramCatalogBlock(BaseModel):
    """Canonical architecture component metadata for the canvas palette."""

    type_id: str
    label: str
    category: str
    icon: str
    default_role: str
    keywords: list[str] = Field(default_factory=list)
    cloud_equivalents: dict[str, str] = Field(default_factory=dict)


class DiagramProviderInfo(BaseModel):
    """Selectable cloud provider lens metadata."""

    id: str
    label: str
    short_label: str


class DiagramCatalogCategory(BaseModel):
    """Display metadata for a canonical component category."""

    id: str
    label: str


class DiagramCatalogResponse(BaseModel):
    """Full backend-synced diagram component catalog."""

    categories: list[DiagramCatalogCategory]
    blocks: list[DiagramCatalogBlock]
    providers: list[DiagramProviderInfo] = Field(default_factory=list)


class ArchitectureReviewSchema(BaseModel):
    """Structured multimodal critique separating visual ambiguity from design flaws."""

    diagram_version: int
    interpreted_components: list[str] = Field(default_factory=list)
    interpreted_data_flows: list[str] = Field(default_factory=list)
    visual_clarifications_needed: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_components: list[str] = Field(default_factory=list)
    bottlenecks_and_spofs: list[str] = Field(default_factory=list)
    unnecessary_complexity: list[str] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    overall_impression: str
    suggested_defence_topics: list[str] = Field(default_factory=list)


class RubricDimensionScore(BaseModel):
    """Single scored rubric dimension backed by concrete session evidence."""

    dimension: str
    score: int = Field(ge=1, le=5)
    evidence: str = Field(min_length=5)
    critique: str

    @field_validator("evidence")
    @classmethod
    def _validate_non_blank_evidence(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise ValueError(
                "Evidence must contain at least 5 non-whitespace characters."
            )
        return cleaned


class FinalEvaluationSchema(BaseModel):
    """Evidence-backed final scorecard and actionable next steps."""

    overall_score: float = Field(ge=0.0, le=100.0)
    raw_score: float | None = Field(default=None, ge=0.0, le=100.0)
    guidance_penalty: float = Field(default=0.0, ge=0.0, le=100.0)
    assistance_mode: Literal["SOLO", "COACHED"] = "SOLO"
    xp_earned: int = Field(default=100, ge=0)
    readiness_rating: Literal[
        "NEEDS_PRACTICE", "DEVELOPING", "INTERVIEW_READY", "STRONG_HIRE"
    ]
    executive_summary: str
    rubric_scores: list[RubricDimensionScore]
    key_strengths: list[str]
    critical_gaps: list[str]
    recommended_next_steps: list[str]


class SystemDesignSessionCreate(BaseModel):
    """Payload to start a new system design practice or interview session."""

    challenge_id: int
    application_id: int | None = None
    mode: SystemDesignMode = "ADAPTIVE"
    brief_seed: str | None = Field(default=None, max_length=64)
    variant_id: str | None = Field(default=None, max_length=80)


class SystemDesignChallengeCreate(BaseModel):
    """Manual creation of a custom system design challenge."""

    title: str = Field(..., min_length=3, max_length=200)
    category: str = Field(default="DISTRIBUTED_SYSTEMS", max_length=80)
    difficulty: str = Field(default="MEDIUM", max_length=40)
    prompt_summary: str = Field(..., min_length=5, max_length=600)
    initial_prompt: str = Field(..., min_length=10, max_length=4000)
    tags: list[str] = Field(default_factory=list)
    expected_components: list[str] = Field(default_factory=list)
    scale_notes: str = ""


class SystemDesignChallengeUpdate(BaseModel):
    """Payload to edit an existing system design challenge (built-in or custom)."""

    title: str = Field(..., min_length=3, max_length=255)
    category: str = Field("DISTRIBUTED_SYSTEMS", min_length=2, max_length=64)
    difficulty: str = Field("MEDIUM", min_length=2, max_length=32)
    prompt_summary: str = Field(..., min_length=5, max_length=1500)
    initial_prompt: str = Field(..., min_length=10, max_length=4000)
    tags: list[str] | None = None
    expected_components: list[str] | None = None
    scale_notes: str | None = Field(None, max_length=2000)


class SystemDesignChallengeGenerateRequest(BaseModel):
    """AI generation of a custom system design challenge from a topic or job application."""

    topic: str = Field(default="", max_length=1000)
    application_id: int | None = None
    difficulty: str = Field(default="MEDIUM", max_length=40)
    use_web_search: bool = True
    extra_context: str = Field(default="", max_length=3000)
    allow_duplicate: bool = False


class ChallengeFrontierPromptResponse(BaseModel):
    """Self-contained Markdown prompt to generate a tailored challenge in any frontier chat."""

    filename: str
    markdown_prompt: str
    context_signals: list[str] = Field(default_factory=list)
    existing_challenge_titles: list[str] = Field(default_factory=list)


class ImportFrontierChallengeRequest(BaseModel):
    """Import a challenge JSON payload produced by an external frontier chat model."""

    raw_response: str = Field(..., min_length=20, max_length=100000)
    application_id: int | None = None
    difficulty: str = Field(default="MEDIUM", max_length=40)
    allow_duplicate: bool = False


def _strip_non_empty_text(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Message cannot be blank.")
    return cleaned


class RequirementsMessageRequest(BaseModel):
    """Candidate message submitted during Stage B requirements discovery."""

    message: str = Field(..., min_length=1, max_length=8000)
    request_hint: bool = False

    @field_validator("message")
    @classmethod
    def _validate_non_empty_message(cls, value: str) -> str:
        return _strip_non_empty_text(value)


class DiagramReviewRequest(BaseModel):
    """Optional target diagram revision for Stage D architecture analysis."""

    diagram_version: int | None = Field(default=None, ge=1)
    use_web_search: bool = False


class DefenceMessageRequest(BaseModel):
    """Candidate answer or defence statement submitted during Stage E."""

    message: str = Field(..., min_length=1, max_length=8000)
    request_hint: bool = False
    use_web_search: bool = False

    @field_validator("message")
    @classmethod
    def _validate_non_empty_message(cls, value: str) -> str:
        return _strip_non_empty_text(value)


class FrontierEvaluationPacketRead(BaseModel):
    """Self-contained markdown dossier for grading in a frontier model (Claude/GPT/Gemini)."""

    session_id: int
    challenge_title: str
    filename: str
    diagram_version: int | None = None
    markdown_packet: str


class ImportFrontierEvaluationRequest(BaseModel):
    """Paste raw JSON or Markdown+JSON output from an external frontier model to save scorecard."""

    raw_response: str = Field(..., min_length=10, max_length=60000)


class RequirementsLedgerUpdateRequest(BaseModel):
    """Manual edit and/or lock state update for the requirements ledger."""

    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    scale_estimates: dict[str, str] = Field(default_factory=dict)
    out_of_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    notes: str = ""
    is_locked: bool = False


class SessionModeUpdateRequest(BaseModel):
    """Switch session guidance mode between INTERVIEW and PRACTICE."""

    mode: SystemDesignMode


class SystemDesignSessionRead(BaseModel):
    """Candidate-facing session state returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    challenge_id: int
    application_id: int | None = None
    mode: str
    brief_seed: str | None = None
    variant_id: str | None = None
    variant_title: str | None = None
    variant_focus: str | None = None
    variant_selection_mode: str = "random"
    stage: str
    status: str
    requirements_transcript: list[dict[str, Any]] = Field(default_factory=list)
    requirements_ledger: dict[str, Any] = Field(default_factory=dict)
    diagrams_metadata: list[dict[str, Any]] = Field(default_factory=list)
    diagram_guidance: dict[str, Any] = Field(default_factory=dict)
    palette_extensions: list[dict[str, Any]] = Field(default_factory=list)
    capabilities_checklist: list[dict[str, Any]] = Field(default_factory=list)
    architecture_reviews: list[dict[str, Any]] = Field(default_factory=list)
    defence_transcript: list[dict[str, Any]] = Field(default_factory=list)
    final_evaluation: dict[str, Any] | None = None
    overall_score: float | None = None
    readiness_rating: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    challenge: SystemDesignChallengeRead | None = None
    active_task_id: int | None = None
    active_task_status: str | None = None
    active_task_stage: str | None = None
    active_task_type: str | None = None
    active_task_error: str | None = None
    active_task_attempt_count: int = 0
    active_task_completed_steps: list[str] = Field(default_factory=list)
    active_task_provider: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _mask_blind_variant_and_strip_brief(cls, value: Any) -> Any:
        def _get(field: str, default: Any = None) -> Any:
            if isinstance(value, dict):
                return value.get(field, default)
            return getattr(value, field, default)

        selection_mode = str(_get("variant_selection_mode", "random") or "random")
        status_val = str(_get("status", "IN_PROGRESS") or "IN_PROGRESS")
        reveal_variant = status_val == "COMPLETED" or selection_mode != "random"
        raw_brief = _get("session_brief")
        session_brief = raw_brief if isinstance(raw_brief, dict) else {}

        raw_exts = session_brief.get("diagram_palette_extensions") or []
        safe_exts: list[dict[str, Any]] = []
        seen_ext_keys: set[str] = set()
        if isinstance(raw_exts, list):
            for idx, ext in enumerate(raw_exts):
                if not isinstance(ext, dict):
                    continue
                label = str(ext.get("label") or ext.get("name") or "").strip()
                if not label:
                    continue
                tid = str(ext.get("type_id") or "").strip() or f"scenario-{idx + 1}"
                dedup_key = f"{tid}:{label.lower()}"
                if dedup_key in seen_ext_keys:
                    continue
                seen_ext_keys.add(dedup_key)
                safe_exts.append(
                    {
                        "type_id": tid,
                        "label": label[:120],
                        "category": str(
                            ext.get("category") or "compute_services"
                        ).strip(),
                        "icon": str(ext.get("icon") or "box").strip(),
                        "default_role": str(
                            ext.get("default_role")
                            or ext.get("hint_role")
                            or f"Scenario-specific domain component: {label}."
                        ).strip(),
                        "is_custom": True,
                        "is_scenario_extension": True,
                    }
                )

        data = (
            dict(value)
            if isinstance(value, dict)
            else {
                "id": _get("id"),
                "challenge_id": _get("challenge_id"),
                "application_id": _get("application_id"),
                "mode": _get("mode"),
                "brief_seed": _get("brief_seed"),
                "variant_id": _get("variant_id"),
                "variant_selection_mode": selection_mode,
                "stage": _get("stage"),
                "status": status_val,
                "requirements_transcript": list(_get("requirements_transcript") or []),
                "requirements_ledger": dict(_get("requirements_ledger") or {}),
                "diagrams_metadata": list(_get("diagrams_metadata") or []),
                "diagram_guidance": dict(_get("diagram_guidance") or {}),
                "architecture_reviews": list(_get("architecture_reviews") or []),
                "defence_transcript": list(_get("defence_transcript") or []),
                "final_evaluation": _get("final_evaluation"),
                "overall_score": _get("overall_score"),
                "readiness_rating": _get("readiness_rating"),
                "created_at": _get("created_at"),
                "updated_at": _get("updated_at"),
                "completed_at": _get("completed_at"),
                "challenge": _get("challenge"),
                "active_task_id": _get("active_task_id"),
                "active_task_status": _get("active_task_status"),
                "active_task_stage": _get("active_task_stage"),
                "active_task_type": _get("active_task_type"),
                "active_task_error": _get("active_task_error"),
                "active_task_attempt_count": int(
                    _get("active_task_attempt_count") or 0
                ),
                "active_task_completed_steps": list(
                    _get("active_task_completed_steps") or []
                ),
                "active_task_provider": _get("active_task_provider"),
            }
        )
        data["palette_extensions"] = safe_exts
        from app.services.diagram_catalog import resolve_challenge_blueprint

        blueprint_for_caps = resolve_challenge_blueprint(
            session_brief, data.get("requirements_ledger") or {}
        )
        data["capabilities_checklist"] = [
            {
                "id": str(c.get("id") or ""),
                "title": str(c.get("title") or ""),
                "goal": str(c.get("goal") or ""),
                "accepted_type_groups": list(c.get("accepted_type_groups") or []),
                "defence_tradeoff": str(c.get("defence_tradeoff") or ""),
            }
            for c in (blueprint_for_caps.get("required_capabilities") or [])
            if isinstance(c, dict)
        ]
        data.pop("session_brief", None)
        if reveal_variant:
            data["variant_title"] = session_brief.get("variant_title") or data.get(
                "variant_title"
            )
            data["variant_focus"] = (
                session_brief.get("focus_summary")
                or session_brief.get("variant_focus")
                or data.get("variant_focus")
            )
        else:
            data["variant_id"] = None
            data["variant_title"] = None
            data["variant_focus"] = None
        return data
