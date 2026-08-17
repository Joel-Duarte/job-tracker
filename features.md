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