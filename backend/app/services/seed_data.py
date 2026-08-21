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


def build_dossier(
    company: str,
    position: str,
    fit_score: int,
    prog_score: int,
    fit_tier: str,
    summary_text: str,
    matching_skills: list[str],
    missing_skills: list[str],
    sal_min: float,
    sal_max: float,
    location: str,
    work_model: str,
    recommendation: str,
) -> dict:
    return {
        "company": company,
        "position": position,
        "fit_score": fit_score,
        "programmatic_match_score": prog_score,
        "fit_tier": fit_tier,
        "match_summary": summary_text,
        "hard_matches": {
            "keyword_match_rate": f"{len(matching_skills)}/{len(matching_skills) + len(missing_skills)} core skills found",
            "top_alignment": matching_skills[:3],
        },
        "optimization_gaps": {
            "missing_completely": missing_skills,
            "vocabulary_mismatches": [
                f"Vocabulary alignment recommended for {missing_skills[0]}"
            ]
            if missing_skills
            else [],
            "experience_mismatch": None,
        },
        "tailoring_strategy": {
            "vocabulary_translation": [
                {
                    "jd_term": f"{skill} Infrastructure",
                    "cv_term": f"{skill} Integration",
                    "replacement_guidance": f"Explicitly highlight production scale with {skill}.",
                }
                for skill in matching_skills[:2]
            ],
            "impact_reframing": [
                {
                    "bullet_point": f"Engineered scalable services for {company}.",
                    "suggested_rewrite": f"Architected high-throughput microservices for {company} handling 20,000 req/sec with 99.99% reliability.",
                    "reason": "Quantifies impact and aligns with senior backend requirements.",
                }
            ],
            "structural_adjustments": [
                "Elevate core distributed systems competencies to the summary section.",
            ],
        },
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "pros": [
            f"Competitive compensation range (${int(sal_min):,}-${int(sal_max):,})",
            "Strong technical engineering culture and autonomy",
        ],
        "cons": [
            "High throughput operational SLA expectations",
        ],
        "salary_min": sal_min,
        "salary_max": sal_max,
        "currency": "USD",
        "location": location,
        "work_model": work_model,
        "recommendation": recommendation,
        "summary": summary_text,
    }


def build_structured_spec(
    company: str,
    domain: str,
    position: str,
    why_hiring: str,
    what_you_will_build: str,
    responsibilities: list[str],
    requirements: list[str],
    extracted_skills: list[str],
    comp_text: str,
    location_text: str,
    workplace_type: str,
) -> dict:
    return {
        "job_found": True,
        "company": company,
        "company_url": domain,
        "position": position,
        "why_hiring": why_hiring,
        "what_you_will_build": what_you_will_build,
        "responsibilities": responsibilities,
        "requirements": requirements,
        "extracted_skills": extracted_skills,
        "compensation_text": comp_text,
        "location_text": location_text,
        "workplace_type": workplace_type,
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
    Populates a rich, 90-day rolling development test dataset following the rules in `guide.md`:
    - Entity relationship hierarchy order (CV & Company -> Application -> JobPosting -> Events -> Action Items)
    - 90-day rolling window timestamps (Current Period 0-14d, Previous Period 15-30d, Historical 31-90d)
    - Realistic status ratios: ~40% Applied/In-Progress, ~15% Assessment, ~20% Interview, ~10% Offer/Hired, ~15% Rejected/Archived
    - Full structured_spec and match_analysis_payload JSONB specifications
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
    # 2. Companies & Applications (25 Companies spanning rolling 90-day window)
    # -------------------------------------------------------------------------

    # Define 25 companies spanning the 90-day historical window with status distribution ratios
    company_seed_specs = [
        # --- Days 0-14 (Current Period: ~35% of apps) ---
        {
            "name": "Stripe",
            "domain": "stripe.com",
            "pos": "Senior Backend Engineer - Global Payments",
            "status": "APPLIED",
            "days_ago": 2,
            "sal_min": 195000,
            "sal_max": 245000,
            "work_model": "Remote",
            "fit_score": 94,
            "prog_score": 90,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Kafka", "Redis"],
            "missing": ["ISO 20022"],
            "has_action": True,
            "action_title": "Book 30-minute intro call via Calendly link",
            "action_urgency": "HIGH",
            "action_due_days": 2,
        },
        {
            "name": "Datadog",
            "domain": "datadoghq.com",
            "pos": "Senior Software Engineer - Distributed Tracing",
            "status": "ONLINE_ASSESSMENT",
            "days_ago": 4,
            "sal_min": 185000,
            "sal_max": 235000,
            "work_model": "Hybrid",
            "fit_score": 84,
            "prog_score": 82,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Go", "Python", "eBPF", "OpenTelemetry", "Linux Internals"],
            "missing": ["eBPF"],
            "has_action": True,
            "action_title": "Complete Datadog 90-minute online coding & systems assessment",
            "action_urgency": "HIGH",
            "action_due_days": 1,
        },
        {
            "name": "Linear",
            "domain": "linear.app",
            "pos": "Staff Systems & Sync Engineer",
            "status": "TECHNICAL_INTERVIEW",
            "days_ago": 6,
            "sal_min": 210000,
            "sal_max": 275000,
            "work_model": "Remote",
            "fit_score": 89,
            "prog_score": 85,
            "fit_tier": "STRONG_MATCH",
            "skills": ["TypeScript", "PostgreSQL", "Real-time Sync", "Redis", "CRDTs"],
            "missing": ["CRDTs"],
            "has_action": True,
            "action_title": "Prepare system design diagrams for Linear sync architecture round",
            "action_urgency": "HIGH",
            "action_due_days": 2,
            "has_guide": True,
        },
        {
            "name": "Figma",
            "domain": "figma.com",
            "pos": "Principal Platform Engineer",
            "status": "OFFER",
            "days_ago": 8,
            "sal_min": 240000,
            "sal_max": 310000,
            "work_model": "Hybrid",
            "fit_score": 86,
            "prog_score": 80,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Rust", "Go", "Kubernetes", "WebAssembly", "C++"],
            "missing": ["C++ Canvas Engine Rendering"],
            "has_action": True,
            "action_title": "Review Figma offer package details ($285k base + equity) and send questions",
            "action_urgency": "MEDIUM",
            "action_due_days": 4,
        },
        {
            "name": "Vercel",
            "domain": "vercel.com",
            "pos": "Staff Edge Infrastructure Engineer",
            "status": "APPLIED",
            "days_ago": 9,
            "sal_min": 200000,
            "sal_max": 260000,
            "work_model": "Remote",
            "fit_score": 91,
            "prog_score": 88,
            "fit_tier": "STRONG_MATCH",
            "skills": ["TypeScript", "Go", "WebAssembly", "Edge Compute", "Redis"],
            "missing": ["Rust WASM Compiler Tools"],
            "has_action": False,
        },
        {
            "name": "Supabase",
            "domain": "supabase.com",
            "pos": "Senior PostgreSQL Platform Engineer",
            "status": "TECHNICAL_INTERVIEW",
            "days_ago": 11,
            "sal_min": 190000,
            "sal_max": 240000,
            "work_model": "Remote",
            "fit_score": 93,
            "prog_score": 90,
            "fit_tier": "STRONG_MATCH",
            "skills": ["PostgreSQL", "Go", "Distributed Systems", "Elixir"],
            "missing": ["Elixir / Erlang VM"],
            "has_action": False,
        },
        {
            "name": "Resend",
            "domain": "resend.com",
            "pos": "Senior Infrastructure & Email Engine Specialist",
            "status": "APPLIED",
            "days_ago": 13,
            "sal_min": 175000,
            "sal_max": 225000,
            "work_model": "Remote",
            "fit_score": 87,
            "prog_score": 84,
            "fit_tier": "STRONG_MATCH",
            "skills": ["TypeScript", "Node.js", "PostgreSQL", "SMTP Protocols"],
            "missing": ["DKIM / SPF Deliverability Tuning"],
            "has_action": False,
        },
        {
            "name": "PostHog",
            "domain": "posthog.com",
            "pos": "Senior Analytics Ingestion Engineer",
            "status": "ONLINE_ASSESSMENT",
            "days_ago": 14,
            "sal_min": 180000,
            "sal_max": 230000,
            "work_model": "Remote",
            "fit_score": 88,
            "prog_score": 85,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "ClickHouse", "Kafka", "Django"],
            "missing": ["ClickHouse Internal Sharding"],
            "has_action": False,
        },
        # --- Days 15-30 (Previous Period: ~30% of apps) ---
        {
            "name": "Snowflake",
            "domain": "snowflake.com",
            "pos": "Principal Cloud Database Architect",
            "status": "APPLIED",
            "days_ago": 16,
            "sal_min": 220000,
            "sal_max": 280000,
            "work_model": "Hybrid",
            "fit_score": 82,
            "prog_score": 78,
            "fit_tier": "STRONG_MATCH",
            "skills": ["C++", "Java", "Distributed Query Engines", "AWS"],
            "missing": ["Java Virtual Machine Optimization"],
            "has_action": False,
        },
        {
            "name": "Airbnb",
            "domain": "airbnb.com",
            "pos": "Senior Platform Engineer",
            "status": "REJECTED",
            "days_ago": 18,
            "sal_min": 190000,
            "sal_max": 240000,
            "work_model": "Remote",
            "fit_score": 78,
            "prog_score": 75,
            "fit_tier": "MODERATE_MATCH",
            "skills": ["Java", "Kubernetes", "AWS", "Spring Boot"],
            "missing": ["Java", "Spring Boot"],
            "has_action": False,
        },
        {
            "name": "Cloudflare",
            "domain": "cloudflare.com",
            "pos": "Staff Network & Distributed Edge Engineer",
            "status": "TECHNICAL_INTERVIEW",
            "days_ago": 21,
            "sal_min": 210000,
            "sal_max": 270000,
            "work_model": "Hybrid",
            "fit_score": 85,
            "prog_score": 82,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Rust", "Go", "BGP Protocols", "Linux Kernel"],
            "missing": ["Linux Kernel eBPF"],
            "has_action": False,
        },
        {
            "name": "Retool",
            "domain": "retool.com",
            "pos": "Senior Full-Stack Backend Lead",
            "status": "APPLIED",
            "days_ago": 23,
            "sal_min": 185000,
            "sal_max": 235000,
            "work_model": "Hybrid",
            "fit_score": 88,
            "prog_score": 86,
            "fit_tier": "STRONG_MATCH",
            "skills": ["TypeScript", "Node.js", "PostgreSQL", "React"],
            "missing": [],
            "has_action": False,
        },
        {
            "name": "Modal",
            "domain": "modal.com",
            "pos": "Systems Engineer - Serverless GPU Runtime",
            "status": "ONLINE_ASSESSMENT",
            "days_ago": 25,
            "sal_min": 210000,
            "sal_max": 280000,
            "work_model": "Remote",
            "fit_score": 90,
            "prog_score": 88,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "Rust", "Linux Containers", "CUDA"],
            "missing": ["CUDA Driver Kernels"],
            "has_action": False,
        },
        {
            "name": "Sentry",
            "domain": "sentry.io",
            "pos": "Senior Python Backend Systems Engineer",
            "status": "HIRED",
            "days_ago": 28,
            "sal_min": 190000,
            "sal_max": 240000,
            "work_model": "Remote",
            "fit_score": 95,
            "prog_score": 92,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "Django", "ClickHouse", "PostgreSQL", "Kafka"],
            "missing": [],
            "has_action": False,
        },
        {
            "name": "Pinecone",
            "domain": "pinecone.io",
            "pos": "Senior Vector Indexing Engineer",
            "status": "APPLIED",
            "days_ago": 30,
            "sal_min": 195000,
            "sal_max": 250000,
            "work_model": "Remote",
            "fit_score": 84,
            "prog_score": 80,
            "fit_tier": "STRONG_MATCH",
            "skills": ["C++", "Go", "HNSW Algorithms", "Distributed Vector Search"],
            "missing": ["SIMD Acceleration"],
            "has_action": False,
        },
        # --- Days 31-90 (Historical Cohorts: ~35% of apps) ---
        {
            "name": "Weights & Biases",
            "domain": "wandb.ai",
            "pos": "Senior MLOps Platform Engineer",
            "status": "APPLIED",
            "days_ago": 35,
            "sal_min": 185000,
            "sal_max": 235000,
            "work_model": "Remote",
            "fit_score": 83,
            "prog_score": 80,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "Kubernetes", "AWS", "PyTorch"],
            "missing": ["PyTorch Distributed Training"],
            "has_action": False,
        },
        {
            "name": "Chroma",
            "domain": "trychroma.com",
            "pos": "Distributed Database Engineer",
            "status": "REJECTED",
            "days_ago": 42,
            "sal_min": 180000,
            "sal_max": 230000,
            "work_model": "Remote",
            "fit_score": 79,
            "prog_score": 76,
            "fit_tier": "MODERATE_MATCH",
            "skills": ["Python", "Rust", "SQLite", "Vector Embeddings"],
            "missing": ["Rust Internal Memory Safety"],
            "has_action": False,
        },
        {
            "name": "LangChain",
            "domain": "langchain.com",
            "pos": "Staff Agent Frameworks Engineer",
            "status": "TECHNICAL_INTERVIEW",
            "days_ago": 48,
            "sal_min": 195000,
            "sal_max": 255000,
            "work_model": "Remote",
            "fit_score": 92,
            "prog_score": 89,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "TypeScript", "LangGraph", "AsyncIO", "LLM APIs"],
            "missing": [],
            "has_action": False,
        },
        {
            "name": "Scale AI",
            "domain": "scale.com",
            "pos": "Senior Data Engine Infrastructure Engineer",
            "status": "APPLIED",
            "days_ago": 54,
            "sal_min": 200000,
            "sal_max": 260000,
            "work_model": "Hybrid",
            "fit_score": 86,
            "prog_score": 82,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Python", "PostgreSQL", "Kafka", "Kubernetes"],
            "missing": [],
            "has_action": False,
        },
        {
            "name": "Astral",
            "domain": "astral.sh",
            "pos": "Systems Engineer - Python Tooling in Rust",
            "status": "ONLINE_ASSESSMENT",
            "days_ago": 60,
            "sal_min": 190000,
            "sal_max": 250000,
            "work_model": "Remote",
            "fit_score": 81,
            "prog_score": 78,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Rust", "Python ASTs", "Compiler Design"],
            "missing": ["Compiler AST Parsing"],
            "has_action": False,
        },
        {
            "name": "ClickHouse",
            "domain": "clickhouse.com",
            "pos": "Principal Columnar Engine Engineer",
            "status": "ARCHIVED",
            "days_ago": 68,
            "sal_min": 220000,
            "sal_max": 290000,
            "work_model": "Remote",
            "fit_score": 75,
            "prog_score": 72,
            "fit_tier": "MODERATE_MATCH",
            "skills": ["C++", "Columnar Storage", "SIMD"],
            "missing": ["C++20 SIMD Primitives"],
            "has_action": False,
        },
        {
            "name": "Cockroach Labs",
            "domain": "cockroachlabs.com",
            "pos": "Distributed Consensus Engineer",
            "status": "APPLIED",
            "days_ago": 75,
            "sal_min": 200000,
            "sal_max": 260000,
            "work_model": "Remote",
            "fit_score": 88,
            "prog_score": 85,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Go", "Raft Consensus", "Distributed SQL"],
            "missing": [],
            "has_action": False,
        },
        {
            "name": "Tailscale",
            "domain": "tailscale.com",
            "pos": "Senior Networking Software Engineer",
            "status": "APPLIED",
            "days_ago": 81,
            "sal_min": 185000,
            "sal_max": 240000,
            "work_model": "Remote",
            "fit_score": 87,
            "prog_score": 84,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Go", "WireGuard Protocols", "Networking"],
            "missing": ["WireGuard Kernel Routing"],
            "has_action": False,
        },
        {
            "name": "PlanetScale",
            "domain": "planetscale.com",
            "pos": "Senior Vitess Database Engineer",
            "status": "REJECTED",
            "days_ago": 86,
            "sal_min": 190000,
            "sal_max": 245000,
            "work_model": "Remote",
            "fit_score": 76,
            "prog_score": 73,
            "fit_tier": "MODERATE_MATCH",
            "skills": ["Go", "MySQL Internals", "Vitess Sharding"],
            "missing": ["MySQL Storage Engine Internals"],
            "has_action": False,
        },
        {
            "name": "Fly.io",
            "domain": "fly.io",
            "pos": "Staff MicroVM Runtime Engineer",
            "status": "APPLIED",
            "days_ago": 89,
            "sal_min": 205000,
            "sal_max": 265000,
            "work_model": "Remote",
            "fit_score": 89,
            "prog_score": 86,
            "fit_tier": "STRONG_MATCH",
            "skills": ["Go", "Rust", "Firecracker MicroVMs", "Linux Kernel"],
            "missing": [],
            "has_action": False,
        },
    ]

    total_companies = len(company_seed_specs)
    total_apps = len(company_seed_specs)
    total_job_postings = len(company_seed_specs)
    total_events = 0
    total_actions = 0
    total_tasks = 0

    for spec in company_seed_specs:
        app_date = now - timedelta(days=spec["days_ago"])

        # 2a. Company Model
        company = CompanyModel(
            name=spec["name"],
            name_normalized=spec["name"].lower(),
            domain=spec["domain"],
        )
        session.add(company)
        await session.flush()

        # Build Match Analysis Dossier Payload
        dossier = build_dossier(
            company=spec["name"],
            position=spec["pos"],
            fit_score=spec["fit_score"],
            prog_score=spec["prog_score"],
            fit_tier=spec["fit_tier"],
            summary_text=f"Match evaluation for {spec['pos']} at {spec['name']}.",
            matching_skills=spec["skills"],
            missing_skills=spec["missing"],
            sal_min=float(spec["sal_min"]),
            sal_max=float(spec["sal_max"]),
            location=f"{spec['work_model']} (US / Europe)",
            work_model=spec["work_model"],
            recommendation="APPLY_STRONGLY" if spec["fit_score"] >= 85 else "APPLY",
        )

        # 2b. Application Model
        guide_html = None
        if spec.get("has_guide"):
            guide_html = (
                f"<div class='interview-guide-container'><h2>{spec['name']} Technical Architecture Guide</h2>"
                f"<p>System design and architecture preparation for {spec['pos']}.</p></div>"
            )

        app = ApplicationModel(
            company_id=company.id,
            position=spec["pos"],
            position_normalized=spec["pos"].lower(),
            external_job_id=f"{company.name_normalized}-job-{spec['days_ago']}",
            job_url=f"https://{spec['domain']}/careers/{company.name_normalized}",
            status=spec["status"],
            application_date=app_date,
            last_activity_at=app_date + timedelta(hours=12),
            interview_guide_html=guide_html,
            interview_guide_generated_at=app_date + timedelta(hours=10)
            if guide_html
            else None,
            match_analysis_payload=dossier,
        )
        session.add(app)
        await session.flush()

        # 2c. Job Posting Model
        structured_spec = build_structured_spec(
            company=spec["name"],
            domain=spec["domain"],
            position=spec["pos"],
            why_hiring=f"Expanding core engineering team at {spec['name']}.",
            what_you_will_build=f"High performance systems for {spec['pos']}.",
            responsibilities=[
                f"Design and maintain scalable microservices for {spec['name']}.",
                "Optimize query performance and database transactional consistency.",
            ],
            requirements=[
                "5+ years backend software engineering experience.",
                "Expertise in distributed systems, SQL, and event streaming.",
            ],
            extracted_skills=spec["skills"],
            comp_text=f"${spec['sal_min']:,} - ${spec['sal_max']:,} USD",
            location_text=spec["work_model"],
            workplace_type=spec["work_model"],
        )

        jp = JobPostingModel(
            application_id=app.id,
            job_url=f"https://{spec['domain']}/careers/{company.name_normalized}",
            description_markdown=f"# {spec['pos']}\n\nJoin {spec['name']} to build scalable backend systems.",
            salary_min=float(spec["sal_min"]),
            salary_max=float(spec["sal_max"]),
            currency="USD",
            location=spec["work_model"],
            work_model=spec["work_model"],
            required_skills=spec["skills"],
            structured_spec=structured_spec,
        )
        session.add(jp)

        # 2d. Application Events
        evt1 = ApplicationEventModel(
            email_application_id=app.id,
            email_message_id=f"msg-{app.id}-sub",
            email_sender=f"recruiting@{spec['domain']}",
            email_sender_name=f"{spec['name']} Talent Team",
            email_subject=f"Application Confirmation: {spec['pos']}",
            email_received_at=app_date,
            email_event_type="APPLICATION_SUBMITTED",
            email_status_after_event="APPLIED",
            email_summary=f"Application for {spec['pos']} received.",
            email_action_required=False,
            email_raw_body=f"Hi Alex, thank you for applying to {spec['name']}!",
        )
        session.add(evt1)
        total_events += 1

        if spec["status"] in [
            "ONLINE_ASSESSMENT",
            "TECHNICAL_INTERVIEW",
            "OFFER",
            "REJECTED",
        ]:
            evt_type_map = {
                "ONLINE_ASSESSMENT": "ASSESSMENT_REQUEST",
                "TECHNICAL_INTERVIEW": "INTERVIEW_INVITE",
                "OFFER": "OFFER_RECEIVED",
                "REJECTED": "REJECTION",
            }
            evt2 = ApplicationEventModel(
                email_application_id=app.id,
                email_message_id=f"msg-{app.id}-status",
                email_sender=f"recruiting@{spec['domain']}",
                email_sender_name=f"{spec['name']} Recruiting",
                email_subject=f"Update regarding your application at {spec['name']}",
                email_received_at=app_date + timedelta(days=1),
                email_event_type=evt_type_map[spec["status"]],
                email_status_after_event=spec["status"],
                email_summary=f"Status update: moved to {spec['status']}.",
                email_action_required=spec.get("has_action", False),
                email_action=spec.get("action_title")
                if spec.get("has_action")
                else None,
            )
            session.add(evt2)
            await session.flush()
            total_events += 1

            # 2e. Action Item
            if spec.get("has_action"):
                action = ActionItemModel(
                    application_id=app.id,
                    event_id=evt2.id,
                    title=spec["action_title"],
                    due_date=now + timedelta(days=spec.get("action_due_days", 2)),
                    status="PENDING",
                    urgency=spec.get("action_urgency", "MEDIUM"),
                )
                session.add(action)
                total_actions += 1

        # 2f. Intake Evaluation Task
        task = IntakeEvaluationTaskModel(
            task_type="JOB_ASSESSMENT",
            job_url=f"https://{spec['domain']}/careers/{company.name_normalized}",
            title_hint=f"{spec['name']} - {spec['pos']}",
            status="COMPLETED",
            stage="COMPLETE",
            result_json=dossier,
            created_at=app_date,
            completed_at=app_date + timedelta(minutes=2),
        )
        session.add(task)
        total_tasks += 1

    stats["companies"] = total_companies
    stats["applications"] = total_apps
    stats["job_postings"] = total_job_postings
    stats["application_events"] = total_events
    stats["action_items"] = total_actions
    stats["intake_tasks"] = total_tasks

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
    # 5. AI Providers & Task Bindings (Local LM Studio Default)
    # -------------------------------------------------------------------------
    provider_local = AIProviderModel(
        name="Local LM studio",
        provider_type="openai",
        base_url="http://192.168.1.187:1234/v1",
        api_key="",
        max_concurrency=1,
        is_active=True,
    )
    session.add(provider_local)
    await session.flush()

    binding_global = AITaskBindingModel(
        task_type="GLOBAL_DEFAULT",
        provider_id=provider_local.id,
        model_name="qwen/qwen3.5-9b",
        temperature=0.2,
        is_active=True,
    )
    binding_1 = AITaskBindingModel(
        task_type="JOB_ASSESSMENT",
        provider_id=provider_local.id,
        model_name="qwen/qwen3.5-9b",
        temperature=0.2,
        is_active=True,
    )
    binding_2 = AITaskBindingModel(
        task_type="EMAIL_EXTRACTION",
        provider_id=provider_local.id,
        model_name="qwen/qwen3.5-9b",
        temperature=0.0,
        is_active=True,
    )
    binding_3 = AITaskBindingModel(
        task_type="INTERVIEW_GUIDE",
        provider_id=provider_local.id,
        model_name="qwen/qwen3.5-9b",
        temperature=0.3,
        is_active=True,
    )
    binding_4 = AITaskBindingModel(
        task_type="JD_EXTRACTION",
        provider_id=provider_local.id,
        model_name="qwen/qwen3.5-9b",
        temperature=0.0,
        is_active=True,
    )
    binding_5 = AITaskBindingModel(
        task_type="COVER_LETTER",
        provider_id=provider_local.id,
        model_name="qwen/qwen3.5-9b",
        temperature=0.3,
        is_active=True,
    )
    session.add_all(
        [binding_global, binding_1, binding_2, binding_3, binding_4, binding_5]
    )
    stats["ai_providers"] = 1
    stats["ai_task_bindings"] = 6

    # -------------------------------------------------------------------------
    # 6. Connected Email Accounts
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
    logger.info("Successfully seeded 90-day rolling development dataset: %s", stats)
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
            "🌱 Clean database detected in development mode. Populating 90-day rolling test dataset..."
        )
        stats = await seed_development_dataset(session)
        print("\n" + "=" * 60)
        print(" 🌱 SEED DATA LOADED: Job Tracker 90-Day Rolling Dataset Initialized")
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
