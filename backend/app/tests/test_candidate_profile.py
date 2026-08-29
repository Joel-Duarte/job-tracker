from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.schemas.candidate_profile import CVAnonymizationResult
from app.services.matcher import compute_programmatic_skill_match


def test_programmatic_skill_matcher_aliases_and_ratios():
    candidate_skills = [
        "Python",
        "PostgreSQL",
        "Kubernetes",
        "Docker",
        "FastAPI",
        "Kafka",
    ]
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

    from app.schemas.candidate_profile import DomainExperienceItem

    mock_anonymized = CVAnonymizationResult(
        anonymized_resume=(
            "Staff Engineer at [Fintech Enterprise] (4 years)\n"
            "Built distributed billing pipelines using Python, FastAPI, PostgreSQL, and AWS."
        ),
        extracted_skills=[
            "Python",
            "FastAPI",
            "PostgreSQL",
            "AWS",
            "Distributed Systems",
        ],
        total_years_experience=6.0,
        domain_expertise=["Fintech", "Distributed Systems"],
        domain_breakdown=[
            DomainExperienceItem(
                domain="Distributed Systems", years=5.0, is_active=True
            ),
            DomainExperienceItem(domain="Fintech", years=3.5, is_active=True),
        ],
        core_competencies=["Distributed Billing Pipelines", "High-Throughput APIs"],
        spoken_languages=[
            {"language": "English", "proficiency": "Native"},
            {"language": "Spanish", "proficiency": "B2"},
        ],
        summary="Experienced Staff Engineer with fintech and distributed systems expertise.",
    )

    with patch(
        "app.services.evaluation_worker.anonymize_and_parse_cv", new_callable=AsyncMock
    ) as mock_anonymize:
        mock_anonymize.return_value = mock_anonymized

        app.dependency_overrides[get_db] = lambda: db_session
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Enqueue CV Task
            resp = await client.post("/api/v1/profile/cv", json={"raw_text": raw_cv})
            assert resp.status_code == 202
            data = resp.json()
            task_id = data["task_id"]
            assert data["status"] in ["QUEUED", "PROCESSING"]

            # Process task in test session
            from app.services.evaluation_worker import process_evaluation_task

            await process_evaluation_task(task_id, db=db_session)

            # 2. Check Task Status
            task_resp = await client.get(f"/api/v1/profile/cv/tasks/{task_id}")
            assert task_resp.status_code == 200
            task_data = task_resp.json()
            assert task_data["status"] == "COMPLETED"
            assert task_data["stage"] == "COMPLETE"

            # 3. Get Active CV Profile
            get_resp = await client.get("/api/v1/profile/cv")
            assert get_resp.status_code == 200
            active_data = get_resp.json()
            assert active_data is not None
            assert "Python" in active_data["extracted_skills"]
            assert active_data["years_of_experience"] == 6.0
            assert len(active_data["domain_experience"]) == 2
            assert (
                active_data["domain_experience"][0]["domain"] == "Distributed Systems"
            )
            assert active_data["domain_experience"][0]["years"] == 5.0
            assert active_data["domain_experience"][0]["is_active"] is True
            assert "[Fintech Enterprise]" in active_data["anonymized_text"]
            assert active_data["core_competencies"] == [
                "Distributed Billing Pipelines",
                "High-Throughput APIs",
            ]
            assert len(active_data["spoken_languages"]) == 2
            assert active_data["spoken_languages"][0]["language"] == "English"
            assert active_data["spoken_languages"][0]["proficiency"] == "Native"

            # 4. Patch CV (years_of_experience, domain_experience, spoken_languages)
            patch_resp = await client.patch(
                f"/api/v1/profile/cv/{active_data['id']}",
                json={
                    "years_of_experience": 7.0,
                    "anonymized_text": "Updated Custom Sanitized CV",
                    "core_competencies": ["Distributed Systems", "Cloud Architecture"],
                    "spoken_languages": [
                        {"language": "English", "proficiency": "Native"},
                        {"language": "German", "proficiency": "C1"},
                    ],
                    "domain_experience": [
                        {
                            "domain": "Distributed Systems",
                            "years": 5.5,
                            "is_active": True,
                        },
                        {"domain": "Fintech", "years": 3.5, "is_active": False},
                        {"domain": "Cloud & DevOps", "years": 2.0, "is_active": True},
                    ],
                },
            )
            assert patch_resp.status_code == 200
            patched_data = patch_resp.json()
            assert patched_data["years_of_experience"] == 7.0
            assert len(patched_data["domain_experience"]) == 3
            assert patched_data["domain_experience"][1]["is_active"] is False
            assert "Cloud & DevOps" in patched_data["domain_expertise"]
            assert len(patched_data["spoken_languages"]) == 2
            assert patched_data["spoken_languages"][1]["language"] == "German"
            assert patched_data["spoken_languages"][1]["proficiency"] == "C1"

            # 5. Delete CV
            del_resp = await client.delete(f"/api/v1/profile/cv/{active_data['id']}")
            assert del_resp.status_code == 204

            # 6. Verify Active CV is None
            get_after_del = await client.get("/api/v1/profile/cv")
            assert get_after_del.status_code == 200
            assert get_after_del.json() is None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_parse_cv_document_file_endpoint():
    import io

    import docx

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test .txt file upload
        txt_content = (
            b"John Candidate - Full Stack Engineer with Vue and Python experience."
        )
        resp_txt = await client.post(
            "/api/v1/profile/cv/parse-file",
            files={"file": ("resume.txt", txt_content, "text/plain")},
        )
        assert resp_txt.status_code == 200
        data_txt = resp_txt.json()
        assert "John Candidate" in data_txt["text"]
        assert data_txt["filename"] == "resume.txt"

        # 2. Test .docx file upload
        doc = docx.Document()
        doc.add_paragraph("Jane Developer - Lead Software Architect")
        doc.add_paragraph("Expert in FastAPI, Vue, and PostgreSQL")
        docx_buf = io.BytesIO()
        doc.save(docx_buf)

        resp_docx = await client.post(
            "/api/v1/profile/cv/parse-file",
            files={
                "file": (
                    "jane_cv.docx",
                    docx_buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert resp_docx.status_code == 200
        data_docx = resp_docx.json()
        assert "Jane Developer" in data_docx["text"]
        assert "FastAPI, Vue, and PostgreSQL" in data_docx["text"]

        # 3. Test empty file upload validation
        resp_empty = await client.post(
            "/api/v1/profile/cv/parse-file",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp_empty.status_code == 400
        assert "Uploaded file is empty" in resp_empty.json()["detail"]


def test_spoken_language_match_models_and_schemas():
    from app.schemas.llm import (
        ExtractedJobSpec,
        JobAssessmentResult,
        LanguageMatchResult,
        SpokenLanguageRequirement,
    )

    spec = ExtractedJobSpec(
        position="Senior Backend Engineer",
        company="Tech Corp",
        detected_language="German",
        required_spoken_languages=[
            SpokenLanguageRequirement(
                language="German", requirement="mandatory", proficiency="Fluent / C1"
            )
        ],
    )
    assert spec.detected_language == "German"
    assert len(spec.required_spoken_languages) == 1
    assert spec.required_spoken_languages[0].requirement == "mandatory"

    assessment = JobAssessmentResult(
        position="Senior Backend Engineer",
        company="Tech Corp",
        fit_score=92,
        language_match=LanguageMatchResult(
            is_matched=False,
            detected_jd_language="German",
            required_languages=[
                SpokenLanguageRequirement(
                    language="German",
                    requirement="mandatory",
                    proficiency="Fluent / C1",
                )
            ],
            missing_mandatory=["German"],
            missing_preferred=[],
            warning="Role requires Fluent / C1 German (job posting written in German), which is not listed in your profile.",
        ),
    )
    assert assessment.fit_score == 92
    assert assessment.language_match is not None
    assert assessment.language_match.is_matched is False
    assert "German" in assessment.language_match.missing_mandatory
    assert "German" in assessment.language_match.warning
