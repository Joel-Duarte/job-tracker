# Test Data Seeding Guide & Database Schema Specification (`guide.md`)

This specification document outlines the database schema audit, relationship dependencies, data generation rules, and concrete seeding implementation guidelines for building a realistic, multi-phase test dataset for development and automated testing environments.

---

## 1. Database Schema Audit & Entity Relationships

The application uses SQLAlchemy models mapped to PostgreSQL database tables. Below is the comprehensive audit of core models, foreign key dependencies, unique constraints, indices, required fields, and status enums.

### Entity Relationship & Dependency Graph

To prevent foreign key constraint violations during seeding or cleanup, entities must be created in order of their dependency hierarchy:

```
[CandidateCVModel]       [CompanyModel]        [EmailAccountModel]      [AIProviderModel]
                               |                        |                       |
                       [ApplicationModel]      [StagingItemModel]      [AITaskBindingModel]
                       /       |        \
      [JobPostingModel] [EventModel] [Embedding]
                             |
                       [ActionItemModel]

[OtherEventModel]    [IntakeEvaluationTaskModel]    [SystemSettingsModel]
```

---

### Core Database Models Audit Table

| Model Name (`__tablename__`) | Primary Key | Foreign Keys & Relationships | Required / Non-Nullable Fields | Unique Constraints / Indices | Status & Stage Enums |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CompanyModel`**<br/>(`email_companies`) | `id` (BigInteger) | `applications` (1-to-N) | `name`<br/>`name_normalized` | `idx_email_companies_name_normalized` (UNIQUE)<br/>`idx_email_companies_domain`<br/>`idx_email_companies_name_trgm` (GIN) | N/A |
| **`ApplicationModel`**<br/>(`email_applications`) | `id` (BigInteger) | `company_id` -> `email_companies.id` (RESTRICT)<br/>`events` (1-to-N, CASCADE)<br/>`job_posting` (1-to-1, CASCADE)<br/>`embedding_record` (1-to-1, CASCADE)<br/>`action_items` (1-to-N, CASCADE) | `company_id`<br/>`status` (default: `"APPLIED"`) | `idx_email_applications_company_id`<br/>`idx_email_applications_status`<br/>`idx_email_applications_external_job_id`<br/>`idx_email_applications_application_key` | Statuses:<br/>`"APPLIED"`, `"IN_PROGRESS"`, `"ONLINE_ASSESSMENT"`, `"RECRUITER_SCREEN"`, `"TECHNICAL_INTERVIEW"`, `"OFFER"`, `"HIRED"`, `"REJECTED"`, `"ARCHIVED"` |
| **`JobPostingModel`**<br/>(`job_postings`) | `id` (BigInteger) | `application_id` -> `email_applications.id` (CASCADE) | `job_url` | `idx_job_postings_application_id`<br/>`idx_job_postings_job_url` | Work Models:<br/>`"Remote"`, `"Hybrid"`, `"Onsite"` |
| **`ApplicationEventModel`**<br/>(`email_application_events`) | `id` (BigInteger) | `email_application_id` -> `email_applications.id` (CASCADE)<br/>`action_items` (1-to-N, SET NULL) | `email_application_id`<br/>`email_event_type`<br/>`source_channel` (default: `"EMAIL"`) | `email_message_id` (UNIQUE)<br/>`email_internet_message_id` (UNIQUE)<br/>`idx_email_application_events_application_id`<br/>`idx_email_application_events_received_at` | Event Types:<br/>`"APPLICATION_SUBMITTED"`, `"RECRUITER_SCREEN"`, `"ASSESSMENT_REQUEST"`, `"INTERVIEW_INVITE"`, `"OFFER_RECEIVED"`, `"REJECTION"` |
| **`ActionItemModel`**<br/>(`action_items`) | `id` (BigInteger) | `application_id` -> `email_applications.id` (CASCADE)<br/>`event_id` -> `email_application_events.id` (SET NULL) | `title`<br/>`status` (default: `"PENDING"`) | `idx_action_items_application_id`<br/>`idx_action_items_status` | Statuses:<br/>`"PENDING"`, `"COMPLETED"`, `"DISMISSED"`<br/>Urgencies:<br/>`"HIGH"`, `"MEDIUM"`, `"LOW"` |
| **`ApplicationEmbeddingModel`**<br/>(`email_application_embeddings`) | `email_application_id` (PK, BigInteger) | `email_application_id` -> `email_applications.id` (CASCADE) | `email_application_id`<br/>`content`<br/>`embedding` (Vector(768)) | `email_application_embeddings_idx` (HNSW) | N/A |
| **`IntakeEvaluationTaskModel`**<br/>(`intake_evaluation_tasks`) | `id` (BigInteger) | Independent | `task_type` (default: `"JOB_ASSESSMENT"`)<br/>`title_hint`<br/>`status` (default: `"QUEUED"`)<br/>`stage` (default: `"FETCHING"`) | `idx_intake_evaluation_tasks_status`<br/>`idx_intake_evaluation_tasks_task_type` | Task Types:<br/>`"JOB_ASSESSMENT"`, `"CV_ANONYMIZATION"`, `"COVER_LETTER"`<br/>Statuses:<br/>`"QUEUED"`, `"PROCESSING"`, `"COMPLETED"`, `"FAILED"`, `"CANCELLED"`<br/>Stages:<br/>`"FETCHING"`, `"SCRUBBING"`, `"EXTRACTING"`, `"MATCHING"`, `"ASSESSING"`, `"SAVING"`, `"COMPLETE"`, `"FAILED"` |
| **`CandidateCVModel`**<br/>(`candidate_cvs`) | `id` (BigInteger) | Independent | `raw_text`<br/>`is_active` (default: `true`) | N/A | N/A |
| **`StagingItemModel`**<br/>(`email_staging_items`) | `id` (BigInteger) | Independent | `status` (default: `"PENDING"`) | `email_message_id` (UNIQUE)<br/>`email_internet_message_id` (UNIQUE)<br/>`idx_email_staging_items_status` | Statuses:<br/>`"PENDING"`, `"APPROVED"`, `"REJECTED"`, `"PROCESSED"` |
| **`OtherEventModel`**<br/>(`email_other_events`) | `id` (BigInteger) | Independent | `email_type` | `email_message_id` (UNIQUE)<br/>`email_internet_message_id` (UNIQUE) | Types:<br/>`"NEWSLETTER"`, `"RECRUITER_OUTREACH"`, `"COMMUNITY"` |
| **`AIProviderModel`**<br/>(`ai_providers`) | `id` (BigInteger) | `task_bindings` (1-to-N, CASCADE) | `name`<br/>`provider_type`<br/>`max_concurrency`<br/>`is_active` | N/A | Provider Types:<br/>`"openai"`, `"anthropic"`, `"ollama"`, `"azure"` |
| **`AITaskBindingModel`**<br/>(`ai_task_bindings`) | `id` (BigInteger) | `provider_id` -> `ai_providers.id` (RESTRICT) | `task_type`<br/>`provider_id`<br/>`model_name`<br/>`temperature` | `task_type` (UNIQUE) | Task Bindings:<br/>`"GLOBAL_DEFAULT"`, `"JOB_ASSESSMENT"`, `"EMAIL_EXTRACTION"`, `"INTERVIEW_GUIDE"`, `"JD_EXTRACTION"`, `"COVER_LETTER"` |

---

## 2. Realistic Mock Data Generation Rules (Rolling 90-Day Window)

To test weekly/monthly funnel metrics, trend deltas, and cohort conversions, seeded timestamps must be distributed across a **rolling 90-day historical window** relative to execution time (`now`).

### Pipeline Distribution Ratios
Seed datasets should adhere to realistic recruitment funnel conversion drop-offs:

1. **Applications Pipeline Distribution** (Total N = ~25 - 30 applications):
   - **`APPLIED` / `IN_PROGRESS`**: ~40% (New leads, recent submissions, high volume)
   - **`ONLINE_ASSESSMENT`**: ~15% (Initial technical screens)
   - **`TECHNICAL_INTERVIEW`**: ~20% (Active mid/late stage pipelines)
   - **`OFFER` / `HIRED`**: ~10% (Successful top conversions)
   - **`REJECTED` / `ARCHIVED`**: ~15% (Terminal pipeline states)

2. **Time Window Distribution Strategy** (Rolling 90 Days):
   - **Days 0 - 14 (Current Period)**: ~35% of all applications & events (drives current period KPI calculations)
   - **Days 15 - 30 (Previous Period)**: ~30% of applications & events (enables non-zero trend delta calculations)
   - **Days 31 - 90 (Historical Cohorts)**: ~35% distributed across weeks W-4 to W-12 (populates historical weekly/monthly analytics charts)

3. **Compensation & Work Model Distributions**:
   - **Salary Ranges**: $120,000 to $320,000 USD (Base) with $20k-$60k spread between `salary_min` and `salary_max`.
   - **Work Models**:
     - `Remote`: 60%
     - `Hybrid`: 30%
     - `Onsite`: 10%
   - **Fit Scores (`fit_score`)**:
     - `STRONG_MATCH` (80 - 95): 45%
     - `MODERATE_MATCH` (65 - 79): 35%
     - `LOW_MATCH` (40 - 64): 20%

---

## 3. Standardized JSON Schema Specifications

Complex JSONB fields require strict, uniform structures to avoid runtime errors in frontend components and analytical services.

### A. `match_analysis_payload` (ApplicationModel)

```json
{
  "company": "Stripe",
  "position": "Senior Backend Engineer - Global Payments",
  "fit_score": 92,
  "programmatic_match_score": 88,
  "fit_tier": "STRONG_MATCH",
  "match_summary": "Exceptional alignment with candidate's experience in high-throughput Python/FastAPI microservices and PostgreSQL transactional consistency.",
  "hard_matches": {
    "keyword_match_rate": "9/10 core skills found",
    "top_alignment": [
      "Python & FastAPI Backend Architecture",
      "PostgreSQL Transaction Isolation",
      "Kafka Distributed Event Streaming"
    ]
  },
  "optimization_gaps": {
    "missing_completely": ["ISO 20022 Financial Protocols"],
    "vocabulary_mismatches": ["Used 'reconciliation' vs 'double-entry ledger'"],
    "experience_mismatch": null
  },
  "tailoring_strategy": {
    "vocabulary_translation": [
      {
        "jd_term": "Double-entry ledger infrastructure",
        "cv_term": "Payment reconciliation pipelines",
        "replacement_guidance": "Explicitly highlight double-entry bookkeeping and exact-once semantics."
      }
    ],
    "impact_reframing": [
      {
        "bullet_point": "Scaled payment settlement pipelines to 45,000 req/sec.",
        "suggested_rewrite": "Architected zero-downtime payment settlement engine handling 45k req/sec across multi-region PostgreSQL clusters.",
        "reason": "Emphasizes reliability SLAs and distributed database resilience."
      }
    ],
    "structural_adjustments": [
      "Elevate payment settlement section to top of experience."
    ]
  },
  "matching_skills": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis", "Docker", "Kubernetes"],
  "missing_skills": ["ISO 20022", "Financial Ledger Auditing"],
  "pros": ["Industry-leading compensation", "World-class distributed systems team"],
  "cons": ["High stakes on-call rotation"],
  "salary_min": 195000.0,
  "salary_max": 245000.0,
  "currency": "USD",
  "location": "Remote (North America)",
  "work_model": "Remote",
  "recommendation": "APPLY_STRONGLY",
  "summary": "Outstanding candidate-job match."
}
```

### B. `structured_spec` (JobPostingModel)

```json
{
  "job_found": true,
  "company": "Stripe",
  "company_url": "stripe.com",
  "position": "Senior Backend Engineer - Global Payments",
  "why_hiring": "Expanding global payments platform to support multi-currency settlement scaling.",
  "what_you_will_build": "Zero-downtime double-entry ledger engines and high-throughput transactional APIs.",
  "responsibilities": [
    "Architect, build, and maintain high-reliability transactional APIs processing millions of daily transactions.",
    "Optimize distributed consensus and asynchronous idempotency across acquiring networks."
  ],
  "requirements": [
    "5+ years software engineering experience in Python, Go, or Java.",
    "Deep expertise in PostgreSQL, transaction isolation levels, and data modeling.",
    "Experience with Kafka or distributed event streaming."
  ],
  "extracted_skills": ["Python", "Go", "PostgreSQL", "Kafka", "FastAPI", "Redis"],
  "compensation_text": "$195,000 - $245,000 USD",
  "location_text": "San Francisco, CA / Remote",
  "workplace_type": "Remote"
}
```

---

## 4. Concrete Python Seeding Implementation Example

Below is a complete, execution-ready Async SQLAlchemy seeding pattern that populates a 90-day rolling dataset.

```python
import logging
from datetime import UTC, datetime, timedelta
import random

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.applications import (
    CompanyModel,
    ApplicationModel,
    JobPostingModel,
    ApplicationEventModel,
    ActionItemModel,
)
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.candidate_profile import CandidateCVModel

logger = logging.getLogger(__name__)

async def seed_rolling_90day_dataset(session: AsyncSession) -> dict[str, int]:
    now = datetime.now(UTC)
    stats = {"companies": 0, "applications": 0, "events": 0, "intake_tasks": 0}

    # 1. Seed Candidate Profile
    cv = CandidateCVModel(
        raw_text="Alex Morgan\nStaff Backend Engineer\nSkills: Python, FastAPI, PostgreSQL, Kafka, Redis, Go, Kubernetes",
        extracted_skills=["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis", "Go", "Kubernetes", "Docker", "TypeScript"],
        years_of_experience=8.0,
        is_active=True,
    )
    session.add(cv)

    # 2. Define Sample Companies & Job Specs
    companies_data = [
        ("Stripe", "stripe.com", "Senior Backend Engineer", 195000, 245000, "Remote", "APPLIED", 3),
        ("Linear", "linear.app", "Staff Systems & Sync Engineer", 210000, 275000, "Remote", "TECHNICAL_INTERVIEW", 12),
        ("Figma", "figma.com", "Principal Platform Engineer", 240000, 310000, "Hybrid", "OFFER", 25),
        ("Datadog", "datadoghq.com", "Senior Tracing Engineer", 185000, 235000, "Hybrid", "ONLINE_ASSESSMENT", 5),
        ("Airbnb", "airbnb.com", "Senior Platform Engineer", 190000, 240000, "Remote", "REJECTED", 20),
        ("Snowflake", "snowflake.com", "Principal Cloud Architect", 220000, 280000, "Hybrid", "APPLIED", 45),
        ("Vercel", "vercel.com", "Senior Edge Systems Engineer", 180000, 230000, "Remote", "TECHNICAL_INTERVIEW", 55),
        ("Cloudflare", "cloudflare.com", "Staff Network Engineer", 200000, 260000, "Onsite", "REJECTED", 70),
    ]

    for comp_name, domain, pos, sal_min, sal_max, work_model, status, days_ago in companies_data:
        app_date = now - timedelta(days=days_ago)

        # Create Company
        comp = CompanyModel(
            name=comp_name,
            name_normalized=comp_name.lower(),
            domain=domain,
        )
        session.add(comp)
        await session.flush()
        stats["companies"] += 1

        # Create Application
        app = ApplicationModel(
            company_id=comp.id,
            position=pos,
            position_normalized=pos.lower(),
            status=status,
            application_date=app_date,
            last_activity_at=app_date + timedelta(days=1),
            match_analysis_payload={
                "fit_score": random.randint(75, 95),
                "programmatic_match_score": random.randint(70, 90),
                "fit_tier": "STRONG_MATCH",
                "missing_skills": ["Rust"] if random.random() > 0.5 else [],
            },
        )
        session.add(app)
        await session.flush()
        stats["applications"] += 1

        # Create Job Posting
        jp = JobPostingModel(
            application_id=app.id,
            job_url=f"https://{domain}/jobs/{app.id}",
            salary_min=sal_min,
            salary_max=sal_max,
            work_model=work_model,
            required_skills=["Python", "PostgreSQL", "Distributed Systems"],
        )
        session.add(jp)

        # Create Timeline Events
        evt = ApplicationEventModel(
            email_application_id=app.id,
            email_message_id=f"msg-{app.id}-1",
            email_sender=f"recruiting@{domain}",
            email_subject=f"Application Status for {pos}",
            email_received_at=app_date,
            email_event_type="APPLICATION_SUBMITTED" if status == "APPLIED" else "INTERVIEW_INVITE",
            email_status_after_event=status,
        )
        session.add(evt)
        stats["events"] += 1

        # Seed Intake Queue Tasks across the 90-day window
        task = IntakeEvaluationTaskModel(
            task_type="JOB_ASSESSMENT",
            job_url=f"https://{domain}/jobs/{app.id}",
            title_hint=f"{comp_name} - {pos}",
            status="COMPLETED",
            stage="COMPLETE",
            created_at=app_date,
            completed_at=app_date + timedelta(minutes=2),
        )
        session.add(task)
        stats["intake_tasks"] += 1

    await session.commit()
    logger.info(f"Seeding completed successfully: {stats}")
    return stats
```

---

## 5. Verification & Testing Instructions

To verify that seeded data properly feeds into the analytical endpoints and UI views:

1. **Database Seeding Execution**:
   ```bash
   uv run python -m app.services.seed_data
   ```

2. **Metrics & Analytics Endpoint Verification**:
   - Query funnel metrics for weekly aggregated cohorts:
     `GET /api/v1/analytics/funnel?period=weekly&num_periods=8`
   - Confirm non-zero trend percentages (`trend_percentage`) and valid `chart_data` / `table_data` structures.

3. **Ruff Formatting & Linting Check**:
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   ```
