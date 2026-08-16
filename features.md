# Proposed Features for Job Tracker

Based on the architecture and core goals of the Job Tracker project, here are some ideated features with pros, cons, and evaluations.

## 1. Tailored Cover Letter & Resume Generator
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

## 2. One-Click Email Reply Drafter
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

## 3. Mock Interview Simulator (Chat-based)
**Description:** Expanding on the `interview_guide_graph.py`, this feature would create an interactive chat interface (`AgentChatView`) where the AI adopts the persona of the hiring manager for a specific application. It asks the user questions from the generated interview guide and scores their responses.

**Pros:**
1. Highly engaging feature that provides active value (interview practice) rather than just passive tracking.
2. The foundational data (company profile, required skills, specific interviewer questions) is already generated and stored by the Interview Guide feature.

**Cons:**
1. Requires maintaining complex conversation state and strict prompt boundaries to keep the LLM acting exclusively as an interviewer.
2. A purely text-based chat simulator may feel unnatural for interview prep compared to a voice-based system, but voice introduces significant latency and cost hurdles.

- **Relevance to Project:** 7/10
- **Ease of Implementation:** 5/10
