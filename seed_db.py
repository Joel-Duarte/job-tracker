import asyncio
from app.core.database import AsyncSessionLocal
from app.models.applications import ApplicationModel, CompanyModel
from app.models.intake_tasks import IntakeEvaluationTaskModel

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if company exists
        company = CompanyModel(name="Acme Corp", name_normalized="acme corp", domain="acme.com")
        session.add(company)
        await session.flush()

        app1 = ApplicationModel(
            company_id=company.id,
            position="Senior Frontend Engineer",
            status="APPLIED",
            cover_letter_text="Dear Hiring Manager,\n\nI am thrilled to apply for the Senior Frontend Engineer role at Acme Corp. With over 8 years of experience building modern web applications...",
            cover_letter_status="DRAFTED",
            match_score=88,
            location="San Francisco, CA (Hybrid)",
            work_model="Hybrid",
            salary_min=160000,
            salary_max=190000,
            currency="USD",
        )
        session.add(app1)

        app2 = ApplicationModel(
            company_id=company.id,
            position="Staff Systems Architect",
            status="APPLIED",
            cover_letter_text=None,
            cover_letter_status=None,
            match_score=75,
            location="Remote",
            work_model="Remote",
            salary_min=180000,
            salary_max=220000,
            currency="USD",
        )
        session.add(app2)

        await session.commit()

        task1 = IntakeEvaluationTaskModel(
            task_type="JOB_ASSESSMENT",
            status="COMPLETED",
            stage="COMPLETE",
            title_hint="Acme Corp - Senior Frontend Engineer",
            result_json={
                "application_id": app1.id,
                "company": "Acme Corp",
                "position": "Senior Frontend Engineer",
                "match_score": 88,
                "cover_letter_text": app1.cover_letter_text,
                "cover_letter_status": "DRAFTED",
                "summary": "Excellent match fit across Vue.js and TypeScript requirements.",
                "matching_skills": ["Vue.js", "JavaScript", "CSS"],
                "missing_skills": ["GraphQL"],
            }
        )
        session.add(task1)
        await session.commit()

        print("Seeded successfully! App1 ID:", app1.id, "App2 ID:", app2.id)

if __name__ == "__main__":
    asyncio.run(seed())
