from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.prompts import DEFAULT_PROMPTS
from app.main import app
from app.models.applications import ApplicationModel, CompanyModel, JobPostingModel
from app.models.candidate_profile import CandidateCVModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.schemas.applications import (
    ApplicationQuestionItem,
    ApplicationQuestionsResponse,
    ApplicationQuestionsUpdateRequest,
    GenerateApplicationQuestionsRequest,
)
from app.services.evaluation_worker import _execute_application_qa_steps


def test_application_questions_schemas():
    item = ApplicationQuestionItem(
        id="q_123",
        question="Why do you want to work here?",
        word_limit=150,
        answer="I am passionate about infrastructure...",
        status="GENERATED",
        updated_at=datetime.now(UTC),
    )
    assert item.id == "q_123"
    assert item.question == "Why do you want to work here?"
    assert item.word_limit == 150
    assert item.status == "GENERATED"

    gen_req = GenerateApplicationQuestionsRequest(
        questions=[item],
        tone="enthusiastic",
        custom_instructions="Focus on distributed databases.",
    )
    assert len(gen_req.questions) == 1
    assert gen_req.tone == "enthusiastic"

    update_req = ApplicationQuestionsUpdateRequest(questions=[item])
    assert len(update_req.questions) == 1

    resp = ApplicationQuestionsResponse(
        application_id=42,
        questions=[item],
        status="COMPLETED",
    )
    assert resp.application_id == 42
    assert len(resp.questions) == 1
    assert resp.status == "COMPLETED"


def test_application_qa_prompt_template_exists():
    from langchain_core.prompts import ChatPromptTemplate

    assert "application_qa" in DEFAULT_PROMPTS
    template = DEFAULT_PROMPTS["application_qa"]
    assert "{company_name}" in template
    assert "{position}" in template
    assert "{job_description}" in template
    assert "{candidate_cv}" in template
    assert "{questions_json}" in template
    assert "STRICT FACTUAL GROUNDING" in template
    assert "HONEST SKILL GAP HANDLING" in template
    assert "ZERO INVENTIONS" in template

    # Verify LangChain template compiles and formats with zero unexpected variable errors
    prompt_obj = ChatPromptTemplate.from_template(template)
    assert set(prompt_obj.input_variables) == {
        "company_name",
        "position",
        "company_research_context",
        "job_description",
        "candidate_cv",
        "questions_json",
        "tone",
        "custom_instructions",
    }
    formatted = prompt_obj.format(
        company_name="Acme Corp",
        position="Backend Engineer",
        company_research_context="Verified Company Intelligence:\n- Mission: High scale",
        job_description="Build distributed systems",
        candidate_cv="Staff Engineer with 8 years Python experience",
        questions_json='[{"id":"q1","question":"Why Acme?"}]',
        tone="professional",
        custom_instructions="",
    )
    assert "Acme Corp" in formatted
    assert '"id": "<question_id>"' in formatted
    assert "Verified Company Intelligence" in formatted


@pytest.mark.asyncio
async def test_application_questions_endpoints(db_session):
    company = CompanyModel(
        name="Test Company", name_normalized="test company", domain="testco.com"
    )
    db_session.add(company)
    await db_session.flush()

    application = ApplicationModel(
        company_id=company.id,
        position="Senior Distributed Systems Engineer",
        status="APPLIED",
        application_questions=[
            {
                "id": "q_initial",
                "question": "What is your biggest accomplishment?",
                "word_limit": 100,
                "answer": "Scaled settlement engine.",
                "status": "GENERATED",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ],
    )
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. GET questions
        res = await ac.get(f"/api/v1/applications/{application.id}/questions")
        assert res.status_code == 200
        data = res.json()
        assert data["application_id"] == application.id
        assert len(data["questions"]) == 1
        assert (
            data["questions"][0]["question"] == "What is your biggest accomplishment?"
        )

        # 2. PATCH questions (edit answer)
        patch_payload = {
            "questions": [
                {
                    "id": "q_initial",
                    "question": "What is your biggest accomplishment?",
                    "word_limit": 100,
                    "answer": "Manually edited accomplishment text.",
                    "status": "GENERATED",
                },
                {
                    "id": "q_new",
                    "question": "Why leave current role?",
                    "word_limit": 50,
                    "answer": None,
                    "status": "DRAFT",
                },
            ]
        }
        res_patch = await ac.patch(
            f"/api/v1/applications/{application.id}/questions",
            json=patch_payload,
        )
        assert res_patch.status_code == 200
        patch_data = res_patch.json()
        assert len(patch_data["questions"]) == 2
        assert (
            patch_data["questions"][0]["answer"]
            == "Manually edited accomplishment text."
        )
        assert patch_data["questions"][1]["id"] == "q_new"

        # 3. POST generate (queue task)
        gen_payload = {
            "questions": [
                {
                    "id": "q_gen1",
                    "question": "Why do you want to join us?",
                    "word_limit": 150,
                }
            ],
            "tone": "executive",
        }
        res_gen = await ac.post(
            f"/api/v1/applications/{application.id}/questions/generate",
            json=gen_payload,
        )
        assert res_gen.status_code == 202
        gen_data = res_gen.json()
        assert gen_data["status"] == "QUEUED"
        assert len(gen_data["questions"]) == 1
        assert gen_data["questions"][0]["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_execute_application_qa_steps(db_session):
    company = CompanyModel(
        name="CloudCorp", name_normalized="cloudcorp", domain="cloudcorp.io"
    )
    db_session.add(company)
    await db_session.flush()

    cv = CandidateCVModel(
        raw_text="8+ years backend engineer in Python, Go, and Kafka.",
        anonymized_text="Staff engineer specializing in distributed systems and Kafka.",
    )
    db_session.add(cv)

    app_rec = ApplicationModel(
        company_id=company.id,
        position="Distributed Systems Lead",
        status="APPLIED",
        application_questions=[
            {
                "id": "q_test1",
                "question": "What is your experience with Kafka?",
                "word_limit": 100,
                "status": "QUEUED",
            }
        ],
    )
    db_session.add(app_rec)
    await db_session.flush()

    job_posting = JobPostingModel(
        application_id=app_rec.id,
        job_url="https://cloudcorp.io/jobs/lead",
        description_markdown="Looking for an engineer to lead Kafka streaming.",
    )
    db_session.add(job_posting)
    await db_session.commit()
    await db_session.refresh(app_rec)

    task = IntakeEvaluationTaskModel(
        task_type="APPLICATION_QA",
        status="QUEUED",
        stage="QUEUED",
        raw_text=str(app_rec.id),
        result_json={
            "application_id": app_rec.id,
            "company": "CloudCorp",
            "position": "Distributed Systems Lead",
            "questions": [
                {
                    "id": "q_test1",
                    "question": "What is your experience with Kafka?",
                    "word_limit": 100,
                }
            ],
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    mock_answers = [
        {
            "id": "q_test1",
            "question": "What is your experience with Kafka?",
            "word_limit": 100,
            "answer": "Over 8 years scaling distributed stream architectures with Kafka.",
            "status": "GENERATED",
            "updated_at": datetime.now(UTC).isoformat(),
        }
    ]

    with patch(
        "app.services.evaluation_worker.generate_application_answers",
        new=AsyncMock(return_value=mock_answers),
    ):
        await _execute_application_qa_steps(task, db_session)

    await db_session.refresh(task)
    await db_session.refresh(app_rec)

    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert len(app_rec.application_questions) == 1
    assert app_rec.application_questions[0]["answer"] == (
        "Over 8 years scaling distributed stream architectures with Kafka."
    )
    assert app_rec.application_questions[0]["status"] == "GENERATED"


@pytest.mark.asyncio
async def test_application_qa_worker_invokes_company_research(db_session):
    company = CompanyModel(
        name="Apex Systems",
        name_normalized="apex systems",
        domain="apex.io",
        company_research=None,
    )
    db_session.add(company)
    await db_session.flush()

    cv = CandidateCVModel(
        raw_text="Lead Engineer with 10 years experience",
        extracted_skills=["Python", "Kafka"],
    )
    db_session.add(cv)

    app_rec = ApplicationModel(
        company_id=company.id,
        position="Principal Architect",
        status="APPLIED",
        application_questions=[
            {
                "id": "q_comp",
                "question": "Why Apex Systems?",
                "word_limit": 150,
                "status": "QUEUED",
            }
        ],
    )
    db_session.add(app_rec)
    await db_session.flush()

    task = IntakeEvaluationTaskModel(
        task_type="APPLICATION_QA",
        status="QUEUED",
        stage="QUEUED",
        raw_text=str(app_rec.id),
        result_json={
            "application_id": app_rec.id,
            "company": "Apex Systems",
            "position": "Principal Architect",
            "include_company_research": True,
            "questions": [
                {
                    "id": "q_comp",
                    "question": "Why Apex Systems?",
                    "word_limit": 150,
                }
            ],
        },
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    mock_research = {
        "summary": "Building ultra-low-latency financial infrastructure.",
        "engineering_culture": "Distributed systems, Rust and Python.",
        "recent_initiatives": "Launched high-throughput settlement engine.",
    }
    mock_answers = [
        {
            "id": "q_comp",
            "question": "Why Apex Systems?",
            "word_limit": 150,
            "answer": "Apex's ultra-low-latency mission matches my streaming background.",
            "status": "GENERATED",
            "updated_at": datetime.now(UTC).isoformat(),
        }
    ]

    with (
        patch(
            "app.services.company_research.research_company_context",
            new=AsyncMock(return_value=mock_research),
        ) as mock_res_call,
        patch(
            "app.services.evaluation_worker.generate_application_answers",
            new=AsyncMock(return_value=mock_answers),
        ) as mock_qa_call,
    ):
        await _execute_application_qa_steps(task, db_session)

    mock_res_call.assert_awaited_once()
    mock_qa_call.assert_awaited_once()
    qa_kwargs = mock_qa_call.call_args.kwargs
    assert qa_kwargs.get("company_research") == mock_research

    await db_session.refresh(task)
    assert task.status == "COMPLETED"
    assert task.stage == "COMPLETE"
    assert task.result_json.get("company_research") == mock_research
