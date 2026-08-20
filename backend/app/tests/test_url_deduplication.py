import pytest
from sqlalchemy import select

from app.models.applications import ApplicationModel
from app.models.staging import StagingItemModel
from app.schemas.llm import JobAssessmentResult
from app.services.job_saver import persist_or_stage_job_assessment


@pytest.mark.asyncio
async def test_persist_job_assessment_deduplicates_referral_urls(db_session):
    """Test that submitting the same job posting URL with different referral parameters is detected as a duplicate."""
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
    app_id = res1["application_id"]

    # Verify stored application job_url is clean and normalized
    app_record = await db_session.get(ApplicationModel, app_id)
    assert app_record.job_url == "https://stripe.com/jobs/senior-dev"

    # Submit second job assessment for the same job with DIFFERENT referral params
    second_assessment = JobAssessmentResult(
        company="Stripe",
        position="Senior Software Engineer",
        fit_score=85,
        summary="Duplicate job lead from Twitter referral.",
        matching_skills=["Python"],
    )

    url_2 = "https://stripe.com/jobs/senior-dev?utm_source=twitter&ref=colleague2&fbclid=123456"
    res2 = await persist_or_stage_job_assessment(
        db=db_session,
        assessment=second_assessment,
        raw_text="Job description text for senior dev",
        job_url=url_2,
    )

    assert res2["status"] == "staged"
    assert res2["is_duplicate"] is True
    assert res2["route"] == "staging"
    assert res2["existing_application_id"] == app_id

    # Verify Staging item was created
    staging_res = await db_session.execute(
        select(StagingItemModel).where(StagingItemModel.id == res2["staging_item_id"])
    )
    staged_item = staging_res.scalar_one_or_none()
    assert staged_item is not None
    assert staged_item.match_reason == "DUPLICATE_APPLICATION_FOUND"
