import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_providers import AIProviderModel, AITaskBindingModel
from app.models.applications import (
    ActionItemModel,
    ApplicationEventModel,
    ApplicationModel,
    CompanyModel,
    JobPostingModel,
    OtherEventModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.email_accounts import EmailAccountModel
from app.models.intake_tasks import IntakeEvaluationTaskModel
from app.models.staging import StagingItemModel

logger = logging.getLogger(__name__)


def build_stripe_dossier() -> dict:
    return {
        "company": "Stripe",
        "position": "Senior Backend Engineer - Global Payments",
        "fit_score": 94,
        "programmatic_match_score": 90,
        "fit_tier": "STRONG_MATCH",
        "match_summary": (
            "Exceptional alignment with candidate's 8+ years scaling high-throughput Python/FastAPI distributed systems, "
            "PostgreSQL transactional consistency, and Kafka streaming pipelines."
        ),
        "hard_matches": {
            "keyword_match_rate": "9/10 core skills found",
            "top_alignment": [
                "Python & FastAPI Backend Architecture",
                "PostgreSQL Transaction Isolation & Concurrency",
                "Kafka Distributed Event Streaming",
            ],
        },
        "optimization_gaps": {
            "missing_completely": [
                "Direct ISO 20022 / SWIFT interbank settlement protocol experience"
            ],
            "vocabulary_mismatches": [
                "Ledger Consistency (used 'billing reconciliation' in CV vs 'double-entry ledger' in JD)"
            ],
            "experience_mismatch": None,
        },
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "jd_term": "Double-entry ledger infrastructure",
                    "cv_term": "Payment reconciliation pipelines",
                    "replacement_guidance": "Explicitly highlight double-entry bookkeeping and exact-once transactional semantics.",
                },
                {
                    "jd_term": "Asynchronous idempotency keys",
                    "cv_term": "Deduplicated API requests",
                    "replacement_guidance": "Use standard fintech terminology: 'Idempotency key management with Redis distributed locks'.",
                },
            ],
            "impact_reframing": [
                {
                    "bullet_point": "Scaled payment settlement pipelines to 45,000 req/sec at CloudTech.",
                    "suggested_rewrite": "Architected zero-downtime distributed payment settlement engine handling 45k req/sec with 99.999% SLA across multi-region PostgreSQL clusters.",
                    "reason": "Emphasizes reliability SLAs and distributed database resilience required for Stripe's tier-1 payment services.",
                }
            ],
            "structural_adjustments": [
                "Elevate the CloudTech payment settlement section to the top of the Experience section.",
                "Group Kafka, Redis, and PostgreSQL under a dedicated 'Distributed Data Primitives' skill category.",
            ],
        },
        "matching_skills": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Distributed Systems",
            "Kafka",
            "Redis",
            "Docker",
            "Kubernetes",
            "AWS",
            "System Design",
        ],
        "missing_skills": ["ISO 20022", "Financial Ledger Auditing"],
        "pros": [
            "Industry-leading compensation package ($195k-$245k + top-tier equity)",
            "World-class distributed systems engineering culture and tooling",
            "High leverage and direct business impact on global commerce",
        ],
        "cons": [
            "High-stakes on-call rotation with strict latency SLAs",
            "High technical complexity across cross-border acquiring networks",
        ],
        "salary_min": 195000.0,
        "salary_max": 245000.0,
        "currency": "USD",
        "location": "Remote (North America / Europe)",
        "work_model": "Remote",
        "recommendation": "APPLY_STRONGLY",
        "summary": "Outstanding candidate-job match. Highly recommended to pursue through immediate recruiter interview scheduling.",
    }


def build_linear_dossier() -> dict:
    return {
        "company": "Linear",
        "position": "Staff Systems & Sync Engineer",
        "fit_score": 89,
        "programmatic_match_score": 85,
        "fit_tier": "STRONG_MATCH",
        "match_summary": (
            "Strong match across distributed state synchronization, PostgreSQL performance, and real-time backend architecture. "
            "Candidate's deep systems background directly translates to local-first client sync."
        ),
        "hard_matches": {
            "keyword_match_rate": "8/10 core skills found",
            "top_alignment": [
                "Distributed Systems & State Synchronization",
                "PostgreSQL Performance & Index Tuning",
                "TypeScript / Node.js High-Concurrency Backends",
            ],
        },
        "optimization_gaps": {
            "missing_completely": ["CRDT implementation experience in production"],
            "vocabulary_mismatches": [
                "Real-time sync (used 'event streaming' vs 'delta-based state reconciliation')"
            ],
            "experience_mismatch": None,
        },
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "jd_term": "Local-first client state sync",
                    "cv_term": "Optimistic UI and real-time backend events",
                    "replacement_guidance": "Frame experience around offline delta sync protocols and conflict resolution algorithms.",
                }
            ],
            "impact_reframing": [
                {
                    "bullet_point": "Built async ingestion engines and PostgreSQL partitioned storage at DataSphere.",
                    "suggested_rewrite": "Engineered low-latency async state synchronization engine utilizing PostgreSQL JSONB and WebSocket subscriptions, reducing client round-trip latency to <15ms.",
                    "reason": "Highlights speed and latency metrics that align directly with Linear's brand of instantaneous responsiveness.",
                }
            ],
            "structural_adjustments": [
                "Add a 'Sync & Concurrency Patterns' bullet point to the core competencies summary.",
            ],
        },
        "matching_skills": [
            "TypeScript",
            "PostgreSQL",
            "Distributed Systems",
            "Redis",
            "System Design",
            "Docker",
        ],
        "missing_skills": ["CRDTs", "SQLite/Wasm Client Storage"],
        "pros": [
            "Exceptionally high product quality standard and engineering autonomy",
            "Pure remote-first work culture with low meeting overhead",
            "Competitive staff-level compensation ($210k - $275k)",
        ],
        "cons": [
            "Small team requiring strong cross-functional ownership from protocol to UI",
        ],
        "salary_min": 210000.0,
        "salary_max": 275000.0,
        "currency": "USD",
        "location": "Remote (Global)",
        "work_model": "Remote",
        "recommendation": "APPLY_STRONGLY",
        "summary": "Excellent fit for Staff Systems role. Technical interview preparation should focus on synchronization architecture.",
    }


def build_figma_dossier() -> dict:
    return {
        "company": "Figma",
        "position": "Principal Platform Engineer",
        "fit_score": 86,
        "programmatic_match_score": 80,
        "fit_tier": "STRONG_MATCH",
        "match_summary": (
            "Strong platform match with deep Kubernetes, distributed compute, and systems expertise. "
            "Candidate has extensive scale experience to support Figma multiplayer canvas infrastructure."
        ),
        "hard_matches": {
            "keyword_match_rate": "8/10 core skills found",
            "top_alignment": [
                "Cloud-Native Kubernetes & Platform Engineering",
                "High-Concurrency Go and Systems Architecture",
                "Multi-Tenant Distributed Compute Clustering",
            ],
        },
        "optimization_gaps": {
            "missing_completely": ["C++ Canvas Engine Rendering"],
            "vocabulary_mismatches": ["Rust/WASM runtime bridge"],
            "experience_mismatch": None,
        },
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "jd_term": "Multiplayer state synchronization",
                    "cv_term": "Distributed consensus and stream processing",
                    "replacement_guidance": "Frame data streams as real-time collaborative document mutations.",
                }
            ],
            "impact_reframing": [
                {
                    "bullet_point": "Managed platform infrastructure across multi-region Kubernetes clusters.",
                    "suggested_rewrite": "Architected resilient multi-cluster Kubernetes platform supporting 10M+ daily active sessions with automated traffic failover and zero packet loss.",
                    "reason": "Demonstrates the massive scale demanded by Figma's global collaborative user base.",
                }
            ],
            "structural_adjustments": [
                "Highlight Go, Kubernetes, and WebAssembly in the top technical summary.",
            ],
        },
        "matching_skills": [
            "Go",
            "Kubernetes",
            "Distributed Systems",
            "AWS",
            "Docker",
            "PostgreSQL",
        ],
        "missing_skills": ["Rust WebAssembly Compilation", "C++"],
        "pros": [
            "Lucrative offer package ($285k base + $140k/yr equity)",
            "Industry-defining collaborative creative suite platform",
            "High-caliber platform engineering organization",
        ],
        "cons": [
            "Complex legacy C++ engine interfaces alongside modern Rust/WASM stacks",
        ],
        "salary_min": 240000.0,
        "salary_max": 310000.0,
        "currency": "USD",
        "location": "San Francisco, CA / Remote",
        "work_model": "Hybrid",
        "recommendation": "APPLY_STRONGLY",
        "summary": "Outstanding offer secured. Evaluation shows strong technical alignment and compelling career growth.",
    }


def build_datadog_dossier() -> dict:
    return {
        "company": "Datadog",
        "position": "Senior Software Engineer - Distributed Tracing",
        "fit_score": 84,
        "programmatic_match_score": 82,
        "fit_tier": "STRONG_MATCH",
        "match_summary": (
            "Solid match for APM ingest and distributed tracing pipelines. "
            "Candidate's Go/Python streaming background aligns with high-scale telemetry ingestion."
        ),
        "hard_matches": {
            "keyword_match_rate": "8/10 core skills found",
            "top_alignment": [
                "Go & Python High-Performance Backends",
                "Kafka High-Throughput Ingestion Pipelines",
                "Distributed Systems Reliability",
            ],
        },
        "optimization_gaps": {
            "missing_completely": ["eBPF kernel telemetry probing"],
            "vocabulary_mismatches": ["OpenTelemetry span instrumentation"],
            "experience_mismatch": None,
        },
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "jd_term": "Distributed trace propagation",
                    "cv_term": "Correlation ID request tracing",
                    "replacement_guidance": "Use W3C Trace Context and OpenTelemetry terminology.",
                }
            ],
            "impact_reframing": [],
            "structural_adjustments": [],
        },
        "matching_skills": [
            "Go",
            "Python",
            "Kafka",
            "Redis",
            "Distributed Systems",
            "Kubernetes",
        ],
        "missing_skills": ["eBPF", "OpenTelemetry SDK internals"],
        "pros": [
            "Market leader in cloud observability with massive dataset scale",
            "Strong engineering focus on low-level Linux and memory efficiency",
        ],
        "cons": [
            "Heavy operational footprint and continuous telemetry data pressure",
        ],
        "salary_min": 185000.0,
        "salary_max": 235000.0,
        "currency": "USD",
        "location": "New York, NY / Remote",
        "work_model": "Hybrid",
        "recommendation": "APPLY",
        "summary": "High alignment on backend ingest pipelines. Online assessment sent to evaluate algorithms and concurrency.",
    }


def build_airbnb_dossier() -> dict:
    return {
        "company": "Airbnb",
        "position": "Senior Platform Engineer",
        "fit_score": 78,
        "programmatic_match_score": 75,
        "fit_tier": "MODERATE_MATCH",
        "match_summary": (
            "Good core platform background, but role requires heavy JVM/Java ecosystem experience "
            "which is a slight delta from candidate's Python/Go focus."
        ),
        "hard_matches": {
            "keyword_match_rate": "6/10 core skills found",
            "top_alignment": [
                "Kubernetes & Cloud Infrastructure Platform",
                "AWS Infrastructure as Code & Terraform",
            ],
        },
        "optimization_gaps": {
            "missing_completely": ["Java / Spring Boot Microservices Platform"],
            "vocabulary_mismatches": [],
            "experience_mismatch": "Position prioritized internal JVM platform specialists",
        },
        "tailoring_strategy": {
            "vocabulary_translation": [],
            "impact_reframing": [],
            "structural_adjustments": [],
        },
        "matching_skills": [
            "Kubernetes",
            "AWS",
            "Docker",
            "Distributed Systems",
        ],
        "missing_skills": ["Java", "Spring Boot", "Spinnaker"],
        "pros": ["Strong brand, generous travel benefits"],
        "cons": ["Heavy legacy JVM platform stack"],
        "salary_min": 190000.0,
        "salary_max": 240000.0,
        "currency": "USD",
        "location": "San Francisco, CA / Remote",
        "work_model": "Remote",
        "recommendation": "CAUTION",
        "summary": "Application closed following internal candidate selection.",
    }


async def is_database_empty(session: AsyncSession) -> bool:
    """Checks if the database has zero applications and companies."""
    count_apps = (
        await session.execute(select(func.count(ApplicationModel.id)))
    ).scalar_one()
    count_companies = (
        await session.execute(select(func.count(CompanyModel.id)))
    ).scalar_one()
    return count_apps == 0 and count_companies == 0


async def seed_development_dataset(session: AsyncSession) -> dict[str, int]:
    """
    Populates a rich, multi-domain mock development dataset covering all application features:
    - 1 Active Candidate CV Profile
    - 5 Companies & Applications with diverse statuses and full candidate dossiers
    - 5 Linked Job Postings with salaries, skills, and descriptions
    - 9 Timeline Application Events
    - 5 Action Items with varying urgencies and deadlines
    - 3 Non-Job 'Other' Recruitment & Tech Events
    - 3 Ambiguous Staging Queue Leads for triage
    - 3 Persisted Intake AI Evaluation Tasks with complete dossier results
    - 3 AI Providers & default Task Bindings
    - 2 Connected Email Accounts

    Note: Vector embeddings are deliberately omitted to avoid external model requirements during bootstrap.
    """
    now = datetime.now(UTC)
    stats: dict[str, int] = {}

    # -------------------------------------------------------------------------
    # 1. Candidate CV Profile
    # -------------------------------------------------------------------------
    cv = CandidateCVModel(
        raw_text=(
            "Alex Morgan\n"
            "Staff Software Engineer & Distributed Systems Architect\n"
            "Email: alex.morgan.dev@gmail.com | Location: San Francisco, CA (Remote Friendly)\n\n"
            "Summary:\n"
            "Staff backend engineer with 8+ years of experience designing and scaling distributed systems, "
            "event-driven microservices, and high-throughput transactional APIs in Python, Go, and TypeScript. "
            "Experienced with PostgreSQL, Kafka, Redis, Kubernetes, AWS, and LLM orchestration (LangChain, LangGraph).\n\n"
            "Experience:\n"
            "- Senior Distributed Systems Engineer at CloudTech (2022 - Present): Scaled payment settlement pipelines to 45,000 req/sec.\n"
            "- Backend Infrastructure Engineer at DataSphere (2018 - 2022): Built async ingestion engines and PostgreSQL partitioned storage.\n\n"
            "Skills: Python, FastAPI, Go, TypeScript, PostgreSQL, Distributed Systems, Kafka, Redis, Docker, Kubernetes, AWS, LangChain, System Design."
        ),
        anonymized_text=(
            "[Candidate] - Staff Software Engineer & Distributed Systems Architect\n"
            "Summary: Staff backend engineer with 8+ years of experience designing and scaling distributed systems.\n"
            "Skills: Python, FastAPI, Go, TypeScript, PostgreSQL, Distributed Systems, Kafka, Redis, Docker, Kubernetes, AWS, LangChain, System Design."
        ),
        extracted_skills=[
            "Python",
            "FastAPI",
            "Go",
            "TypeScript",
            "PostgreSQL",
            "Distributed Systems",
            "Kafka",
            "Redis",
            "Docker",
            "Kubernetes",
            "AWS",
            "LangChain",
            "System Design",
            "Vue.js",
        ],
        years_of_experience=8.5,
        domain_expertise=[
            "Fintech & Payments Infrastructure",
            "Distributed Systems & Event-Driven Architecture",
            "High-Throughput API Design",
            "Cloud Native & Kubernetes Platform",
        ],
        domain_experience=[
            {
                "domain": "Fintech & Payments Infrastructure",
                "years": 4.0,
                "description": "High-throughput settlement engines and ledger consistency",
            },
            {
                "domain": "Distributed Systems",
                "years": 6.5,
                "description": "Kafka stream processing, Redis caching, async pipelines",
            },
        ],
        core_competencies=[
            "High-Throughput Backend Architecture",
            "Relational Database Performance Optimization",
            "Fault-Tolerant Distributed Consensus",
            "Full-Stack Web App Development (Vue 3 + FastAPI)",
        ],
        summary="Senior / Staff Distributed Systems Engineer specializing in Python, FastAPI, and real-time backend architectures.",
        is_active=True,
    )
    session.add(cv)
    stats["candidate_cvs"] = 1

    # -------------------------------------------------------------------------
    # 2. Companies & Applications (with Match Analysis Dossiers)
    # -------------------------------------------------------------------------

    # --- Company 1: Stripe (Status: APPLIED) ---
    stripe_dossier = build_stripe_dossier()
    stripe = CompanyModel(name="Stripe", name_normalized="stripe", domain="stripe.com")
    session.add(stripe)
    await session.flush()

    app_stripe = ApplicationModel(
        company_id=stripe.id,
        position="Senior Backend Engineer - Global Payments",
        position_normalized="senior backend engineer - global payments",
        external_job_id="stripe-pay-8821",
        job_url="https://stripe.com/jobs/senior-backend-payments",
        status="APPLIED",
        application_date=now - timedelta(days=4),
        last_activity_at=now - timedelta(days=1),
        match_analysis_payload=stripe_dossier,
    )
    session.add(app_stripe)
    await session.flush()

    jp_stripe = JobPostingModel(
        application_id=app_stripe.id,
        job_url="https://stripe.com/jobs/senior-backend-payments",
        description_markdown="""# Senior Backend Engineer - Global Payments

Stripe is looking for a Senior Backend Engineer to join our Core Payments Infrastructure organization.

### What you will do:
- Architect, build, and maintain high-reliability transactional APIs processing millions of daily transactions.
- Optimize distributed consensus and asynchronous idempotency across international acquiring networks.
- Partner with security and compliance teams to enforce zero-trust payment primitives.

### Qualifications:
- 5+ years of software engineering experience in Python, Go, or Java.
- Deep expertise in PostgreSQL, transaction isolation levels, and data modeling.
- Experience with Kafka, RabbitMQ, or distributed event streaming.
- Strong fundamentals in distributed systems consistency models.
""",
        salary_min=195000,
        salary_max=245000,
        currency="USD",
        location="Remote (North America / Europe)",
        work_model="Remote",
        required_skills=[
            "Python",
            "Distributed Systems",
            "Kafka",
            "PostgreSQL",
            "FastAPI",
        ],
    )
    session.add(jp_stripe)

    event_stripe_1 = ApplicationEventModel(
        email_application_id=app_stripe.id,
        email_message_id="stripe-msg-001",
        email_sender="recruiting@stripe.com",
        email_sender_name="Stripe Talent Team",
        email_subject="Application Received: Senior Backend Engineer - Global Payments",
        email_received_at=now - timedelta(days=4),
        email_event_type="APPLICATION_SUBMITTED",
        email_status_after_event="APPLIED",
        email_summary="Confirmation that your application for Senior Backend Engineer was received.",
        email_action_required=False,
        email_raw_body="Hi Alex, thank you for applying to Stripe! Our engineering team is currently reviewing your background.",
    )
    event_stripe_2 = ApplicationEventModel(
        email_application_id=app_stripe.id,
        email_message_id="stripe-msg-002",
        email_sender="sarah.connor@stripe.com",
        email_sender_name="Sarah Connor (Stripe Recruiting)",
        email_subject="Next Steps with Stripe: Senior Backend Engineer",
        email_received_at=now - timedelta(days=1),
        email_event_type="RECRUITER_SCREEN",
        email_status_after_event="APPLIED",
        email_summary="Recruiter reached out to schedule a 30-minute initial conversation.",
        email_action_required=True,
        email_action="Book a 30-minute intro call via Calendly link",
        email_raw_body="Hi Alex, we were impressed with your distributed systems background and would love to schedule a 30-minute introductory call this week.",
    )
    session.add_all([event_stripe_1, event_stripe_2])
    await session.flush()

    action_stripe = ActionItemModel(
        application_id=app_stripe.id,
        event_id=event_stripe_2.id,
        title="Schedule 30-min recruiter screen with Sarah (Stripe Talent)",
        due_date=now + timedelta(hours=20),
        status="PENDING",
        urgency="HIGH",
        action_url="https://calendly.com/stripe-talent/alex-30min",
    )
    session.add(action_stripe)

    # --- Company 2: Linear (Status: TECHNICAL_INTERVIEW) ---
    linear_dossier = build_linear_dossier()
    linear = CompanyModel(name="Linear", name_normalized="linear", domain="linear.app")
    session.add(linear)
    await session.flush()

    guide_html = """<div class="interview-guide-container">
<h2>Linear Technical Architecture Interview Guide</h2>
<p>Tailored preparation for Linear Staff Systems & Sync Engineer round.</p>
<section>
<h3>1. Core Architecture Focus Areas</h3>
<ul>
<li><strong>Offline-first synchronization:</strong> CRDTs, optimistic UI updates, and conflict resolution over WebSockets.</li>
<li><strong>PostgreSQL high-performance indexing:</strong> Partitioning, GiST/GIN indexes for issue tracking, and transaction latency.</li>
<li><strong>Client-server protocol design:</strong> Delta sync payloads and low-bandwidth state reconciliation.</li>
</ul>
</section>
<section>
<h3>2. Strategic Behavioral Points</h3>
<p>Highlight your experience scaling async event streaming pipelines and real-time multi-tenant data sync engines.</p>
</section>
</div>"""

    app_linear = ApplicationModel(
        company_id=linear.id,
        position="Staff Systems & Sync Engineer",
        position_normalized="staff systems & sync engineer",
        external_job_id="linear-eng-402",
        job_url="https://linear.app/careers/staff-systems-engineer",
        status="TECHNICAL_INTERVIEW",
        application_date=now - timedelta(days=12),
        last_activity_at=now - timedelta(hours=14),
        interview_guide_html=guide_html,
        interview_guide_generated_at=now - timedelta(hours=10),
        match_analysis_payload=linear_dossier,
    )
    session.add(app_linear)
    await session.flush()

    jp_linear = JobPostingModel(
        application_id=app_linear.id,
        job_url="https://linear.app/careers/staff-systems-engineer",
        description_markdown="""# Staff Systems & Sync Engineer

Linear is building the future of software project management with instantaneous UI responsiveness.

### Responsibilities:
- Lead the architecture of our real-time client-cloud sync engine.
- Build fault-tolerant distributed sync protocols that work offline and online.
- Optimize database queries and caching layers for sub-10ms response times globally.

### Requirements:
- Deep experience in TypeScript, Node.js, and PostgreSQL.
- Understanding of distributed state, CRDTs, and local-first software patterns.
- Strong background in high-performance WebSockets and Redis pub/sub.
""",
        salary_min=210000,
        salary_max=275000,
        currency="USD",
        location="Remote (Global)",
        work_model="Remote",
        required_skills=[
            "TypeScript",
            "PostgreSQL",
            "Real-time Sync",
            "Distributed Systems",
            "Redis",
        ],
    )
    session.add(jp_linear)

    event_linear_1 = ApplicationEventModel(
        email_application_id=app_linear.id,
        email_message_id="linear-msg-001",
        email_sender="jobs@linear.app",
        email_sender_name="Linear Recruiting",
        email_subject="Linear Application: Staff Systems Engineer",
        email_received_at=now - timedelta(days=12),
        email_event_type="APPLICATION_SUBMITTED",
        email_status_after_event="APPLIED",
        email_summary="Application confirmed.",
        email_action_required=False,
    )
    event_linear_2 = ApplicationEventModel(
        email_application_id=app_linear.id,
        email_message_id="linear-msg-002",
        email_sender="tuomas@linear.app",
        email_sender_name="Tuomas Artman (Linear)",
        email_subject="Linear Architecture Round - System Design Interview Invitation",
        email_received_at=now - timedelta(hours=14),
        email_event_type="INTERVIEW_INVITE",
        email_status_after_event="TECHNICAL_INTERVIEW",
        email_summary="Invited to the 60-minute System Design & Synchronization round.",
        email_action_required=True,
        email_action="Prepare diagrams for offline sync architecture session",
        email_raw_body="Hi Alex, we enjoyed our chat! We would like to invite you to our 60-minute technical architecture interview focusing on data sync and local-first persistence.",
    )
    session.add_all([event_linear_1, event_linear_2])
    await session.flush()

    action_linear = ActionItemModel(
        application_id=app_linear.id,
        event_id=event_linear_2.id,
        title="Prepare system design diagrams for Linear sync architecture round",
        due_date=now + timedelta(days=2),
        status="PENDING",
        urgency="HIGH",
    )
    session.add(action_linear)

    # --- Company 3: Figma (Status: OFFER) ---
    figma_dossier = build_figma_dossier()
    figma = CompanyModel(name="Figma", name_normalized="figma", domain="figma.com")
    session.add(figma)
    await session.flush()

    app_figma = ApplicationModel(
        company_id=figma.id,
        position="Principal Platform Engineer",
        position_normalized="principal platform engineer",
        external_job_id="figma-platform-99",
        job_url="https://figma.com/careers/principal-platform",
        status="OFFER",
        application_date=now - timedelta(days=25),
        last_activity_at=now - timedelta(hours=6),
        match_analysis_payload=figma_dossier,
    )
    session.add(app_figma)
    await session.flush()

    jp_figma = JobPostingModel(
        application_id=app_figma.id,
        job_url="https://figma.com/careers/principal-platform",
        description_markdown="""# Principal Platform Engineer

Help Figma scale multiplayer collaborative canvas technology to hundreds of millions of users worldwide.

### Requirements:
- 8+ years building high-performance compute and platform infrastructure in Rust, Go, or C++.
- Expertise in WebAssembly, Kubernetes, and distributed memory caching.
- Proven leadership driving multi-quarter infrastructure roadmaps.
""",
        salary_min=240000,
        salary_max=310000,
        currency="USD",
        location="San Francisco, CA / Remote",
        work_model="Hybrid",
        required_skills=[
            "Rust",
            "Go",
            "Kubernetes",
            "WebAssembly",
            "Distributed Systems",
        ],
    )
    session.add(jp_figma)

    event_figma_pre = ApplicationEventModel(
        email_application_id=app_figma.id,
        email_message_id="figma-msg-000",
        email_sender="careers@figma.com",
        email_sender_name="Figma Talent Team",
        email_subject="Thank you for applying to Figma",
        email_received_at=now - timedelta(days=25),
        email_event_type="APPLICATION_SUBMITTED",
        email_status_after_event="APPLIED",
        email_summary="Application confirmed for Principal Platform Engineer.",
        email_action_required=False,
    )
    event_figma_1 = ApplicationEventModel(
        email_application_id=app_figma.id,
        email_message_id="figma-msg-001",
        email_sender="recruiter@figma.com",
        email_sender_name="Figma People Team",
        email_subject="Figma Offer: Principal Platform Engineer 🎉",
        email_received_at=now - timedelta(hours=6),
        email_event_type="OFFER_RECEIVED",
        email_status_after_event="OFFER",
        email_summary="Official offer letter received ($285k Base + $140k/yr Equity).",
        email_action_required=True,
        email_action="Review offer documents and schedule decision call before Friday",
        email_raw_body="Alex, we are thrilled to extend an offer to join Figma as Principal Platform Engineer! Attached is your formal offer breakdown.",
    )
    session.add_all([event_figma_pre, event_figma_1])
    await session.flush()

    action_figma = ActionItemModel(
        application_id=app_figma.id,
        event_id=event_figma_1.id,
        title="Review Figma offer package details ($285k base + equity) and send questions",
        due_date=now + timedelta(days=4),
        status="PENDING",
        urgency="MEDIUM",
    )
    session.add(action_figma)

    # --- Company 4: Datadog (Status: ONLINE_ASSESSMENT) ---
    datadog_dossier = build_datadog_dossier()
    datadog = CompanyModel(
        name="Datadog", name_normalized="datadog", domain="datadoghq.com"
    )
    session.add(datadog)
    await session.flush()

    app_datadog = ApplicationModel(
        company_id=datadog.id,
        position="Senior Software Engineer - Distributed Tracing",
        position_normalized="senior software engineer - distributed tracing",
        external_job_id="datadog-apm-512",
        job_url="https://careers.datadoghq.com/detail/512",
        status="ONLINE_ASSESSMENT",
        application_date=now - timedelta(days=5),
        last_activity_at=now - timedelta(days=2),
        match_analysis_payload=datadog_dossier,
    )
    session.add(app_datadog)
    await session.flush()

    jp_datadog = JobPostingModel(
        application_id=app_datadog.id,
        job_url="https://careers.datadoghq.com/detail/512",
        description_markdown="""# Senior Software Engineer - Distributed Tracing

Datadog is looking for a Senior Software Engineer to build high-scale APM ingest pipelines.

### Requirements:
- Strong experience in Go, Python, or C++.
- Understanding of eBPF, OpenTelemetry, and Linux tracing internals.
- Deep focus on memory optimization, concurrency, and low latency processing.
""",
        salary_min=185000,
        salary_max=235000,
        currency="USD",
        location="New York, NY / Remote",
        work_model="Hybrid",
        required_skills=[
            "Go",
            "Python",
            "Observability",
            "Linux Internals",
            "OpenTelemetry",
        ],
    )
    session.add(jp_datadog)

    event_datadog_1 = ApplicationEventModel(
        email_application_id=app_datadog.id,
        email_message_id="datadog-msg-001",
        email_sender="recruiting@datadoghq.com",
        email_sender_name="Datadog Technical Recruitment",
        email_subject="Datadog Online Technical Assessment (90 min)",
        email_received_at=now - timedelta(days=2),
        email_event_type="ASSESSMENT_REQUEST",
        email_status_after_event="ONLINE_ASSESSMENT",
        email_summary="Received HackerRank automated coding & systems test link.",
        email_action_required=True,
        email_action="Complete HackerRank assessment by Thursday",
        email_raw_body="Hi Alex, please complete this 90-minute technical evaluation covering algorithmic problem solving and concurrent system design.",
    )
    session.add(event_datadog_1)
    await session.flush()

    action_datadog = ActionItemModel(
        application_id=app_datadog.id,
        event_id=event_datadog_1.id,
        title="Complete Datadog 90-minute online coding & systems assessment",
        due_date=now + timedelta(hours=36),
        status="PENDING",
        urgency="HIGH",
    )
    session.add(action_datadog)

    # --- Company 5: Airbnb (Status: REJECTED) ---
    airbnb_dossier = build_airbnb_dossier()
    airbnb = CompanyModel(name="Airbnb", name_normalized="airbnb", domain="airbnb.com")
    session.add(airbnb)
    await session.flush()

    app_airbnb = ApplicationModel(
        company_id=airbnb.id,
        position="Senior Platform Engineer",
        position_normalized="senior platform engineer",
        external_job_id="airbnb-plat-303",
        job_url="https://careers.airbnb.com/positions/303",
        status="REJECTED",
        application_date=now - timedelta(days=20),
        last_activity_at=now - timedelta(days=6),
        match_analysis_payload=airbnb_dossier,
    )
    session.add(app_airbnb)
    await session.flush()

    jp_airbnb = JobPostingModel(
        application_id=app_airbnb.id,
        job_url="https://careers.airbnb.com/positions/303",
        description_markdown="# Senior Platform Engineer\nBuilding Airbnb core developer infrastructure.",
        salary_min=190000,
        salary_max=240000,
        currency="USD",
        location="San Francisco, CA / Remote",
        work_model="Remote",
        required_skills=["Java", "Kubernetes", "AWS", "Terraform"],
    )
    session.add(jp_airbnb)

    event_airbnb_1 = ApplicationEventModel(
        email_application_id=app_airbnb.id,
        email_message_id="airbnb-msg-001",
        email_sender="talent@airbnb.com",
        email_sender_name="Airbnb Recruiting",
        email_subject="Your Application at Airbnb",
        email_received_at=now - timedelta(days=6),
        email_event_type="REJECTION",
        email_status_after_event="REJECTED",
        email_summary="Application not moving forward due to internal candidate placement.",
        email_action_required=False,
        email_raw_body="Hi Alex, thank you for your interest in Airbnb. At this time, we have decided to proceed with an internal candidate for this role.",
    )
    session.add(event_airbnb_1)
    await session.flush()

    action_airbnb = ActionItemModel(
        application_id=app_airbnb.id,
        event_id=event_airbnb_1.id,
        title="Archive application notes and reconnect with recruiter on LinkedIn",
        due_date=now - timedelta(days=5),
        status="COMPLETED",
        urgency="LOW",
    )
    session.add(action_airbnb)

    stats["companies"] = 5
    stats["applications"] = 5
    stats["job_postings"] = 5
    stats["application_events"] = 8
    stats["action_items"] = 5

    # -------------------------------------------------------------------------
    # 3. Other Recruitment & Tech Events
    # -------------------------------------------------------------------------
    other_1 = OtherEventModel(
        email_message_id="other-msg-001",
        email_sender="newsletter@bytebytego.com",
        email_sender_name="Alex Xu (ByteByteGo)",
        email_subject="ByteByteGo: Understanding Modern Distributed Consensus Protocols",
        email_received_at=now - timedelta(days=2),
        email_type="NEWSLETTER",
        company="ByteByteGo",
        summary="Engineering deep dive on Raft vs Paxos in modern cloud databases.",
        action_required=False,
        raw_body="In this week's issue, we break down how modern distributed databases implement Raft leader election...",
    )
    other_2 = OtherEventModel(
        email_message_id="other-msg-002",
        email_sender="recruiter@venturetalent.io",
        email_sender_name="Elena Rostova (Venture Talent)",
        email_subject="Founding Engineer Role at Series A AI Compute Startup",
        email_received_at=now - timedelta(days=3),
        email_type="RECRUITER_OUTREACH",
        company="Venture Talent",
        summary="Cold outreach for Founding Engineer role with 1.5% equity stake.",
        action_required=False,
        raw_body="Hi Alex, came across your distributed systems profile on GitHub. We are partnering with an early-stage AI compute company looking for a Founding Engineer...",
    )
    other_3 = OtherEventModel(
        email_message_id="other-msg-003",
        email_sender="aws-announcements@amazon.com",
        email_sender_name="AWS Architecture Community",
        email_subject="AWS Weekly: Scaling Event-Driven Microservices with Kafka & Aurora",
        email_received_at=now - timedelta(days=5),
        email_type="COMMUNITY",
        company="Amazon Web Services",
        summary="Architecture patterns for low-latency event processing in multi-region deployments.",
        action_required=False,
    )
    session.add_all([other_1, other_2, other_3])
    stats["other_events"] = 3

    # -------------------------------------------------------------------------
    # 4. Staging Queue Items (Ambiguous Leads for Triage)
    # -------------------------------------------------------------------------
    staging_1 = StagingItemModel(
        email_message_id="staging-msg-001",
        email_sender="founder@stealth-ai-infra.io",
        email_sender_name="Stealth AI Labs",
        email_subject="Intro: Distributed Systems Role at Stealth Seed Startup",
        email_received_at=now - timedelta(days=1),
        email_raw_body="Hi Alex, we are building a next-gen model serving runtime. Would love to have a casual 20m sync about our founding engineering role.",
        extracted_data={
            "company": "Stealth AI Labs",
            "position": "Founding Backend Engineer",
            "status": "INTERVIEW",
            "event_type": "RECRUITER_SCREEN",
            "summary": "Founder reached out for introductory call.",
        },
        match_score=0.45,
        match_reason="LOW_FUZZY_SCORE: Unregistered company domain",
        status="PENDING",
    )
    staging_2 = StagingItemModel(
        email_message_id="staging-msg-002",
        email_sender="careers@nexacorp-systems.com",
        email_sender_name="NexaCorp Recruiting",
        email_subject="Application Update: Principal Consultant",
        email_received_at=now - timedelta(hours=18),
        email_raw_body="Thank you for submitting your profile to NexaCorp. We are reviewing your technical background for multiple senior openings.",
        extracted_data={
            "company": "NexaCorp",
            "position": "Principal Consultant",
            "status": "APPLIED",
            "event_type": "APPLICATION_SUBMITTED",
            "summary": "Application update with multiple role possibilities.",
        },
        match_score=0.62,
        match_reason="MULTIPLE_COMPANY_MATCHES: Ambiguous company match against Nexa Global vs NexaCorp",
        status="PENDING",
    )
    staging_3 = StagingItemModel(
        email_message_id="staging-msg-003",
        email_sender="no-reply@greenhouse-mail.io",
        email_sender_name="Automated Career Portal",
        email_subject="Thank you for your application",
        email_received_at=now - timedelta(days=3),
        email_raw_body="We have received your application and will be in touch if your background aligns with our open positions.",
        extracted_data={
            "company": "Unknown Greenhouse Client",
            "position": "Software Engineer",
            "status": "APPLIED",
            "event_type": "APPLICATION_SUBMITTED",
            "summary": "Automated Greenhouse receipt without explicit company name.",
        },
        match_score=0.35,
        match_reason="UNSPECIFIED_ROLE: Missing company identifier in subject and body",
        status="PENDING",
    )
    session.add_all([staging_1, staging_2, staging_3])
    stats["staging_items"] = 3

    # -------------------------------------------------------------------------
    # 5. Intake Evaluation Tasks (Persisted AI Queue with Dossier Results)
    # -------------------------------------------------------------------------
    task_1 = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        job_url="https://stripe.com/jobs/senior-backend-payments",
        title_hint="Stripe - Senior Backend Engineer",
        status="COMPLETED",
        stage="COMPLETE",
        result_json=stripe_dossier,
        created_at=now - timedelta(days=4),
        completed_at=now - timedelta(days=4, minutes=-2),
    )
    task_2 = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        job_url="https://linear.app/careers/staff-systems-engineer",
        title_hint="Linear - Staff Systems & Sync Engineer",
        status="COMPLETED",
        stage="COMPLETE",
        result_json=linear_dossier,
        created_at=now - timedelta(days=12),
        completed_at=now - timedelta(days=12, minutes=-3),
    )
    task_3 = IntakeEvaluationTaskModel(
        task_type="JOB_ASSESSMENT",
        job_url="https://snowflake.com/careers/cloud-architect",
        title_hint="Snowflake - Principal Cloud Architect",
        status="PROCESSING",
        stage="ASSESSING",
        result_json=None,
        created_at=now - timedelta(minutes=5),
    )
    session.add_all([task_1, task_2, task_3])
    stats["intake_tasks"] = 3

    # -------------------------------------------------------------------------
    # 6. AI Providers & Task Bindings
    # -------------------------------------------------------------------------
    provider_openai = AIProviderModel(
        name="OpenAI (Default)",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        api_key=None,
        max_concurrency=4,
        is_active=True,
    )
    provider_anthropic = AIProviderModel(
        name="Anthropic (Claude 3.5 Sonnet)",
        provider_type="anthropic",
        base_url="https://api.anthropic.com/v1",
        api_key=None,
        max_concurrency=2,
        is_active=True,
    )
    provider_local = AIProviderModel(
        name="Local LM Studio / Ollama",
        provider_type="custom",
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        max_concurrency=1,
        is_active=False,
    )
    session.add_all([provider_openai, provider_anthropic, provider_local])
    await session.flush()

    binding_1 = AITaskBindingModel(
        task_type="JOB_ASSESSMENT",
        provider_id=provider_openai.id,
        model_name="gpt-4o",
        temperature=0.2,
        is_active=True,
    )
    binding_2 = AITaskBindingModel(
        task_type="EMAIL_EXTRACTION",
        provider_id=provider_openai.id,
        model_name="gpt-4o-mini",
        temperature=0.0,
        is_active=True,
    )
    binding_3 = AITaskBindingModel(
        task_type="INTERVIEW_GUIDE",
        provider_id=provider_anthropic.id,
        model_name="claude-3-5-sonnet-20241022",
        temperature=0.3,
        is_active=True,
    )
    session.add_all([binding_1, binding_2, binding_3])
    stats["ai_providers"] = 3
    stats["ai_task_bindings"] = 3

    # -------------------------------------------------------------------------
    # 7. Connected Email Accounts
    # -------------------------------------------------------------------------
    account_1 = EmailAccountModel(
        name="Personal Gmail (Recruitment)",
        auth_type="IMAP",
        imap_host="imap.gmail.com",
        imap_port=993,
        username="alex.morgan.dev@gmail.com",
        folder="INBOX",
        is_active=True,
        sync_interval="1h",
        last_synced_at=now - timedelta(hours=1),
    )
    account_2 = EmailAccountModel(
        name="Work Fastmail",
        auth_type="IMAP",
        imap_host="imap.fastmail.com",
        imap_port=993,
        username="alex@morgan-consulting.io",
        folder="INBOX",
        is_active=False,
        sync_interval="6h",
    )
    session.add_all([account_1, account_2])
    stats["email_accounts"] = 2

    # Commit all seeded data in a single clean transaction
    await session.commit()
    logger.info("Successfully seeded development dataset: %s", stats)
    return stats


async def maybe_seed_dev_data(session_factory) -> bool:
    """
    Checks if development seeding is enabled and database is empty.
    If both conditions are met, seeds the dataset.
    """
    is_dev = settings.SEED_DEV_DATA or settings.ENVIRONMENT.lower() in (
        "development",
        "dev",
    )
    if not is_dev:
        logger.debug(
            "Skipping dev seed: SEED_DEV_DATA is disabled and ENVIRONMENT != development"
        )
        return False

    async with session_factory() as session:
        empty = await is_database_empty(session)
        if not empty:
            logger.info("Database already contains data. Skipping initial mock seed.")
            return False

        logger.info(
            "🌱 Clean database detected in development mode. Populating mock test dataset..."
        )
        stats = await seed_development_dataset(session)
        print("\n" + "=" * 60)
        print(" 🌱 SEED DATA LOADED: Job Tracker Development Dataset Initialized")
        print(f"    - Companies:          {stats.get('companies', 0)}")
        print(f"    - Applications:       {stats.get('applications', 0)}")
        print(f"    - Job Postings:       {stats.get('job_postings', 0)}")
        print(f"    - Action Items:       {stats.get('action_items', 0)}")
        print(f"    - Timeline Events:    {stats.get('application_events', 0)}")
        print(f"    - Staging Queue:      {stats.get('staging_items', 0)}")
        print(f"    - AI Queue Tasks:     {stats.get('intake_tasks', 0)}")
        print(f"    - AI Providers:       {stats.get('ai_providers', 0)}")
        print(f"    - Email Accounts:     {stats.get('email_accounts', 0)}")
        print("=" * 60 + "\n")
        return True
