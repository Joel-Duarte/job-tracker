# Proposed Features for Job Tracker

Based on the architecture and core goals of the Job Tracker project, here are 20 ideated features sorted by Relevance to the Project.

## 1. Automated Application Follow-Up Reminders
**Description:** A background job that monitors application timelines. If an application stays in the "Applied" or "Interview" stage for X days without a new `ApplicationEventModel` (email), it automatically generates an `ActionItemModel` reminding the user to follow up, complete with a drafted nudge email.

**Pros:**
1. Keeps candidates proactive and prevents ghosting, drastically improving their pipeline conversion.
2. Seamlessly integrates with the existing Kanban status and Action Item architecture.

**Cons:**
1. Requires implementing a robust background scheduler (e.g., APScheduler or Celery) beyond the simple FastAPI background tasks currently used.
2. Could generate unwanted UI noise if the user casually tracks applications they don't strongly care about.

- **Relevance to Project:** 10/10
- **Ease of Implementation:** 7/10

---

## 2. Automated Job Board Auto-Filler (Via Browser Extension)
**Description:** A companion browser extension that reads the user's structured `CandidateCVModel` from the backend and automatically maps and injects the data (experience, links, education) into standard Workday, Lever, and Greenhouse forms on click.

**Pros:**
1. Eliminates the most universally hated aspect of job hunting: manually re-typing resumes into portals.
2. Converts the application from a passive tracking board into an active, high-speed application engine.

**Cons:**
1. Inherently fragile due to constant DOM and form changes on third-party job boards.
2. Requires bootstrapping, publishing, and maintaining an entirely separate browser extension repository and tech stack.

- **Relevance to Project:** 10/10
- **Ease of Implementation:** 3/10

---

## 3. Tailored Cover Letter & Resume Generator
**Description:** A module that takes the user's `CandidateCVModel` and a specific `JobPostingModel` or `ApplicationModel`, and uses the LLM to generate a highly targeted cover letter and a tailored version of the resume emphasizing the matching skills.

**Pros:**
1. Solves a massive pain point for job seekers by automating a tedious manual task.
2. Leverages the existing LLM orchestration (LangChain/LangGraph) and the robust skill-matching algorithms already present in the codebase.

**Cons:**
1. Exporting the final tailored resume to a cleanly formatted PDF or DOCX requires additional backend libraries and complex styling logic.
2. Requires building a new specialized frontend editor for users to review, tweak, and approve the generated documents before saving.

- **Relevance to Project:** 9/10
- **Ease of Implementation:** 6/10

---

## 4. Salary Negotiation Co-Pilot
**Description:** A dedicated tool that takes a received `offered_salary`, the `job_posting.salary_max`, and the user's `CandidateCVModel` experience level to query the LLM for market rates and generate a strategic, step-by-step negotiation script to counter-offer.

**Pros:**
1. Unmatched ROI for the user—a feature that literally helps them negotiate thousands of dollars.
2. Makes the tracker feel like a true "career agent" rather than just a database.

**Cons:**
1. LLMs can give overly aggressive or out-of-touch negotiation advice if not strictly prompted.
2. Relying entirely on LLM world knowledge for salary data may be inaccurate without integrating a paid external salary API.

- **Relevance to Project:** 9/10
- **Ease of Implementation:** 6/10

---

## 5. Job Market Keyword Trend Analyzer
**Description:** Aggregates the `required_skills` and `missing_skills` across all ingested `JobPostingModel`s for a user. Displays a word cloud or list indicating which skills the user lacks that are appearing most frequently in jobs they want.

**Pros:**
1. Gives candidates direct, data-backed advice on what to study next to improve their hireability.
2. Uses data the app is already actively collecting and storing via the `intake.py` pipeline.

**Cons:**
1. Requires relatively heavy SQL aggregation and caching to keep the frontend snappy.
2. Normalization of skill strings (e.g. "ReactJS" vs "React" vs "React.js") is difficult without continuous LLM sanitization.

- **Relevance to Project:** 9/10
- **Ease of Implementation:** 6/10

---

## 6. Inbox "Cold Outreach" Campaign Manager
**Description:** Allows users to create a wishlist of target companies. The AI generates highly personalized cold outreach messages to recruiters at those companies based on the user's `CandidateProfile`, and the system tracks open/reply rates via the `email_fetcher`.

**Pros:**
1. Empowers proactive, outbound job searching which is highly effective for senior candidates.
2. Unlocks an entirely new, highly lucrative workflow that standard job trackers don't touch.

**Cons:**
1. Edges dangerously close to spam/botting territory, depending on user behavior.
2. High risk of the user's connected email provider triggering rate-limits or bans.

- **Relevance to Project:** 9/10
- **Ease of Implementation:** 5/10

---

## 7. Interview Scheduling Assistant (Calendly/Google Calendar Sync)
**Description:** Automatically detects interview invite emails, extracts times, and cross-references the user's connected Google Calendar. It drafts a reply with available time slots and syncs the finalized event back to the `ApplicationModel`.

**Pros:**
1. Reduces the friction and cognitive load of the "scheduling dance."
2. Ensures interviews are instantly reflected in the Kanban timeline and reminders.

**Cons:**
1. Deep 2-way Google/Outlook Calendar integration requires managing complex OAuth scopes and refresh tokens.
2. Timezone logic and edge cases are notoriously difficult to get right.

- **Relevance to Project:** 9/10
- **Ease of Implementation:** 4/10

---

## 8. Application "Staleness" Auto-Archiver
**Description:** A cleanup cron job that automatically moves applications from "Applied" to "Archived/Ghosted" if there has been no email activity or status change for 60+ days, keeping the active Kanban board uncluttered.

**Pros:**
1. Improves the UX by keeping the Kanban board focused only on active leads.
2. Very easy to implement via a simple nightly SQL query and state transition.

**Cons:**
1. Might prematurely archive slow-moving enterprise or government applications.
2. Users might feel they lost data if the transition happens without clear notification.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 9/10

---

## 9. One-Click Email Reply Drafter
**Description:** Since the system tracks `ActionItemModel`s for emails requiring a response (e.g., "Schedule Interview", "Respond to Offer"), this feature adds an "Auto-Draft Reply" button. It uses the `ApplicationEventModel` context and the user's profile to instantly draft a professional email reply.

**Pros:**
1. Perfectly complements the existing Action Items and email intake pipelines, closing the loop from "Action Required" to "Action Taken".
2. Extremely straightforward to implement on the backend using the existing `llm_factory.py` with a new specific prompt template.

**Cons:**
1. Without integrating full OAuth SMTP sending capabilities, users still have to copy-paste the drafted text into their email client manually.
2. Potential risk if the user blindly copies an LLM hallucination (e.g., agreeing to a wrong time or salary) without reviewing.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 8/10

---

## 10. Application Conversion Analytics Dashboard
**Description:** A rich analytics view visualizing the user's pipeline funnel (e.g., Applied -> Screen % -> Technical % -> Offer %) and using AI to correlate which specific `extracted_skills` or domains from their profile result in the highest interview rates.

**Pros:**
1. Provides data-driven insights to help users identify flaws in their resume or interviewing strategy.
2. Visually satisfying and a standard hallmark of mature CRM-style software.

**Cons:**
1. Requires importing and configuring a robust charting library (like Chart.js or D3) on the Vue frontend.
2. Requires writing complex SQL aggregation and analytics queries on the backend.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 7/10

---

## 11. Smart Portfolio & Case Study Matcher
**Description:** Allows users to catalog links and descriptions of their past projects. When an application hits the `TECHNICAL_INTERVIEW` stage, the AI evaluates the `required_skills` of the job and suggests which specific portfolio projects the candidate should bring up during the interview.

**Pros:**
1. Directly improves technical interview performance by tailoring the candidate's talking points.
2. Fits perfectly into the existing Interview Guide generation workflow.

**Cons:**
1. Requires expanding the database schema and UI significantly to handle structured project/portfolio artifacts.
2. The LLM context window might get crowded if full project descriptions are constantly passed back and forth.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 7/10

---

## 12. Company Culture & Tech Stack Analyzer
**Description:** Before an interview, the LLM searches the web for the target company's engineering blog, recent news, and tech stack (e.g., via StackShare API) to brief the user on what technologies to brush up on and what cultural values to emphasize.

**Pros:**
1. Greatly enhances candidate preparation and boosts confidence.
2. Easily bolted onto the existing LangGraph `interview_guide_graph` structure.

**Cons:**
1. Relies on web search APIs (Tavily/SerpAPI), which might introduce flakiness or hallucinated company matches.
2. Smaller startups will have no data, leading to empty or hallucinated results.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 7/10

---

## 13. Automated Weekly Progress Report
**Description:** Generates a weekly summary email or push notification highlighting metrics like "Jobs Applied To", "Interviews Secured", and "Pending Action Items", paired with an encouraging AI-generated pep talk.

**Pros:**
1. High retention driver; brings users back to the app regularly.
2. Gamifies the job search process, keeping motivation high.

**Cons:**
1. Requires a robust email delivery service (SendGrid/Resend) and HTML email templating.
2. Can be demoralizing if the user had a slow or unsuccessful week.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 7/10

---

## 14. Take-Home Assignment Tracker & Evaluator
**Description:** When an application enters the "Take-Home" stage, this feature tracks the deadline, prompts the user to upload their completed code/document, and uses the LLM to run a preliminary "Code Review" grading it against the `JobPostingModel` requirements before they submit it.

**Pros:**
1. Helps candidates catch obvious bugs or missed requirements before submission.
2. Provides immediate, actionable value during a highly stressful phase of the application.

**Cons:**
1. LLMs may falsely critique correct code or give poor architectural advice, confusing the user.
2. Requires building a UI to securely upload, store, and display large code snippets or PDFs.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 6/10

---

## 15. Network Mapping & Referral Finder
**Description:** An integration (via LinkedIn OAuth or manual CSV import) that maps the user's network connections against the `CompanyModel` list on their Kanban board, visually highlighting companies where they have a "warm introduction" opportunity.

**Pros:**
1. Referrals are statistically the highest-converting job search strategy; this encourages best practices.
2. Transforms the app from an isolated tracking tool into a holistic networking CRM.

**Cons:**
1. LinkedIn's API is notoriously locked down, likely forcing users to manually export and upload their connection data.
2. Introduces data privacy and storage overhead regarding syncing entire personal network graphs.

- **Relevance to Project:** 8/10
- **Ease of Implementation:** 2/10

---

## 16. Automated "Thank You" Email Dispatcher
**Description:** Post-interview, the system scans calendar events or transitions, generates a personalized "Thank you for the interview" email referencing context from the user's `notes`, and queues it as an Action Item for the user to quickly approve and send.

**Pros:**
1. Automates common recruitment etiquette that is proven to boost offer chances.
2. Creates a high perceived "magic" factor by proactively managing the user's relationships.

**Cons:**
1. Completely relies on the user accurately logging interview participants and notes to sound authentic.
2. Without direct SMTP capabilities, it remains just a text snippet requiring manual copy-pasting.

- **Relevance to Project:** 7/10
- **Ease of Implementation:** 8/10

---

## 17. Job Rejection Analyzer & Pivot Strategy
**Description:** When an application is moved to `REJECTED`, the LLM reads the rejection email/reason, compares it against the `JobPostingModel`, and provides a constructive summary (e.g., "Missing senior-level React experience") while suggesting what to study or change for the next application.

**Pros:**
1. Turns negative user experiences (rejections) into actionable, positive data.
2. Encourages continuous improvement and skill development during long job hunts.

**Cons:**
1. Rejection emails are usually automated and generic, severely limiting the AI's ability to extract real insight.
2. Might frustrate users if the AI gives generic or hallucinated advice based on boilerplate rejection text.

- **Relevance to Project:** 7/10
- **Ease of Implementation:** 8/10

---

## 18. Real-time Webhook Integrations (Zapier / Make)
**Description:** Exposes standard webhooks so that when an application changes status or a new interview is scheduled, it can trigger external workflows (e.g., send an SMS, update a Notion doc, or post in a personal Slack channel).

**Pros:**
1. Exponentially increases the flexibility and ecosystem integration capabilities of the app.
2. A standard "power-user" SaaS feature that drives retention.

**Cons:**
1. Requires building a webhook subscription management UI and reliable retry/delivery mechanisms on the backend.
2. Debugging failing external webhooks and managing user configurations is tedious.

- **Relevance to Project:** 7/10
- **Ease of Implementation:** 6/10

---

## 19. Mock Interview Simulator (Chat-based)
**Description:** Expanding on the `interview_guide_graph.py`, this feature would create an interactive chat interface (`AgentChatView`) where the AI adopts the persona of the hiring manager for a specific application. It asks the user questions from the generated interview guide and scores their responses.

**Pros:**
1. Highly engaging feature that provides active value (interview practice) rather than just passive tracking.
2. The foundational data (company profile, required skills, specific interviewer questions) is already generated and stored by the Interview Guide feature.

**Cons:**
1. Requires maintaining complex conversation state and strict prompt boundaries to keep the LLM acting exclusively as an interviewer.
2. A purely text-based chat simulator may feel unnatural for interview prep compared to a voice-based system, but voice introduces significant latency and cost hurdles.

- **Relevance to Project:** 7/10
- **Ease of Implementation:** 5/10

---

## 20. Offer Comparison Matrix
**Description:** When a user receives multiple offers, this tool generates a side-by-side comparison matrix evaluating base salary, equity (calculated via Black-Scholes or standard startup math), benefits, and alignment with the user's `CandidateProfile` goals.

**Pros:**
1. High user value for successful candidates facing complex equity packages.
2. Highly shareable visualization (good for organic growth).

**Cons:**
1. Startup equity mathematics (options, RSUs, strike prices, dilution) are complex and hard to accurately generalize.
2. Will be an empty feature for the vast majority of users who only get one offer at a time.

- **Relevance to Project:** 7/10
- **Ease of Implementation:** 5/10
