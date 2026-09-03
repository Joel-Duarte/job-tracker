from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.applications import CompanyModel
from app.services.company_resolver import resolve_or_create_company


@pytest.mark.asyncio
async def test_resolve_or_create_company_exact_match():
    db = AsyncMock()
    existing = CompanyModel(
        id=1, name="Stripe", name_normalized="stripe", domain="stripe.com"
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing
    db.execute.return_value = mock_res

    comp, was_created = await resolve_or_create_company(db, "Stripe", "stripe.com")
    assert was_created is False
    assert comp.id == 1


@pytest.mark.asyncio
async def test_resolve_or_create_company_domain_match():
    db = AsyncMock()
    existing = CompanyModel(
        id=2,
        name="Linear App Inc",
        name_normalized="linear app inc",
        domain="linear.app",
    )

    # 1. Exact name query returns None
    # 2. Domain query returns existing
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None

    mock_res_domain = MagicMock()
    mock_res_domain.scalar_one_or_none.return_value = existing

    db.execute.side_effect = [mock_res_none, mock_res_domain]

    comp, was_created = await resolve_or_create_company(db, "Linear", "linear.app")
    assert was_created is False
    assert comp.id == 2


@pytest.mark.asyncio
async def test_resolve_or_create_company_fuzzy_match():
    db = AsyncMock()
    existing = CompanyModel(
        id=3, name="Datadog", name_normalized="datadog", domain="datadoghq.com"
    )

    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None

    mock_res_all = MagicMock()
    mock_res_all.scalars.return_value.all.return_value = [existing]

    # 1. Exact name query returns None
    # 2. Trigram query raises exception, triggering fallback
    # 3. Fallback all_companies_stmt returns [existing]
    db.execute.side_effect = [
        mock_res_none,
        Exception("No pg_trgm in mock"),
        mock_res_all,
    ]

    comp, was_created = await resolve_or_create_company(db, "Datadogs", None)
    assert was_created is False
    assert comp.id == 3


@pytest.mark.asyncio
async def test_resolve_or_create_company_new():
    db = AsyncMock()
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    mock_res_none.first.return_value = None

    # Tier 1 (name): None
    # Tier 2 (domain): None
    # Tier 3 (trgm): None
    db.execute.side_effect = [mock_res_none, mock_res_none, mock_res_none]

    comp, was_created = await resolve_or_create_company(
        db, "NewStartup Co", "newstartup.io"
    )
    assert was_created is True
    assert comp.name == "NewStartup Co"
    assert comp.domain == "newstartup.io"
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_companies_merge_endpoints_unit():
    # Test merge validation rules with mock db
    db = AsyncMock()
    # Source and target same
    from fastapi import HTTPException

    from app.routers.companies import merge_companies
    from app.schemas.companies import CompanyMergeRequest

    with pytest.raises(HTTPException) as exc_info:
        await merge_companies(
            CompanyMergeRequest(source_company_id=1, target_company_id=1), db=db
        )
    assert exc_info.value.status_code == 400

    # Target inside source_company_ids
    with pytest.raises(HTTPException) as exc_info2:
        await merge_companies(
            CompanyMergeRequest(source_company_ids=[2, 3, 1], target_company_id=1),
            db=db,
        )
    assert exc_info2.value.status_code == 400

    # Successful multi-merge
    c_target = CompanyModel(id=1, name="Acme", domain=None, rating=None)
    c_src1 = CompanyModel(
        id=2, name="Acme Corp", domain="acme.com", rating=4, notes="Note 1"
    )
    c_src2 = CompanyModel(id=3, name="Acme LLC", domain=None, rating=5, notes=None)

    async def mock_get(model, pk):
        if pk == 1:
            return c_target
        elif pk == 2:
            return c_src1
        elif pk == 3:
            return c_src2
        return None

    db.get.side_effect = mock_get

    res = await merge_companies(
        CompanyMergeRequest(source_company_ids=[2, 3], target_company_id=1), db=db
    )
    assert res["status"] == "merged"
    assert res["target_company_id"] == 1
    assert len(res["source_company_ids"]) == 2
    assert c_target.domain == "acme.com"
    assert c_target.rating == 4
    assert c_target.notes == "Note 1"
    assert db.delete.call_count == 2


@pytest.mark.asyncio
async def test_bulk_research_companies_unit():
    from fastapi import BackgroundTasks

    from app.routers.companies import bulk_research_companies

    db = AsyncMock()
    c1 = CompanyModel(id=1, name="Airbnb", domain="airbnb.com", company_research=None)
    c2 = CompanyModel(id=2, name="Linear", domain="linear.app", company_research={})

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [c1, c2]
    db.execute.return_value = mock_res

    bg = MagicMock(spec=BackgroundTasks)
    res = await bulk_research_companies(background_tasks=bg, payload=None, db=db)
    assert res["status"] == "enqueued"
    assert res["enqueued_count"] == 2
    assert len(res["task_ids"]) == 2
    assert bg.add_task.call_count == 2


@pytest.mark.asyncio
async def test_execute_company_research_steps_unit():
    from unittest.mock import patch

    from app.models.intake_tasks import IntakeEvaluationTaskModel
    from app.services.evaluation_worker import _execute_company_research_steps

    db = AsyncMock()
    task = IntakeEvaluationTaskModel(
        id=99,
        task_type="COMPANY_RESEARCH",
        title_hint="Linear",
        job_url="linear.app",
        raw_text="1",
        status="QUEUED",
        stage="QUEUED",
        result_json={"company_id": 1, "company_name": "Linear", "domain": "linear.app"},
    )

    fake_result = {
        "summary": "Issue tracking for software teams.",
        "engineering_culture": "Fast keyboards.",
        "recent_initiatives": "Linear Insights",
        "public_rating_snippet": "4.9 on Glassdoor",
        "sources": ["https://linear.app"],
        "researched_at": "2026-09-02T12:00:00Z",
    }

    with patch(
        "app.services.company_research.research_company_context",
        new_callable=AsyncMock,
        return_value=fake_result,
    ):
        await _execute_company_research_steps(task, db)

    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETED"
    assert task.result_json["summary"] == "Issue tracking for software teams."


@pytest.mark.asyncio
async def test_get_company_includes_assessment_applications():
    from app.models.applications import ApplicationModel
    from app.routers.companies import get_company

    db = AsyncMock()
    app_assessment = ApplicationModel(
        id=1, position="Assessment Only", status="ASSESSMENT"
    )
    app_applied = ApplicationModel(id=2, position="Senior Engineer", status="APPLIED")
    company = CompanyModel(
        id=1,
        name="Linear",
        name_normalized="linear",
        domain="linear.app",
        applications=[app_assessment, app_applied],
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = company
    db.execute.return_value = mock_res

    res = await get_company(company_id=1, db=db)
    assert res.applications_count == 2
    assert len(res.applications) == 2
    assert {application.id for application in res.applications} == {1, 2}


@pytest.mark.asyncio
async def test_get_potential_duplicates():
    from app.routers.companies import get_potential_duplicates

    db = AsyncMock()
    c1 = CompanyModel(
        id=1, name="Stripe", name_normalized="stripe", domain="stripe.com"
    )
    c2 = CompanyModel(
        id=2, name="Stripe Inc", name_normalized="stripe inc", domain="stripe.com"
    )
    c3 = CompanyModel(
        id=3, name="Linear", name_normalized="linear", domain="linear.app"
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [c1, c2, c3]
    db.execute.return_value = mock_res

    data = await get_potential_duplicates(db=db)
    assert data["total_clusters"] == 1
    assert data["total_duplicate_companies"] == 2
    assert 1 in data["duplicate_company_ids"]
    assert 2 in data["duplicate_company_ids"]


@pytest.mark.asyncio
async def test_update_company_auto_merges_when_renamed():
    from app.routers.companies import update_company
    from app.schemas.companies import CompanyUpdate

    db = AsyncMock()
    c_existing = CompanyModel(id=1, name="CSSF", name_normalized="cssf", domain=None)
    c_renamed = CompanyModel(
        id=2, name="Dellent", name_normalized="dellent", domain="cssf.lu"
    )

    db.get.return_value = c_renamed

    # When query executed for existing company with name_normalized == 'cssf'
    mock_target = MagicMock()
    mock_target.scalars.return_value.first.return_value = c_existing

    mock_final = MagicMock()
    mock_final.scalar_one_or_none.return_value = c_existing

    db.execute.side_effect = [mock_target, None, mock_final]

    payload = CompanyUpdate(name="CSSF")
    res = await update_company(company_id=2, payload=payload, db=db)

    assert res.id == 1
    assert res.name == "CSSF"
    assert c_existing.domain == "cssf.lu"
    db.delete.assert_awaited_once_with(c_renamed)


@pytest.mark.asyncio
async def test_bulk_research_companies_mode_and_duplicate_prevention():
    from fastapi import BackgroundTasks

    from app.routers.companies import bulk_research_companies

    db = AsyncMock()
    bg = BackgroundTasks()

    c1 = CompanyModel(id=1, name="Company 1", domain="c1.com", company_research=None)
    c2 = CompanyModel(
        id=2,
        name="Company 2",
        domain="c2.com",
        company_research={"summary": "Has summary already"},
    )
    c3 = CompanyModel(id=3, name="Company 3", domain="c3.com", company_research={})

    mock_companies = MagicMock()
    mock_companies.scalars.return_value.all.return_value = [c1, c2, c3]

    # Active tasks: company 3 is already active (raw_text = '3')
    mock_active = MagicMock()
    mock_active.scalars.return_value.all.return_value = ["3"]

    db.execute.side_effect = [mock_companies, mock_active]

    # 1. Run in default mode="missing"
    # c2 has summary -> excluded by mode
    # c1 and c3 lack summary -> candidates
    # c3 is already active -> skipped
    # Only c1 is enqueued!
    res = await bulk_research_companies(
        background_tasks=bg, payload={"mode": "missing"}, db=db
    )
    assert res["status"] == "enqueued"
    assert res["enqueued_count"] == 1
    assert res["skipped_count"] == 1  # c3 skipped as duplicate
