from unittest.mock import AsyncMock, patch

import pytest
from app.core.database import get_db
from app.main import app
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
)
from app.schemas.intake import ExtractedEmailInfo
from app.schemas.llm import JobAssessmentResult
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_extension_clip_job_direct(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    with patch(
        "app.routers.extension.generate_and_save_application_embedding",
        new_callable=AsyncMock,
    ) as mock_emb:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/extension/clip-job",
                json={
                    "company": "Anthropic",
                    "position": "AI Research Engineer",
                    "url": "https://anthropic.com/careers/123",
                    "description": "Looking for AI engineers to build next-gen models.",
                    "status": "APPLIED",
                    "location": "San Francisco, CA",
                    "salary": "$250k - $350k",
                },
            )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["company"] == "Anthropic"
        assert data["position"] == "AI Research Engineer"
        assert data["application_id"] is not None

        # Verify DB records
        comp_res = await db_session.execute(
            select(CompanyModel).where(CompanyModel.name_normalized == "anthropic")
        )
        company = comp_res.scalar_one_or_none()
        assert company is not None

        app_res = await db_session.execute(
            select(ApplicationModel).where(
                ApplicationModel.id == data["application_id"]
            )
        )
        application = app_res.scalar_one_or_none()
        assert application is not None
        assert application.job_url == "https://anthropic.com/careers/123"

        event_res = await db_session.execute(
            select(ApplicationEventModel).where(
                ApplicationEventModel.email_application_id == application.id
            )
        )
        event = event_res.scalar_one_or_none()
        assert event is not None
        assert event.email_event_type == "BROWSER_EXTENSION_CLIP"

        mock_emb.assert_called_once_with(db_session, application.id)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_extension_clip_url_pipeline(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    mock_extracted = ExtractedEmailInfo(
        company="Snowflake",
        position="Principal Database Architect",
        email_type="JOB_APPLICATION",
        event_type="APPLICATION_SUBMITTED",
        status="APPLIED",
        summary="Clipped Snowflake job posting.",
        action_required=False,
        action=None,
    )

    with (
        patch(
            "app.services.intake.extract_email_info", new_callable=AsyncMock
        ) as mock_extract,
        patch(
            "app.services.graph_nodes.generate_and_save_application_embedding",
            new_callable=AsyncMock,
        ),
    ):
        mock_extract.return_value = mock_extracted

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/extension/clip-url",
                json={
                    "url": "https://careers.snowflake.com/jobs/999",
                    "raw_html": "<html><body><h1>Principal Database Architect</h1><p>Snowflake is hiring...</p></body></html>",
                },
            )

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["company"] == "Snowflake"
        assert data["position"] == "Principal Database Architect"
        assert data["application_id"] is not None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_extension_intake_url_and_jd_routes(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session

    mock_assessment = JobAssessmentResult(
        company="Datadog",
        position="Senior Systems Engineer",
        fit_score=88,
        programmatic_match_score=80,
        matching_skills=["Python", "Go", "Docker"],
        missing_skills=[],
        pros=["Great tech stack"],
        cons=[],
        salary_min=170000,
        salary_max=220000,
        currency="USD",
        location="Remote",
        work_model="Remote",
        recommendation="APPLY_STRONGLY",
        summary="Strong profile match for distributed systems.",
    )

    with patch(
        "app.routers.intake.assess_job_posting", new_callable=AsyncMock
    ) as mock_assess:
        mock_assess.return_value = mock_assessment

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Test POST /api/v1/intake/url (from extension send-url-btn)
            url_res = await ac.post(
                "/api/v1/intake/url",
                json={
                    "type": "URL_DIRECT_SEND",
                    "url": "https://boards.greenhouse.io/datadog/jobs/123",
                    "title": "Datadog - Senior Systems Engineer",
                },
            )
            assert url_res.status_code == 200
            assert url_res.json()["company"] == "Datadog"
            assert url_res.json()["fit_score"] == 88

            # 2. Test POST /api/v1/intake/jd (from extension elements selection send-btn)
            jd_res = await ac.post(
                "/api/v1/intake/jd",
                json={
                    "id": "card-1",
                    "type": "group",
                    "title": "Job Requirements",
                    "children": [
                        {
                            "id": "elem-1",
                            "type": "card",
                            "text": "Datadog is seeking Senior Systems Engineers with Python and Go experience.",
                        }
                    ],
                },
            )
            assert jd_res.status_code == 200
            assert jd_res.json()["company"] == "Datadog"
            assert jd_res.json()["recommendation"] == "APPLY_STRONGLY"

    app.dependency_overrides.clear()
