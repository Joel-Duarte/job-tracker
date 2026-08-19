import logging
from datetime import UTC, datetime, timedelta

from app.services.seed_data import (
    build_airbnb_dossier,
    build_datadog_dossier,
    build_figma_dossier,
    build_linear_dossier,
    build_stripe_dossier,
)

logger = logging.getLogger(__name__)


class InMemoryFallbackRepository:
    """
    In-memory fallback state repository loaded directly from seed_data.py.
    Used as an operational fallback state store when database connection
    is blocked or database initialization fails.
    """

    def __init__(self):
        self._initialized_at = datetime.now(UTC)
        self.candidate_cv: dict = {}
        self.companies: list[dict] = []
        self.applications: list[dict] = []
        self.job_postings: list[dict] = []
        self.events: list[dict] = []
        self.action_items: list[dict] = []
        self.other_events: list[dict] = []
        self.staging_items: list[dict] = []
        self.intake_tasks: list[dict] = []
        self.ai_providers: list[dict] = []
        self.email_accounts: list[dict] = []

        self._load_fallback_dataset()

    def _load_fallback_dataset(self) -> None:
        now = datetime.now(UTC)

        # 1. Candidate CV
        self.candidate_cv = {
            "id": 1,
            "raw_text": (
                "Alex Morgan\nStaff Software Engineer & Distributed Systems Architect\n"
                "Email: alex.morgan.dev@gmail.com | Location: San Francisco, CA (Remote Friendly)\n"
                "Summary: Staff backend engineer with 8+ years of experience in Python, Go, and TypeScript."
            ),
            "anonymized_text": "[Candidate] - Staff Software Engineer & Distributed Systems Architect",
            "extracted_skills": [
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
            "years_of_experience": 8.5,
            "domain_expertise": [
                "Fintech & Payments Infrastructure",
                "Distributed Systems & Event-Driven Architecture",
                "High-Throughput API Design",
                "Cloud Native & Kubernetes Platform",
            ],
            "summary": "Senior / Staff Distributed Systems Engineer specializing in Python, FastAPI, and real-time backend architectures.",
            "is_active": True,
        }

        # 2. Companies & Applications
        dossiers = [
            (
                "Stripe",
                "stripe.com",
                "Senior Backend Engineer - Global Payments",
                "APPLIED",
                build_stripe_dossier(),
                4,
                1,
            ),
            (
                "Linear",
                "linear.app",
                "Staff Systems & Sync Engineer",
                "TECHNICAL_INTERVIEW",
                build_linear_dossier(),
                12,
                0,
            ),
            (
                "Figma",
                "figma.com",
                "Principal Platform Engineer",
                "OFFER",
                build_figma_dossier(),
                25,
                0,
            ),
            (
                "Datadog",
                "datadoghq.com",
                "Senior Software Engineer - Distributed Tracing",
                "ONLINE_ASSESSMENT",
                build_datadog_dossier(),
                5,
                2,
            ),
            (
                "Airbnb",
                "airbnb.com",
                "Senior Platform Engineer",
                "REJECTED",
                build_airbnb_dossier(),
                20,
                6,
            ),
        ]

        for idx, (
            comp_name,
            domain,
            pos,
            status_str,
            dossier,
            app_days_ago,
            act_days_ago,
        ) in enumerate(dossiers, start=1):
            comp_id = idx
            comp_obj = {
                "id": comp_id,
                "name": comp_name,
                "name_normalized": comp_name.lower(),
                "domain": domain,
            }
            self.companies.append(comp_obj)

            app_date = now - timedelta(days=app_days_ago)
            last_act = (
                now - timedelta(days=act_days_ago)
                if act_days_ago > 0
                else now - timedelta(hours=6)
            )

            app_obj = {
                "id": idx,
                "company_id": comp_id,
                "company": comp_obj,
                "position": pos,
                "position_normalized": pos.lower(),
                "status": status_str,
                "application_date": app_date.isoformat(),
                "last_activity_at": last_act.isoformat(),
                "match_analysis_payload": dossier,
                "job_url": f"https://{domain}/careers/{idx}",
            }
            self.applications.append(app_obj)

            self.job_postings.append(
                {
                    "id": idx,
                    "application_id": idx,
                    "job_url": app_obj["job_url"],
                    "salary_min": dossier.get("salary_min"),
                    "salary_max": dossier.get("salary_max"),
                    "currency": dossier.get("currency", "USD"),
                    "location": dossier.get("location"),
                    "work_model": dossier.get("work_model"),
                    "required_skills": dossier.get("matching_skills", []),
                }
            )

            # Events & Actions
            self.events.append(
                {
                    "id": idx,
                    "email_application_id": idx,
                    "email_subject": f"Update on {pos} position at {comp_name}",
                    "email_sender": f"careers@{domain}",
                    "email_event_type": "APPLICATION_SUBMITTED"
                    if status_str == "APPLIED"
                    else "STATUS_CHANGE",
                    "email_status_after_event": status_str,
                    "email_received_at": app_date.isoformat(),
                }
            )

            self.action_items.append(
                {
                    "id": idx,
                    "application_id": idx,
                    "title": f"Follow up on {pos} application with {comp_name}",
                    "due_date": (now + timedelta(days=2)).isoformat(),
                    "status": "PENDING"
                    if status_str
                    in ("APPLIED", "TECHNICAL_INTERVIEW", "ONLINE_ASSESSMENT")
                    else "COMPLETED",
                    "urgency": "HIGH"
                    if status_str in ("TECHNICAL_INTERVIEW", "ONLINE_ASSESSMENT")
                    else "MEDIUM",
                }
            )

        # 3. Other Recruitment Events
        self.other_events = [
            {
                "id": 1,
                "email_sender": "newsletter@bytebytego.com",
                "company": "ByteByteGo",
                "summary": "Understanding Modern Distributed Consensus Protocols",
                "email_type": "NEWSLETTER",
            },
            {
                "id": 2,
                "email_sender": "recruiter@venturetalent.io",
                "company": "Venture Talent",
                "summary": "Founding Engineer Role at Series A AI Compute Startup",
                "email_type": "RECRUITER_OUTREACH",
            },
        ]

        # 4. Staging Queue Items
        self.staging_items = [
            {
                "id": 1,
                "email_sender": "founder@stealth-ai-infra.io",
                "company": "Stealth AI Labs",
                "status": "PENDING",
                "match_score": 0.45,
            },
            {
                "id": 2,
                "email_sender": "careers@nexacorp-systems.com",
                "company": "NexaCorp",
                "status": "PENDING",
                "match_score": 0.62,
            },
        ]

        # 5. Intake Evaluation Tasks
        self.intake_tasks = [
            {
                "id": 1,
                "title_hint": "Stripe - Senior Backend Engineer",
                "status": "COMPLETED",
                "result_json": build_stripe_dossier(),
            },
            {
                "id": 2,
                "title_hint": "Linear - Staff Systems & Sync Engineer",
                "status": "COMPLETED",
                "result_json": build_linear_dossier(),
            },
        ]

        # 6. AI Providers & Email Accounts
        self.ai_providers = [{"id": 1, "name": "Local LM Studio", "is_active": True}]
        self.email_accounts = [
            {"id": 1, "username": "alex.morgan.dev@gmail.com", "is_active": True}
        ]

        logger.info(
            "Loaded in-memory fallback state repository with %d applications.",
            len(self.applications),
        )

    def get_stats(self) -> dict[str, int]:
        return {
            "companies": len(self.companies),
            "applications": len(self.applications),
            "job_postings": len(self.job_postings),
            "action_items": len(self.action_items),
            "application_events": len(self.events),
            "other_events": len(self.other_events),
            "staging_items": len(self.staging_items),
            "intake_tasks": len(self.intake_tasks),
            "ai_providers": len(self.ai_providers),
            "email_accounts": len(self.email_accounts),
            "candidate_cvs": 1 if self.candidate_cv else 0,
        }

    def get_applications(
        self, q: str | None = None, status_filter: str | None = None
    ) -> list[dict]:
        results = list(self.applications)
        if status_filter:
            results = [
                a for a in results if a["status"].upper() == status_filter.upper()
            ]
        if q:
            pattern = q.lower()
            results = [
                a
                for a in results
                if pattern in a["position"].lower()
                or pattern in a["company"]["name"].lower()
            ]
        return results

    def get_application_by_id(self, app_id: int) -> dict | None:
        for app in self.applications:
            if app["id"] == app_id:
                return app
        return None

    def get_candidate_cv(self) -> dict:
        return self.candidate_cv

    def get_companies(self) -> list[dict]:
        return self.companies

    def get_action_items(self) -> list[dict]:
        return self.action_items

    def get_staging_items(self) -> list[dict]:
        return self.staging_items

    def get_intake_tasks(self) -> list[dict]:
        return self.intake_tasks


_fallback_repo_instance: InMemoryFallbackRepository | None = None


def get_fallback_repository() -> InMemoryFallbackRepository:
    """Returns the singleton InMemoryFallbackRepository instance."""
    global _fallback_repo_instance
    if _fallback_repo_instance is None:
        _fallback_repo_instance = InMemoryFallbackRepository()
    return _fallback_repo_instance
