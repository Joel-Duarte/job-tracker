import pytest
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.main import app
from app.schemas.candidate_profile import CVAnonymizationResult
from app.services.matcher import compute_programmatic_skill_match


def test_programmatic_skill_matcher_aliases_and_ratios():
    candidate_skills = ["Python", "PostgreSQL", "Kubernetes", "Docker", "FastAPI", "Kafka"]
    jd_text = (
        "We are looking for a Senior Engineer with deep knowledge of Python, Postgres, "
        "and k8s container orchestration. Must build high-throughput FastAPI backend services "
        "and distributed Kafka event streaming pipelines. Experience with Docker is a plus."
    )

    result = compute_programmatic_skill_match(candidate_skills, jd_text)
    assert result["candidate_total_skills"] == 6
    assert result["programmatic_score"] >= 80
    assert "Python" in result["matching_skills"]
    assert "PostgreSQL" in result["matching_skills"]
    assert "Kubernetes" in result["matching_skills"]
    assert "Docker" in result["matching_skills"]
    assert "FastAPI" in result["matching_skills"]
    assert "Kafka" in result["matching_skills"]


@pytest.mark.asyncio
async def test_candidate_profile_crud_and_anonymization(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    raw_cv = (
        "John Doe, 123 Main St, San Francisco CA\n"
        "Staff Engineer at Stripe (2018-2022)\n"
        "Built distributed billing pipelines using Python, FastAPI, PostgreSQL, and AWS."
    )

    mock_anonymized = CVAnonymizationResult(
        anonymized_resume=(
            "Staff Engineer at [Fintech Enterprise] (4 years)\n"
            "Built distributed billing pipelines using Python, FastAPI, PostgreSQL, and AWS."
        ),
        extracted_skills=["Python", "FastAPI", "PostgreSQL", "AWS", "Distributed Systems"],
        total_years_experience=6.0,
        domain_expertise=["Fintech", "Distributed Systems"],
        summary="Experienced Staff Engineer with fintech and distributed systems expertise.",
    )

    with patch("app.routers.candidate_profile.anonymize_and_parse_cv", new_callable=AsyncMock) as mock_anonymize:
        mock_anonymize.return_value = mock_anonymized

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Save CV
            resp = await client.post("/api/v1/profile/cv", json={"raw_text": raw_cv})
            assert resp.status_code == 201
            data = resp.json()
            assert data["is_active"] is True
            assert "Python" in data["extracted_skills"]
            assert data["years_of_experience"] == 6.0
            assert "[Fintech Enterprise]" in data["anonymized_text"]

            # 2. Get Active CV
            get_resp = await client.get("/api/v1/profile/cv")
            assert get_resp.status_code == 200
            active_data = get_resp.json()
            assert active_data["id"] == data["id"]
            assert active_data["extracted_skills"] == data["extracted_skills"]

    app.dependency_overrides.clear()

