"""Deterministic CI regression tests for company extraction guardrails,
company deduplication across domains, and interview stage progression.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.schemas.llm import EmailMatchTiebreakerResult, JobAssessmentResult
from app.services.company_resolver import resolve_or_create_company
from app.services.domain_resolver import (
    extract_domain_from_url,
    is_invalid_company_name,
)
from app.services.graph_nodes import db_commit_node, fuzzy_match_node
from app.services.job_saver import persist_or_stage_job_assessment


def _make_assessment(**overrides) -> JobAssessmentResult:
    base = dict(
        company="Technical Bar",
        position="Senior AI Engineer",
        fit_score=80,
        recommendation="APPLY_STRONGLY",
        matching_skills=["Python", "FastAPI"],
        missing_skills=[],
        pros=["Strong Python match"],
        cons=[],
        match_summary="Solid match.",
        summary="Solid match.",
    )
    base.update(overrides)
    return JobAssessmentResult(**base)


def test_invalid_company_name_and_subdomain_extraction():
    for bad in (
        "Technical Bar",
        "Technical Bar Raiser",
        "Hybrid",
        "Remote",
        "On-site",
        "Not Specified",
        "",
    ):
        assert is_invalid_company_name(bad) is True

    for good in ("Hays", "NovaTech", "Stripe", "Linear"):
        assert is_invalid_company_name(good) is False

    # Multi-part SLD (hays.co.uk) must not strip 'hays', while uk.hays.com strips 'uk.'
    assert (
        extract_domain_from_url("https://www.hays.co.uk/jobs/123", "Hays")
        == "hays.co.uk"
    )
    assert extract_domain_from_url("https://uk.hays.com/jobs/123", "Hays") == "hays.com"
    assert (
        extract_domain_from_url("https://talent.novatech.io/role/1", "NovaTech")
        == "novatech.io"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("leaked_company", ["Technical Bar", "Hybrid"])
async def test_job_saver_prefers_structured_spec_over_leaked_assessment_company(
    db_session: AsyncSession, leaked_company: str
):
    assessment = _make_assessment(company=leaked_company)
    structured_spec = {
        "company": "Hays",
        "position": "Senior AI Engineer",
        "extracted_skills": ["Python", "FastAPI"],
    }

    with patch(
        "app.services.domain_resolver.resolve_company_domain_and_about",
        new_callable=AsyncMock,
        return_value=("hays.com", None),
    ):
        res = await persist_or_stage_job_assessment(
            db=db_session,
            assessment=assessment,
            raw_text="Hays hiring Senior AI Engineer (Hybrid)",
            job_url="https://www.hays.com/jobs/12345",
            structured_spec=structured_spec,
        )

    app_row = await db_session.get(ApplicationModel, res["application_id"])
    assert app_row is not None
    comp = await db_session.get(CompanyModel, app_row.company_id)
    assert comp is not None
    assert comp.name == "Hays"


@pytest.mark.asyncio
async def test_job_saver_never_persists_leaked_company_when_spec_missing(
    db_session: AsyncSession,
):
    assessment = _make_assessment(company="Hybrid")
    with patch(
        "app.services.domain_resolver.resolve_company_domain_and_about",
        new_callable=AsyncMock,
        return_value=(None, None),
    ):
        res = await persist_or_stage_job_assessment(
            db=db_session,
            assessment=assessment,
            raw_text="Hybrid role",
            job_url="https://boards.greenhouse.io/novatech/jobs/999",
            structured_spec=None,
        )

    app_row = await db_session.get(ApplicationModel, res["application_id"])
    comp = await db_session.get(CompanyModel, app_row.company_id)
    assert comp is not None
    assert comp.name == "Novatech"


@pytest.mark.asyncio
async def test_company_resolver_deduplicates_regional_domains_and_variants(
    db_session: AsyncSession,
):
    c1, created1 = await resolve_or_create_company(db_session, "Hays", "hays.com")
    assert created1 is True

    # Different regional TLD + division suffix should resolve to same CompanyModel
    c2, created2 = await resolve_or_create_company(db_session, "Hays UK", "hays.co.uk")
    assert created2 is False
    assert c2.id == c1.id

    # Legal suffix variant should match Tier 1 after cleaning
    c3, created3 = await resolve_or_create_company(db_session, "Hays plc", None)
    assert created3 is False
    assert c3.id == c1.id

    # Distinct companies sharing a prefix must NOT be merged
    m1, m_created1 = await resolve_or_create_company(db_session, "Meta", "meta.com")
    m2, m_created2 = await resolve_or_create_company(
        db_session, "MetLife", "metlife.com"
    )
    assert m_created1 is True
    assert m_created2 is True
    assert m1.id != m2.id


@pytest.mark.asyncio
async def test_fuzzy_match_allows_abbreviated_role_on_same_thread(
    db_session: AsyncSession,
):
    comp = CompanyModel(
        name="NovaTech", name_normalized="novatech", domain="novatech.io"
    )
    db_session.add(comp)
    await db_session.flush()

    app = ApplicationModel(
        company_id=comp.id,
        position="Senior IA Software Engineer",
        position_normalized="senior ia software engineer",
        status="APPLIED",
    )
    db_session.add(app)
    await db_session.flush()

    ev = ApplicationEventModel(
        email_application_id=app.id,
        email_conversation_id="conv-novatech-1",
        email_message_id="msg-novatech-1",
        email_event_type="APPLICATION_RECEIVED",
        email_status_after_event="APPLIED",
        email_subject="Application Received",
        email_received_at=datetime.now(UTC),
    )
    db_session.add(ev)
    await db_session.commit()

    config = {"configurable": {"db": db_session}}

    # Abbreviated role on same thread must commit, not stage as THREAD_IDENTITY_CONFLICT
    same_role = await fuzzy_match_node(
        {
            "conversation_id": "conv-novatech-1",
            "position_name": "Software Engineer AI",
            "company_name": "NovaTech",
        },
        config,
    )
    assert same_role["route"] == "commit"
    assert same_role["application_id"] == app.id

    # Unrelated role on same thread must still trigger THREAD_IDENTITY_CONFLICT
    unrelated = await fuzzy_match_node(
        {
            "conversation_id": "conv-novatech-1",
            "position_name": "Product Manager",
            "company_name": "NovaTech",
        },
        config,
    )
    assert unrelated["route"] == "staging"
    assert unrelated["match_reason"] == "THREAD_IDENTITY_CONFLICT"


@pytest.mark.asyncio
async def test_calendar_invite_advances_applied_to_technical_interview(
    db_session: AsyncSession,
):
    comp = CompanyModel(
        name="NovaTech", name_normalized="novatech", domain="novatech.io"
    )
    db_session.add(comp)
    await db_session.flush()

    app = ApplicationModel(
        company_id=comp.id,
        position="Senior AI Software Engineer",
        position_normalized="senior ai software engineer",
        status="APPLIED",
    )
    db_session.add(app)
    await db_session.commit()

    config = {"configurable": {"db": db_session}}
    res = await db_commit_node(
        {
            "is_application": True,
            "company_id": comp.id,
            "company_name": "NovaTech",
            "application_id": app.id,
            "position_name": "Senior AI Software Engineer",
            "message_id": "msg-cal-confirm-1",
            "conversation_id": "conv-cal-1",
            "sender": "recruiter@novatech.io",
            "subject": "SE AI - Alex",
            "received_at": "2026-11-16T13:58:16Z",
            "body": "Microsoft Teams invite",
            "calendar_events": [
                {
                    "uid": "uid-123",
                    "organizer": "recruiter@novatech.io",
                    "method": "REQUEST",
                    "sequence": 0,
                    "start": "2026-11-17T11:00:00Z",
                    "stamp": "2026-11-16T13:58:16Z",
                }
            ],
            "extracted_data": {
                "email_type": "JOB_APPLICATION",
                "summary": "Interview scheduled via Teams.",
                "temporal": {"version": 2, "timezone": "UTC"},
            },
        },
        config,
    )

    assert res["application_id"] == app.id
    await db_session.refresh(app)
    assert app.status == "TECHNICAL_INTERVIEW"

    ev = (
        await db_session.execute(
            select(ApplicationEventModel).where(
                ApplicationEventModel.id == res["event_id"]
            )
        )
    ).scalar_one()
    assert ev.email_event_type == "INTERVIEW_SCHEDULED"
    assert ev.email_status_after_event == "TECHNICAL_INTERVIEW"


@pytest.mark.asyncio
async def test_tiebreaker_commits_alias_and_excludes_rejected_includes_archived(
    db_session: AsyncSession,
):
    c_google = CompanyModel(
        name="Google", name_normalized="google", domain="google.com"
    )
    c_ghost = CompanyModel(
        name="GhostCorp", name_normalized="ghostcorp", domain="ghost.io"
    )
    c_rej = CompanyModel(
        name="RejectCorp", name_normalized="rejectcorp", domain="rej.io"
    )
    db_session.add_all([c_google, c_ghost, c_rej])
    await db_session.flush()

    app_google = ApplicationModel(
        company_id=c_google.id,
        position="Staff Distributed Systems Engineer",
        position_normalized="staff distributed systems engineer",
        status="APPLIED",
    )
    app_ghost = ApplicationModel(
        company_id=c_ghost.id,
        position="Platform Engineer",
        position_normalized="platform engineer",
        status="ARCHIVED",
    )
    app_rej = ApplicationModel(
        company_id=c_rej.id,
        position="Backend Engineer",
        position_normalized="backend engineer",
        status="REJECTED",
    )
    db_session.add_all([app_google, app_ghost, app_rej])
    await db_session.commit()

    captured_candidates = []

    async def fake_tiebreaker(db, **kwargs):
        captured_candidates.extend(kwargs["candidates"])
        return EmailMatchTiebreakerResult(
            matched_application_id=app_google.id,
            confidence=0.92,
            reason="Alphabet Recruiting is Google's parent recruiting brand.",
        )

    config = {"configurable": {"db": db_session}}
    with patch(
        "app.services.llm.resolve_email_match_tiebreaker",
        side_effect=fake_tiebreaker,
    ):
        res = await fuzzy_match_node(
            {
                "conversation_id": "conv-alphabet-1",
                "sender": "recruiting@alphabet-careers.invalid",
                "subject": "Next steps for Staff Systems Engineer",
                "company_name": "Alphabet Recruiting",
                "position_name": "Staff Systems Engineer",
                "extracted_data": {
                    "status": "TECHNICAL_INTERVIEW",
                    "summary": "Teams screen",
                },
            },
            config,
        )

    cand_ids = {c["application_id"] for c in captured_candidates}
    assert app_google.id in cand_ids
    assert app_ghost.id in cand_ids
    assert app_rej.id not in cand_ids
    assert res["route"] == "commit"
    assert res["application_id"] == app_google.id


@pytest.mark.asyncio
async def test_tiebreaker_resolves_multiple_active_roles_and_falls_back_on_low_confidence(
    db_session: AsyncSession,
):
    comp = CompanyModel(
        name="Orbital Cloud", name_normalized="orbital cloud", domain="orbital.io"
    )
    db_session.add(comp)
    await db_session.flush()

    app_be = ApplicationModel(
        company_id=comp.id,
        position="Senior Backend & AI Engineer",
        position_normalized="senior backend & ai engineer",
        status="APPLIED",
    )
    app_fe = ApplicationModel(
        company_id=comp.id,
        position="Senior Frontend Engineer",
        position_normalized="senior frontend engineer",
        status="APPLIED",
    )
    db_session.add_all([app_be, app_fe])
    await db_session.commit()

    config = {"configurable": {"db": db_session}}
    state = {
        "conversation_id": "conv-orbital-multi",
        "sender": "talent@orbital.io",
        "subject": "Chat with Kubernetes infra team",
        "company_name": "Orbital Cloud",
        "position_name": "Software Engineer",
        "extracted_data": {
            "status": "PHONE_SCREEN",
            "summary": "Kubernetes infra chat",
        },
    }

    with patch(
        "app.services.llm.resolve_email_match_tiebreaker",
        new_callable=AsyncMock,
        return_value=EmailMatchTiebreakerResult(
            matched_application_id=app_be.id, confidence=0.90, reason="Infra team match"
        ),
    ):
        ok_res = await fuzzy_match_node(state, config)
    assert ok_res["route"] == "commit"
    assert ok_res["application_id"] == app_be.id

    with patch(
        "app.services.llm.resolve_email_match_tiebreaker",
        new_callable=AsyncMock,
        return_value=EmailMatchTiebreakerResult(
            matched_application_id=app_be.id, confidence=0.60, reason="Uncertain"
        ),
    ):
        low_res = await fuzzy_match_node(state, config)
    assert low_res["route"] == "staging"
    assert low_res["match_reason"] == "AMBIGUOUS_MULTIPLE_APPLICATIONS"

    with patch(
        "app.services.llm.resolve_email_match_tiebreaker",
        new_callable=AsyncMock,
        return_value=EmailMatchTiebreakerResult(
            matched_application_id=999999, confidence=0.99, reason="Hallucinated ID"
        ),
    ):
        bad_id_res = await fuzzy_match_node(state, config)
    assert bad_id_res["route"] == "staging"
    assert bad_id_res["match_reason"] == "AMBIGUOUS_MULTIPLE_APPLICATIONS"
