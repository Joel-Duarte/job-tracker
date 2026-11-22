from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_design import (
    SystemDesignChallengeModel,
    SystemDesignSessionModel,
)
from app.schemas.system_design import (
    ArchitectureReviewSchema,
    DiagramRevisionRead,
    FinalEvaluationSchema,
    RequirementsLedgerSchema,
    RubricDimensionScore,
    SystemDesignChallengeRead,
    SystemDesignSessionRead,
)
from app.services.system_design_seed import (
    CURATED_CHALLENGES,
    seed_system_design_challenges,
)

EXPECTED_SLUGS = {
    "url-shortener",
    "spotify-100k",
    "realtime-notifications",
    "ride-sharing",
    "distributed-job-queue",
    "video-streaming",
    "chat-system",
    "rate-limiter",
}

FORBIDDEN_SECRET_KEYS = (
    "interviewer_brief",
    "session_brief",
    "hidden_context",
    "expected_functional_requirements",
    "expected_non_functional_requirements",
    "common_bottlenecks_and_spofs",
    "over_engineering_traps",
    "defence_questions",
)


def test_curated_challenge_catalog_has_three_profiles_and_consistent_storage_math():
    challenges = {challenge["slug"]: challenge for challenge in CURATED_CHALLENGES}
    assert len(challenges) == 8
    assert all(
        len(challenge["interviewer_brief"]["variants"]) == 3
        for challenge in challenges.values()
    )

    url_shortener = challenges["url-shortener"]["interviewer_brief"]
    assert (
        "150 GB raw mapping data"
        in url_shortener["scale_estimates"]["payload_and_storage"]
    )
    assert "150 GB raw mapping data" in url_shortener["hidden_context"]["retention"]
    assert "1.5 TB raw mapping data" not in str(url_shortener)

    video = challenges["video-streaming"]["interviewer_brief"]
    assert "~250 TB/day raw ingress" in video["scale_estimates"]["daily_uploads"]
    assert (
        "retention, rendition expansion, replication, and budget are open requirements"
        in video["hidden_context"]["raw_ingress_baseline"]
    )

    chat = challenges["chat-system"]["interviewer_brief"]
    assert "~4 TB/day raw text bodies" in chat["scale_estimates"]["daily_messages"]
    assert "~1.46 PB/year" in chat["hidden_context"]["retention_and_storage"]
    assert (
        "retention and deletion policy are open requirements"
        in chat["hidden_context"]["retention_and_storage"]
    )


def test_alembic_migration_metadata_integrity():
    """Verify the system design migration chain resolves cleanly to 7c9d1e3f5a2b as single head."""
    backend_dir = Path(__file__).resolve().parents[2]
    alembic_ini = backend_dir / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["9c2f4a6b8d10"]

    rev_sd = script.get_revision("5a7b9c1d3e5f")
    assert rev_sd is not None
    assert rev_sd.down_revision == "4f6e8a1c3d5b"

    rev_arch = script.get_revision("6b8c0d2e4f1a")
    assert rev_arch is not None
    assert rev_arch.down_revision == "5a7b9c1d3e5f"

    rev_seed = script.get_revision("7c9d1e3f5a2b")
    assert rev_seed is not None
    assert rev_seed.down_revision == "6b8c0d2e4f1a"

    rev_guidance = script.get_revision("8d1e2f3a4b5c")
    assert rev_guidance is not None
    assert rev_guidance.down_revision == "7c9d1e3f5a2b"


def test_evidence_based_rubric_requires_concrete_evidence():
    """RubricDimensionScore must reject missing, short, or blank evidence."""
    with pytest.raises(ValidationError):
        RubricDimensionScore(
            dimension="Scalability",
            score=4,
            critique="Good partitioning strategy.",
        )

    with pytest.raises(ValidationError):
        RubricDimensionScore(
            dimension="Scalability",
            score=4,
            evidence="ok",
            critique="Too short.",
        )

    with pytest.raises(ValidationError):
        RubricDimensionScore(
            dimension="Scalability",
            score=4,
            evidence="     ",
            critique="Blank whitespace must fail.",
        )

    valid = RubricDimensionScore(
        dimension="Scalability",
        score=4,
        evidence="Diagram v2 shards Redis Geo index by city_id to isolate hotspots.",
        critique="Addresses city-level traffic skew cleanly.",
    )
    assert valid.score == 4


def test_candidate_challenge_schema_strips_hidden_brief():
    """Even if validated from a dict containing interviewer_brief, schema strips hidden built-in brief."""
    sample = dict(CURATED_CHALLENGES[0])
    sample.update({"id": 1, "is_builtin": True, "created_at": "2026-11-15T00:00:00Z"})

    projected = SystemDesignChallengeRead.model_validate(sample)
    dumped = projected.model_dump()
    dumped_json = projected.model_dump_json()

    assert "interviewer_brief" not in dumped
    assert projected.expected_components == []
    assert projected.scale_notes == ""
    for secret_key in FORBIDDEN_SECRET_KEYS:
        assert secret_key not in dumped
        assert secret_key not in dumped_json

    custom_sample = dict(sample)
    custom_sample["is_builtin"] = False
    custom_projected = SystemDesignChallengeRead.model_validate(custom_sample)
    assert custom_projected.expected_components == list(
        sample["interviewer_brief"].get("expected_components", [])
    )
    for secret_key in FORBIDDEN_SECRET_KEYS:
        assert secret_key not in custom_projected.model_dump()


@pytest.mark.asyncio
async def test_seed_system_design_challenges_idempotent(db_session: AsyncSession):
    """Seeding inserts all 8 curated challenges and stays idempotent on repeat runs."""
    first_inserted = await seed_system_design_challenges(db_session)
    assert first_inserted == 8

    second_inserted = await seed_system_design_challenges(db_session)
    assert second_inserted == 0

    count_stmt = select(func.count()).select_from(SystemDesignChallengeModel)
    total = (await db_session.execute(count_stmt)).scalar_one()
    assert total == 8

    challenges_stmt = select(SystemDesignChallengeModel)
    challenges = (await db_session.execute(challenges_stmt)).scalars().all()
    assert {c.slug for c in challenges} == EXPECTED_SLUGS

    for challenge in challenges:
        assert challenge.interviewer_brief, f"{challenge.slug} missing hidden brief"
        assert "hidden_context" in challenge.interviewer_brief
        assert "defence_questions" in challenge.interviewer_brief


@pytest.mark.asyncio
async def test_hidden_interviewer_brief_never_leaks_from_orm(
    db_session: AsyncSession,
):
    """Candidate-facing challenge and session schemas must never serialize hidden ground truth."""
    await seed_system_design_challenges(db_session)
    challenges = (
        (await db_session.execute(select(SystemDesignChallengeModel))).scalars().all()
    )

    for challenge in challenges:
        challenge_dto = SystemDesignChallengeRead.model_validate(challenge)
        challenge_dict = challenge_dto.model_dump()
        challenge_json = challenge_dto.model_dump_json()

        assert challenge_dto.expected_components == []
        assert challenge_dto.scale_notes == ""
        for secret_key in FORBIDDEN_SECRET_KEYS:
            assert secret_key not in challenge_dict
            assert secret_key not in challenge_json

    spotify = next(c for c in challenges if c.slug == "spotify-100k")
    session = SystemDesignSessionModel(
        challenge_id=spotify.id,
        mode="INTERVIEW",
        stage="REQUIREMENTS",
        status="IN_PROGRESS",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session, attribute_names=["challenge"])

    session_dto = SystemDesignSessionRead.model_validate(session)
    session_dict = session_dto.model_dump()
    session_json = session_dto.model_dump_json()

    assert session_dto.challenge is not None
    assert session_dto.challenge.slug == "spotify-100k"
    assert "30,000 DAU" not in session_json
    for secret_key in FORBIDDEN_SECRET_KEYS:
        assert secret_key not in (session_dict.get("challenge") or {})
        assert secret_key not in session_json


@pytest.mark.asyncio
async def test_session_lifecycle_jsonb_persistence(db_session: AsyncSession):
    """Verify Requirements Ledger, Diagram metadata, Review, and Evaluation JSONB persistence."""
    await seed_system_design_challenges(db_session)
    challenge = (
        await db_session.execute(
            select(SystemDesignChallengeModel).where(
                SystemDesignChallengeModel.slug == "url-shortener"
            )
        )
    ).scalar_one()

    ledger = RequirementsLedgerSchema(
        functional_requirements=["Shorten URLs", "HTTP 302 redirect"],
        non_functional_requirements=["p99 redirect < 30ms", "99.99% availability"],
        scale_estimates={"read_qps_peak": "12000", "write_qps_peak": "120"},
        out_of_scope=["User signup flow"],
        is_locked=True,
    )
    diagram = DiagramRevisionRead(
        version=1,
        filename="v1.png",
        mime_type="image/png",
        size_bytes=4096,
        notes="Initial stateless redirect cluster + Redis + Postgres.",
        uploaded_at="2026-11-15T01:20:00Z",
    )
    review = ArchitectureReviewSchema(
        diagram_version=1,
        interpreted_components=["Load Balancer", "API Servers", "Redis", "PostgreSQL"],
        interpreted_data_flows=["Client -> LB -> API -> Redis/Postgres"],
        visual_clarifications_needed=[
            "Label whether Redis stores eviction TTL policy."
        ],
        strengths=["Clean cache-aside read path"],
        missing_components=["Async analytics queue"],
        bottlenecks_and_spofs=["Single PostgreSQL writer on ID sequence"],
        unnecessary_complexity=[],
        requirement_gaps=[],
        overall_impression="Solid baseline; clarify key generation strategy.",
        suggested_defence_topics=["Key generation collision safety"],
    )
    evaluation = FinalEvaluationSchema(
        overall_score=84.5,
        readiness_rating="FORMATIVE",
        executive_summary="Strong requirements clarity and justified caching design.",
        rubric_scores=[
            RubricDimensionScore(
                dimension="Requirements Clarity",
                score=5,
                evidence="Asked for 100:1 read/write ratio before sketching storage.",
                critique="Captured peak QPS and p99 SLA accurately.",
            )
        ],
        key_strengths=["Decoupled read cache path"],
        critical_gaps=["Add async worker for click counters"],
        recommended_next_steps=["Practice KGS range pre-allocation trade-offs"],
    )

    session = SystemDesignSessionModel(
        challenge_id=challenge.id,
        mode="PRACTICE",
        stage="COMPLETED",
        status="COMPLETED",
        requirements_ledger=ledger.model_dump(),
        diagrams_metadata=[diagram.model_dump()],
        architecture_reviews=[review.model_dump()],
        final_evaluation=evaluation.model_dump(),
        overall_score=evaluation.overall_score,
        readiness_rating=evaluation.readiness_rating,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    reloaded = (
        await db_session.execute(
            select(SystemDesignSessionModel).where(
                SystemDesignSessionModel.id == session.id
            )
        )
    ).scalar_one()

    assert reloaded.mode == "PRACTICE"
    assert reloaded.stage == "COMPLETED"
    assert reloaded.requirements_ledger["is_locked"] is True
    assert len(reloaded.diagrams_metadata) == 1
    assert reloaded.diagrams_metadata[0]["version"] == 1
    assert reloaded.architecture_reviews[0]["visual_clarifications_needed"] == [
        "Label whether Redis stores eviction TTL policy."
    ]
    assert reloaded.final_evaluation is not None
    assert reloaded.final_evaluation["readiness_rating"] == "FORMATIVE"
    assert reloaded.overall_score == pytest.approx(84.5)


def test_curated_challenges_have_three_distinct_structured_variants():
    """Every curated challenge must define 3 valid variants and expose only safe metadata."""
    required_fields = (
        "variant_id",
        "title",
        "focus_summary",
        "business_context",
        "scale_estimates",
        "functional_requirements",
        "non_functional_requirements",
        "constraints",
        "priorities",
        "out_of_scope",
        "expected_components",
        "defence_questions",
    )
    assert len(CURATED_CHALLENGES) == 8

    for challenge in CURATED_CHALLENGES:
        brief = challenge["interviewer_brief"]
        variants = brief.get("variants") or []
        assert len(variants) == 3, f"{challenge['slug']} should have 3 variants"
        variant_ids = [v.get("variant_id") for v in variants]
        assert len(set(variant_ids)) == 3, (
            f"Duplicate variant_ids in {challenge['slug']}"
        )

        for variant in variants:
            for key in required_fields:
                assert variant.get(key), (
                    f"{challenge['slug']} variant {variant.get('variant_id')} missing {key}"
                )

        # Verify candidate-facing ChallengeRead exposes only safe variant labels
        safe_dto = SystemDesignChallengeRead.model_validate(
            {
                "id": 1,
                "slug": challenge["slug"],
                "title": challenge["title"],
                "category": challenge["category"],
                "difficulty": challenge["difficulty"],
                "prompt_summary": challenge["prompt_summary"],
                "initial_prompt": challenge["initial_prompt"],
                "tags": challenge["tags"],
                "is_builtin": True,
                "is_archived": False,
                "interviewer_brief": brief,
                "created_at": "2026-11-15T00:00:00Z",
            }
        )
        assert len(safe_dto.available_variants) == 3
        dto_json = safe_dto.model_dump_json()
        for secret_key in FORBIDDEN_SECRET_KEYS:
            assert secret_key not in dto_json
        assert "defence_questions" not in dto_json


@pytest.mark.asyncio
async def test_session_read_schema_masks_blind_variant_until_completed(
    db_session: AsyncSession,
):
    """Random-mode sessions hide variant identity until COMPLETED; explicit mode reveals upfront."""
    await seed_system_design_challenges(db_session)
    challenge = (
        await db_session.execute(
            select(SystemDesignChallengeModel).where(
                SystemDesignChallengeModel.slug == "url-shortener"
            )
        )
    ).scalar_one()

    blind_session = SystemDesignSessionModel(
        challenge_id=challenge.id,
        mode="ADAPTIVE",
        stage="REQUIREMENTS",
        status="IN_PROGRESS",
        brief_seed="deadbeef",
        variant_id="enterprise-compliance-linker",
        variant_selection_mode="random",
        session_brief={
            "variant_id": "enterprise-compliance-linker",
            "variant_title": "Enterprise Internal Compliance Linker",
            "focus_summary": "Private SSO links and PostgreSQL YAGNI.",
            "scale_estimates": {"dau": "150,000 employees"},
        },
        requirements_transcript=[],
        requirements_ledger={},
    )
    db_session.add(blind_session)
    await db_session.commit()
    await db_session.refresh(blind_session)
    blind_session.challenge = challenge

    blind_dto = SystemDesignSessionRead.model_validate(blind_session)
    blind_json = blind_dto.model_dump_json()
    assert blind_dto.brief_seed == "deadbeef"
    assert blind_dto.variant_id is None
    assert blind_dto.variant_title is None
    assert blind_dto.variant_focus is None
    assert "session_brief" not in blind_json
    assert "150,000 employees" not in blind_json

    # Explicit selection reveals variant title & focus immediately while keeping brief stripped
    blind_session.variant_selection_mode = "explicit"
    explicit_dto = SystemDesignSessionRead.model_validate(blind_session)
    assert explicit_dto.variant_id == "enterprise-compliance-linker"
    assert explicit_dto.variant_title == "Enterprise Internal Compliance Linker"
    assert explicit_dto.variant_focus == "Private SSO links and PostgreSQL YAGNI."
    assert "150,000 employees" not in explicit_dto.model_dump_json()

    # Completed random session also reveals variant title & focus cleanly
    blind_session.variant_selection_mode = "random"
    blind_session.status = "COMPLETED"
    blind_session.stage = "COMPLETED"
    completed_dto = SystemDesignSessionRead.model_validate(blind_session)
    assert completed_dto.variant_id == "enterprise-compliance-linker"
    assert completed_dto.variant_title == "Enterprise Internal Compliance Linker"
    assert completed_dto.variant_focus == "Private SSO links and PostgreSQL YAGNI."
    assert "150,000 employees" not in completed_dto.model_dump_json()
