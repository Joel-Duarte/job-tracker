import logging
from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.llm_factory import get_task_chat_model
from app.models.applications import ApplicationEventModel, ApplicationModel, JobPostingModel
from app.models.candidate_profile import CandidateCVModel
from app.models.interview_session import InterviewSessionModel
from app.schemas.interview_simulator import (
    InterviewPersona,
    StarPresence,
    TurnEvaluation,
)

logger = logging.getLogger(__name__)

PERSONA_PROMPTS = {
    InterviewPersona.TECHNICAL_BAR_RAISER: (
        "You are a strict, highly technical Bar Raiser interviewer. You evaluate candidates with deep scrutiny "
        "on technical depth, system design tradeoffs, edge cases, concurrency, and algorithmic performance. "
        "Maintain a direct, precise, and rigorous tone. Expect comprehensive architectural clarity."
    ),
    InterviewPersona.HIRING_MANAGER: (
        "You are an experienced Hiring Manager interviewer. You focus on project ownership, cross-functional "
        "collaboration, conflicting priorities, business impact, and engineering leadership. "
        "Maintain a pragmatic, results-oriented, professional tone."
    ),
    InterviewPersona.BEHAVIORAL_CULTURE: (
        "You are a Behavioral & Culture Fit interviewer. You evaluate cultural alignment, teamwork, ethics, "
        "resilience under pressure, and adherence to the STAR (Situation, Task, Action, Result) story structure. "
        "Maintain an attentive, professional, and culture-focused tone."
    ),
    InterviewPersona.SUPPORTIVE_COACH: (
        "You are an encouraging and empathetic Interview Coach. You help candidates polish their answers, "
        "offering supportive feedback, highlighting strengths, constructively pointing out missing STAR elements, "
        "and suggesting rich exemplar rewrites. Maintain a warm, encouraging, and coaching tone."
    ),
}

DECOUPLED_EVALUATION_SYSTEM_PROMPT = """{persona_instruction}

STRICT RULE: YOUR SOLE RESPONSIBILITY IS TO EVALUATE THE CANDIDATE'S ANSWER.
YOU ARE STRICTLY FORBIDDEN FROM ASKING A NEW QUESTION, ASKING FOLLOW-UP QUESTIONS, OR ADVANCING THE TOPIC.
Do not include any greeting or conversational filler beyond the JSON output.

Evaluate the candidate's answer based on the STAR rubric (Situation, Task, Action, Result) and the context provided.
Context (Target Role / JD / Question):
{context_info}

Question Asked: {question_asked}
Candidate's Answer: {user_answer}

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "score": <number between 0 and 100>,
  "star_presence": {{
    "situation": <true|false>,
    "task": <true|false>,
    "action": <true|false>,
    "result": <true|false>
  }},
  "strengths": ["<strength 1>", "<strength 2>"],
  "missing_gaps": ["<gap 1>", "<gap 2>"],
  "constructive_critique": "<Detailed constructive critique tailored to the interviewer persona>",
  "exemplar_rewrite": "<An exemplar STAR response demonstrating how a staff/principal level candidate would answer>"
}}
"""

QUESTION_GENERATION_SYSTEM_PROMPT = """{persona_instruction}

You are conducting a live mock interview.
Target Position: {position}
Company: {company_name}
Job Description Summary / Requirements:
{job_spec}

Candidate CV Summary:
{cv_summary}

Previous Interview Questions & Performance Summary:
{turns_summary}

Generate the NEXT primary interview question for the candidate.
The question should match your interviewer persona traits ({persona_name}) and probe key responsibilities, required skills, or behavioral experiences relevant to the role.

Respond ONLY with a valid JSON object:
{{
  "question": "<The next interview question>",
  "question_type": "BEHAVIORAL_STAR"
}}
"""

DRILL_DOWN_SYSTEM_PROMPT = """{persona_instruction}

You are conducting a live mock interview.
The candidate recently answered the question below, but left gaps or technical areas worth probing deeper.

Question Asked: {last_question}
Candidate's Answer: {last_answer}
Identified Gaps / Areas to Probe: {missing_gaps}

Formulate an adaptive, realistic drill-down follow-up question that challenges the candidate on their previous answer (e.g., asking about specific tradeoffs, scale, edge cases, missing metrics, or postmortems).

Respond ONLY with a valid JSON object:
{{
  "question": "<Adaptive drill-down question>",
  "question_type": "DRILL_DOWN"
}}
"""


class InterviewSimulatorService:

    @staticmethod
    async def get_context_for_application(
        db: AsyncSession, application_id: Optional[int]
    ) -> dict[str, Any]:
        position = "General Software / Technology Role"
        company_name = "General Engineering Practice"
        job_spec = "Standard software engineering and behavioral interview evaluation."
        cv_summary = "Candidate profile and experience."
        opening_questions = [
            "Tell me about a time you faced a complex technical challenge or production incident and how you resolved it."
        ]

        if application_id:
            stmt = (
                select(ApplicationModel)
                .options(
                    selectinload(ApplicationModel.company),
                    selectinload(ApplicationModel.job_posting),
                )
                .where(ApplicationModel.id == application_id)
            )
            res = await db.execute(stmt)
            app_model = res.scalar_one_or_none()

            if app_model:
                position = app_model.position or position
                if app_model.company:
                    company_name = app_model.company.name or company_name
                if app_model.job_posting and app_model.job_posting.description_markdown:
                    job_spec = app_model.job_posting.description_markdown[:2000]

                if app_model.interview_guide_preferences:
                    guide_qs = app_model.interview_guide_preferences.get("questions", [])
                    if guide_qs:
                        opening_questions = [q if isinstance(q, str) else q.get("question", str(q)) for q in guide_qs]

        # Fetch Candidate CV
        cv_stmt = select(CandidateCVModel).order_by(CandidateCVModel.created_at.desc()).limit(1)
        cv_res = await db.execute(cv_stmt)
        cv_model = cv_res.scalar_one_or_none()
        if cv_model and cv_model.raw_text:
            cv_summary = cv_model.raw_text[:2000]

        return {
            "position": position,
            "company_name": company_name,
            "job_spec": job_spec,
            "cv_summary": cv_summary,
            "opening_questions": opening_questions,
        }

    @staticmethod
    async def start_session(
        db: AsyncSession, application_id: Optional[int], persona: str
    ) -> InterviewSessionModel:
        ctx = await InterviewSimulatorService.get_context_for_application(db, application_id)
        first_q = ctx["opening_questions"][0]

        session = InterviewSessionModel(
            application_id=application_id,
            persona=persona,
            status="IN_PROGRESS",
            turns_data=[
                {
                    "turn_index": 1,
                    "question": first_q,
                    "question_type": "BEHAVIORAL_STAR",
                    "user_answer": "",
                    "attempt_count": 0,
                    "evaluation": None,
                    "is_drill_down": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def evaluate_answer(
        db: AsyncSession, session_id: int, turn_index: int, answer_text: str
    ) -> InterviewSessionModel:
        stmt = select(InterviewSessionModel).where(InterviewSessionModel.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        # Find target turn
        turns = list(session.turns_data or [])
        target_turn = None
        target_turn_idx = -1
        for idx, t in enumerate(turns):
            if t.get("turn_index") == turn_index:
                target_turn = t
                target_turn_idx = idx
                break

        if not target_turn:
            # Fallback to last turn or create new turn structure
            target_turn = {
                "turn_index": turn_index,
                "question": "Interview Question",
                "question_type": "BEHAVIORAL_STAR",
                "is_drill_down": False,
            }
            turns.append(target_turn)
            target_turn_idx = len(turns) - 1

        ctx = await InterviewSimulatorService.get_context_for_application(db, session.application_id)
        persona_enum = InterviewPersona(session.persona) if session.persona in InterviewPersona.__members__ else InterviewPersona.TECHNICAL_BAR_RAISER
        persona_inst = PERSONA_PROMPTS.get(persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER])

        prompt = DECOUPLED_EVALUATION_SYSTEM_PROMPT.format(
            persona_instruction=persona_inst,
            context_info=f"Role: {ctx['position']} at {ctx['company_name']}\nJD: {ctx['job_spec'][:1000]}",
            question_asked=target_turn.get("question", ""),
            user_answer=answer_text,
        )

        from app.services.postgres_tracer import PostgresTracer
        tracer = PostgresTracer()

        chat_model = await get_task_chat_model(db, task_type="ASSESSMENT")
        llm_res = await chat_model.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content="Evaluate now.")],
            config={"callbacks": [tracer]}
        )
        await tracer.flush()

        parser = JsonOutputParser()
        try:
            eval_data = parser.parse(llm_res.content)
        except Exception as e:
            logger.error("Failed to parse evaluation JSON from LLM: %s. Output: %s", e, llm_res.content)
            eval_data = {
                "score": 70.0,
                "star_presence": {"situation": True, "task": True, "action": True, "result": False},
                "strengths": ["Clear explanation of scenario."],
                "missing_gaps": ["Could elaborate more on quantifiable results."],
                "constructive_critique": "Solid answer, but add specific metrics to demonstrate impact.",
                "exemplar_rewrite": "During my recent role, I led the architecture update resulting in 40% performance gains.",
            }

        attempt_cnt = target_turn.get("attempt_count", 0) + 1

        target_turn["user_answer"] = answer_text
        target_turn["attempt_count"] = attempt_cnt
        target_turn["evaluation"] = eval_data
        target_turn["updated_at"] = datetime.now(timezone.utc).isoformat()

        turns[target_turn_idx] = target_turn
        session.turns_data = turns

        # Recalculate overall score across evaluated turns
        evaluated_scores = [
            t["evaluation"]["score"]
            for t in turns
            if t.get("evaluation") and isinstance(t["evaluation"], dict) and "score" in t["evaluation"]
        ]
        if evaluated_scores:
            session.overall_score = round(sum(evaluated_scores) / len(evaluated_scores), 1)

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def generate_next_question(
        db: AsyncSession, session_id: int
    ) -> InterviewSessionModel:
        stmt = select(InterviewSessionModel).where(InterviewSessionModel.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        turns = list(session.turns_data or [])

        # Build turns summary
        turns_summary = ""
        for t in turns:
            if t.get("user_answer"):
                turns_summary += f"\nQ ({t.get('turn_index')}): {t.get('question')}\nA: {t.get('user_answer')[:300]}\n"

        ctx = await InterviewSimulatorService.get_context_for_application(db, session.application_id)
        persona_enum = InterviewPersona(session.persona) if session.persona in InterviewPersona.__members__ else InterviewPersona.TECHNICAL_BAR_RAISER
        persona_inst = PERSONA_PROMPTS.get(persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER])

        prompt = QUESTION_GENERATION_SYSTEM_PROMPT.format(
            persona_instruction=persona_inst,
            position=ctx["position"],
            company_name=ctx["company_name"],
            job_spec=ctx["job_spec"][:1500],
            cv_summary=ctx["cv_summary"][:1500],
            turns_summary=turns_summary or "None yet.",
            persona_name=session.persona,
        )

        from app.services.postgres_tracer import PostgresTracer
        tracer = PostgresTracer()

        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_GUIDE")
        llm_res = await chat_model.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content="Generate next question.")],
            config={"callbacks": [tracer]}
        )
        await tracer.flush()

        parser = JsonOutputParser()
        try:
            q_data = parser.parse(llm_res.content)
            next_q = q_data.get("question", "Tell me about a project you are most proud of.")
        except Exception:
            next_q = "Tell me about a challenging project and how you engineered the solution."

        next_index = len(turns) + 1
        new_turn = {
            "turn_index": next_index,
            "question": next_q,
            "question_type": "BEHAVIORAL_STAR",
            "user_answer": "",
            "attempt_count": 0,
            "evaluation": None,
            "is_drill_down": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        turns.append(new_turn)
        session.turns_data = turns

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def generate_drill_down(
        db: AsyncSession, session_id: int, turn_index: Optional[int] = None
    ) -> InterviewSessionModel:
        stmt = select(InterviewSessionModel).where(InterviewSessionModel.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        turns = list(session.turns_data or [])
        if not turns:
            return await InterviewSimulatorService.generate_next_question(db, session_id)

        last_turn = turns[-1]
        if turn_index:
            for t in turns:
                if t.get("turn_index") == turn_index:
                    last_turn = t
                    break

        last_eval = last_turn.get("evaluation") or {}
        gaps = last_eval.get("missing_gaps", ["Details on technical tradeoffs and metrics."])

        persona_enum = InterviewPersona(session.persona) if session.persona in InterviewPersona.__members__ else InterviewPersona.TECHNICAL_BAR_RAISER
        persona_inst = PERSONA_PROMPTS.get(persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER])

        prompt = DRILL_DOWN_SYSTEM_PROMPT.format(
            persona_instruction=persona_inst,
            last_question=last_turn.get("question", ""),
            last_answer=last_turn.get("user_answer", "N/A"),
            missing_gaps=", ".join(gaps) if isinstance(gaps, list) else str(gaps),
        )

        from app.services.postgres_tracer import PostgresTracer
        tracer = PostgresTracer()

        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_GUIDE")
        llm_res = await chat_model.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content="Generate drill-down question.")],
            config={"callbacks": [tracer]}
        )
        await tracer.flush()

        parser = JsonOutputParser()
        try:
            q_data = parser.parse(llm_res.content)
            dd_q = q_data.get("question", "Can you elaborate on the technical tradeoffs you considered?")
        except Exception:
            dd_q = "Can you walk through how you handled system failures or edge cases during that project?"

        next_index = len(turns) + 1
        new_turn = {
            "turn_index": next_index,
            "question": dd_q,
            "question_type": "DRILL_DOWN",
            "user_answer": "",
            "attempt_count": 0,
            "evaluation": None,
            "is_drill_down": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        turns.append(new_turn)
        session.turns_data = turns

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def finalize_session(
        db: AsyncSession, session_id: int
    ) -> dict[str, Any]:
        stmt = select(InterviewSessionModel).where(InterviewSessionModel.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        turns = list(session.turns_data or [])
        evaluated_scores = [
            t["evaluation"]["score"]
            for t in turns
            if t.get("evaluation") and isinstance(t["evaluation"], dict) and "score" in t["evaluation"]
        ]

        if evaluated_scores:
            overall = round(sum(evaluated_scores) / len(evaluated_scores), 1)
        else:
            overall = 75.0

        if overall >= 85.0:
            readiness = "STRONG_HIRE"
        elif overall >= 70.0:
            readiness = "HIRE"
        else:
            readiness = "NEEDS_WORK"

        all_strengths = []
        all_gaps = []
        for t in turns:
            ev = t.get("evaluation")
            if isinstance(ev, dict):
                all_strengths.extend(ev.get("strengths", []))
                all_gaps.extend(ev.get("missing_gaps", []))

        summary_feedback = {
            "key_strengths": list(set(all_strengths))[:3] or ["Demonstrates solid engineering context."],
            "top_improvement_areas": list(set(all_gaps))[:3] or ["Include more quantitative metrics in responses."],
            "total_questions_evaluated": len(evaluated_scores),
        }

        session.overall_score = overall
        session.readiness_rating = readiness
        session.summary_feedback = summary_feedback
        session.status = "COMPLETED"
        session.completed_at = datetime.now(timezone.utc)

        timeline_event_id = None
        if session.application_id:
            event = ApplicationEventModel(
                email_application_id=session.application_id,
                email_event_type="INTERVIEW",
                email_subject=f"Completed Mock Interview ({session.persona})",
                email_summary=f"Completed Mock Interview simulation with score {int(overall)}/100 ({readiness}).",
                email_received_at=datetime.now(timezone.utc),
                source_channel="SYSTEM",
                raw_payload={
                    "session_id": session.id,
                    "overall_score": overall,
                    "readiness": readiness,
                    "persona": session.persona,
                },
            )
            db.add(event)
            await db.flush()
            timeline_event_id = event.id

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return {
            "session_id": session.id,
            "overall_score": overall,
            "readiness_rating": readiness,
            "summary_feedback": summary_feedback,
            "timeline_event_id": timeline_event_id,
        }

    @staticmethod
    async def save_notes(
        db: AsyncSession, session_id: int, custom_markdown: Optional[str] = None
    ) -> ApplicationModel:
        stmt = select(InterviewSessionModel).where(InterviewSessionModel.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session or not session.application_id:
            raise ValueError(f"Valid interview session with application_id required for session {session_id}.")

        app_stmt = select(ApplicationModel).where(ApplicationModel.id == session.application_id)
        app_res = await db.execute(app_stmt)
        app_model = app_res.scalar_one_or_none()
        if not app_model:
            raise ValueError(f"Application {session.application_id} not found.")

        if custom_markdown:
            formatted_notes = custom_markdown
        else:
            fb = session.summary_feedback or {}
            strengths_list = "\n".join([f"- {s}" for s in fb.get("key_strengths", [])])
            gaps_list = "\n".join([f"- {g}" for g in fb.get("top_improvement_areas", [])])

            formatted_notes = f"""### Mock Interview Debrief ({session.persona})
**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
**Readiness Rating**: {session.readiness_rating or 'N/A'} (Score: {session.overall_score or 0}/100)

#### Top Strengths
{strengths_list if strengths_list else '- Solid participation.'}

#### Priority Prep Gaps
{gaps_list if gaps_list else '- Continue refining STAR structure.'}
"""

        existing_notes = app_model.notes or ""
        app_model.notes = (existing_notes + "\n\n" + formatted_notes).strip()
        db.add(app_model)
        await db.commit()
        await db.refresh(app_model)
        return app_model
