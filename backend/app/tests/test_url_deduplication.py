import pytest

from app.models.applications import ApplicationModel
from app.schemas.llm import JobAssessmentResult
from app.services.job_saver import persist_or_stage_job_assessment


@pytest.mark.asyncio
async def test_persist_job_assessment_unrestricted_urls(db_session):
    """Test that submitting the same job posting URL with different referral parameters creates fresh, independent entries with normalized URLs."""
    first_assessment = JobAssessmentResult(
        company="Stripe",
        position="Senior Software Engineer",
        fit_score=85,
        summary="Great fit for senior role.",
        matching_skills=["Python", "FastAPI"],
        missing_skills=["Go"],
    )

    url_1 = "https://stripe.com/jobs/senior-dev?utm_source=linkedin&ref=friend1&source=campaignA"
    res1 = await persist_or_stage_job_assessment(
        db=db_session,
        assessment=first_assessment,
        raw_text="Job description text for senior dev",
        job_url=url_1,
    )

    assert res1["status"] == "success"
    assert res1["is_duplicate"] is False
    app_id_1 = res1["application_id"]

    # Verify stored application job_url is clean and normalized
    app_record_1 = await db_session.get(ApplicationModel, app_id_1)
    assert app_record_1.job_url == "https://stripe.com/jobs/senior-dev"

    # Submit second job assessment for the same job with DIFFERENT referral params
    second_assessment = JobAssessmentResult(
        company="Stripe",
        position="Senior Software Engineer",
        fit_score=85,
        summary="Re-submission from Twitter referral.",
        matching_skills=["Python"],
    )

    url_2 = "https://stripe.com/jobs/senior-dev?utm_source=twitter&ref=colleague2&fbclid=123456"
    res2 = await persist_or_stage_job_assessment(
        db=db_session,
        assessment=second_assessment,
        raw_text="Job description text for senior dev",
        job_url=url_2,
    )

    assert res2["status"] == "success"
    assert res2["is_duplicate"] is False
    assert res2["route"] == "commit"
    app_id_2 = res2["application_id"]
    assert app_id_2 != app_id_1

    # Verify second stored application job_url is also clean and normalized
    app_record_2 = await db_session.get(ApplicationModel, app_id_2)
    assert app_record_2.job_url == "https://stripe.com/jobs/senior-dev"
