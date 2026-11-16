"""Scrubbed multi-pipeline golden evaluation scenarios (JD extraction, Assessment, Email extraction, Cover Letter, Q&A).

Prompts and expectations are calibrated against redacted real-world postings and candidate profile shapes
without containing any PII or proprietary company identifiers.
"""

from __future__ import annotations

from typing import Any

GOLDEN_CV_TEXT = """
Senior Backend & AI Platform Engineer — 8 years of experience.
Spoken Languages: English (Fluent), Portuguese (Native).
Summary:
Built distributed backend services, LLM orchestration workflows, asynchronous task queues, and multi-tenant APIs.

Experience:
- Senior Backend & AI Engineer, Horizon Cloud Systems (2022–Present):
  Architected FastAPI microservices, LangGraph/LangChain agent workflows, pgvector semantic search,
  and PostgreSQL + Redis distributed pipelines processing 40M+ daily events. Deployed on Kubernetes with GitHub Actions CI.
- Software Engineer, Atlas Telemetry Corp (2019–2022):
  Implemented Python/Go ingestion APIs, GraphQL endpoints, TypeScript dashboards, and OpenAI API evaluation tooling.
- Backend Engineer, Northstar Data (2017–2019):
  Designed Django + PostgreSQL financial ledgers and Celery background workers.

Skills: Python, FastAPI, Django, Go, TypeScript, PostgreSQL, pgvector, Redis, Kubernetes, OpenAI API, LangChain, LangGraph, GraphQL, GitHub Actions, PyTorch.
""".strip()

GOLDEN_CV_SKILLS = [
    "Python",
    "FastAPI",
    "Django",
    "Go",
    "TypeScript",
    "PostgreSQL",
    "pgvector",
    "Redis",
    "Kubernetes",
    "OpenAI API",
    "LangChain",
    "LangGraph",
    "GraphQL",
    "GitHub Actions",
    "PyTorch",
]


GOLDEN_PIPELINE_SCENARIOS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------
    # 1. JD Extraction
    # ------------------------------------------------------------------
    {
        "id": "jd_structured_backend_comp",
        "pipeline": "jd_extraction",
        "title_hint": "Senior Python & AI Engineer",
        "page_title": "Senior Python & AI Engineer - Orbital Systems",
        "raw_webpage_data": """
Home | Careers | Privacy Policy | Accept All Cookies
Orbital Systems — Engineering Careers
Role: Senior Python & AI Engineer (Remote - Europe / US East)
Compensation: $150,000 - $180,000 USD per year + equity.

About the Team:
We build resilient APIs and retrieval-augmented LLM pipelines.

Responsibilities:
- Design and scale FastAPI microservices backed by PostgreSQL and Redis.
- Build reliable multi-step LangGraph and OpenAI API agent evaluation pipelines.
- Improve observability, latency SLAs, and Kubernetes deployment automation.

Requirements:
- 5+ years of production Python experience (FastAPI or Django).
- Hands-on experience with PostgreSQL, Redis, and Kubernetes.
- Prior work integrating OpenAI API or open-weights LLM inference.
""",
        "expect_job_found": True,
        "required_skills_any": ["Python", "FastAPI", "PostgreSQL", "Redis"],
        "expected_salary_min": 150000,
        "expected_salary_max": 180000,
        "must_be_null_if_unstated": ["why_hiring"],
    },
    {
        "id": "jd_non_job_cookie_junk",
        "pipeline": "jd_extraction",
        "title_hint": None,
        "page_title": "Privacy Preferences - Example Portal",
        "raw_webpage_data": """
We value your privacy. Choose which cookies to allow: Strictly Necessary, Analytics, Marketing.
Sign in to view your saved preferences. Copyright 2026 Example Portal Inc.
Contact support at [EMAIL] or view Terms of Service and Cookie Policy.
""",
        "expect_job_found": False,
        "required_skills_any": [],
    },
    # ------------------------------------------------------------------
    # 2. Job Assessment (calibrated against real DB fit bands)
    # ------------------------------------------------------------------
    {
        "id": "assess_high_fit_python_ai",
        "pipeline": "assessment",
        "job_description": """
Senior AI & Backend Platform Engineer (Remote - English)
Build the core data model, API platform, and agentic orchestration layer.
Responsibilities:
- Architect FastAPI and Go services backed by PostgreSQL, pgvector, and Redis.
- Build and evaluate multi-step LLM agent pipelines using LangGraph and OpenAI API.
- Run containerized services on Kubernetes with GitHub Actions CI/CD.
Requirements:
- 5+ years Python (FastAPI/Django) plus experience with Go or TypeScript.
- Strong PostgreSQL and Redis fundamentals.
- Proven production work with LLM workflows (LangChain/LangGraph) and Kubernetes.
Fluent English required.
""",
        "candidate_cv": GOLDEN_CV_TEXT,
        "candidate_skills": GOLDEN_CV_SKILLS,
        "candidate_years_of_experience": 8.0,
        "programmatic_baseline": 86,
        "matching_skills": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Redis",
            "Kubernetes",
            "LangGraph",
        ],
        "missing_skills": [],
        "min_score": 72,
        "max_score": 100,
        "allowed_recommendations": [
            "APPLY_STRONGLY",
            "APPLY_MODERATELY",
            "APPLY",
            "MUST_APPLY",
        ],
        "ban_pseudo_risks": True,
    },
    {
        "id": "assess_stretch_presales_architect",
        "pipeline": "assessment",
        "job_description": """
Tabular AI Solutions Architect (Remote)
Be our first Technical Pre-Sales Solutions Architect working alongside Enterprise Account Executives.
Responsibilities:
- Lead technical discovery calls with enterprise CTOs, scope proofs-of-concept, and close deals.
- Guide customer data science teams on tabular modeling with scikit-learn, XGBoost, and Gradient Boosting.
- Build Spark and Snowflake feature engineering demos with sales engineers.
Requirements:
- 5+ years in customer-facing Pre-Sales / Solutions Architecture alongside enterprise sales teams.
- Deep production expertise in scikit-learn, Gradient Boosting, LightGBM, and XGBoost.
- Fluent English required.
""",
        "candidate_cv": GOLDEN_CV_TEXT,
        "candidate_skills": GOLDEN_CV_SKILLS,
        "candidate_years_of_experience": 8.0,
        "programmatic_baseline": 38,
        "matching_skills": ["Python"],
        "missing_skills": [
            "scikit-learn",
            "Gradient Boosting",
            "Pre-Sales / Solutions Architecture",
        ],
        "min_score": 20,
        "max_score": 74,
        "allowed_recommendations": [
            "STRETCH_ROLE",
            "DO_NOT_APPLY",
            "CAUTION",
            "SKIP",
            "APPLY_MODERATELY",
        ],
        "expect_gap_terms_any": [
            "pre-sales",
            "solutions architect",
            "scikit-learn",
            "gradient boosting",
            "xgboost",
        ],
        "ban_pseudo_risks": True,
    },
    {
        "id": "assess_low_fit_android_kotlin",
        "pipeline": "assessment",
        "job_description": """
Senior Android Mobile Engineer - Consumer App
We are hiring a native Android engineer to build flagship mobile experiences.
Requirements:
- 6+ years building native Android applications using Kotlin, Jetpack Compose, and Android SDK.
- Deep knowledge of Coroutines, Flow, Room, Dagger/Hilt, Gradle, and Play Store release pipelines.
- Experience debugging ANRs, battery profiling, and Kotlin Multiplatform.
""",
        "candidate_cv": GOLDEN_CV_TEXT,
        "candidate_skills": GOLDEN_CV_SKILLS,
        "candidate_years_of_experience": 8.0,
        "programmatic_baseline": 10,
        "matching_skills": [],
        "missing_skills": ["Kotlin", "Jetpack Compose", "Android SDK", "Gradle"],
        "min_score": 0,
        "max_score": 52,
        "allowed_recommendations": ["DO_NOT_APPLY", "SKIP", "CAUTION", "STRETCH_ROLE"],
        "ban_pseudo_risks": True,
    },
    # ------------------------------------------------------------------
    # 3. Email Extraction
    # ------------------------------------------------------------------
    {
        "id": "email_interview_invite_with_deadline",
        "pipeline": "email_extraction",
        "sender": "recruiting@orbital-systems.example",
        "subject": "Next Step: Technical Interview & Take-Home Exercise - Senior Python Engineer",
        "date": "2026-11-12T10:30:00Z",
        "email_content": """
Hi Candidate,

Thank you for speaking with our recruiter. The hiring team at Orbital Systems would like to advance you to the Technical Interview stage for the Senior Python Engineer role (Req #REQ-4821).

Could you complete the short backend debugging assignment by Friday, November 20, 2026?
Also, please let us know if you are available for a 45-minute technical interview on Tuesday, November 17 at 14:00 UTC or Wednesday, November 18 at 16:00 UTC.

Best regards,
[PERSON]
""",
        "expect_company": "Orbital Systems",
        "expect_action_required": True,
        "expect_non_empty_fields": [
            "status_evidence",
            "deadline_evidence",
            "meeting_proposal",
        ],
        "expect_null_fields": ["due_date"],
    },
    {
        "id": "email_generic_acknowledgment",
        "pipeline": "email_extraction",
        "sender": "no-reply@ats.orbital-systems.example",
        "subject": "Application Received: Staff Backend Engineer",
        "date": "2026-11-12T08:00:00Z",
        "email_content": """
Hello,

This automated message confirms we received your application for the Staff Backend Engineer position at Horizon Cloud.
Our recruiting team reviews every submission and will reach out if there is a strong match. No further action is needed from you at this time.
""",
        "expect_action_required": False,
        "expect_null_fields": ["due_date", "deadline_evidence"],
    },
    # ------------------------------------------------------------------
    # 4. Cover Letter Grounding & Application Q&A
    # ------------------------------------------------------------------
    {
        "id": "cover_letter_strict_grounding",
        "pipeline": "cover_letter",
        "company_name": "Orbital Systems",
        "position": "Senior Backend Engineer",
        "job_description": """
We are looking for a Senior Backend Engineer experienced with Python, FastAPI, PostgreSQL, and Redis.
Bonus skills (nice to have): Rust, Elixir.
""",
        "candidate_cv": GOLDEN_CV_TEXT,
        "must_include_any": ["FastAPI", "PostgreSQL", "Redis", "Python"],
        "must_not_claim_unverified": [
            "years of rust",
            "production rust",
            "built rust",
            "years of elixir",
            "production elixir",
            "built elixir",
        ],
    },
    {
        "id": "application_qa_honest_gaps",
        "pipeline": "application_qa",
        "company_name": "Orbital Systems",
        "position": "Senior Backend Engineer",
        "job_description": "Seeking backend engineer with FastAPI, PostgreSQL, Redis; Rust is a bonus.",
        "candidate_cv": GOLDEN_CV_TEXT,
        "questions": [
            {
                "id": "q_dist",
                "question": "Briefly describe a distributed backend or LLM system you architected.",
                "word_limit": 120,
            },
            {
                "id": "q_rust",
                "question": "Do you have production experience with Rust?",
                "word_limit": 80,
            },
        ],
        "q1_must_include_any": [
            "FastAPI",
            "PostgreSQL",
            "Redis",
            "LangGraph",
            "Kubernetes",
        ],
        "q2_must_acknowledge_gap_any": [
            "no ",
            "not ",
            "lack",
            "don't",
            "do not",
            "haven't",
            "without",
            "unlisted",
            "absent",
            "focus",
            "instead",
            "python",
            "go",
        ],
        "q2_must_not_claim": [
            "years of production rust",
            "expert in rust",
            "built production services in rust",
        ],
    },
]
