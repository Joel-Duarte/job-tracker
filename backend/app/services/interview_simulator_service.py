import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.llm_factory import get_active_llm_config_dict, get_task_chat_model
from app.models.applications import (
    ApplicationEventModel,
    ApplicationModel,
)
from app.models.candidate_profile import CandidateCVModel
from app.models.interview_session import InterviewSessionModel
from app.schemas.interview_simulator import (
    InterviewPersona,
)

logger = logging.getLogger(__name__)


def is_local_llm_endpoint(
    base_url: str | None, provider_type: str | None = None
) -> bool:
    if provider_type and provider_type.lower() in (
        "lmstudio",
        "ollama",
        "local",
        "vllm",
    ):
        return True
    if not base_url:
        return False
    url_lower = base_url.lower()
    local_indicators = (
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "192.168.",
        "10.",
        ".local",
        "host.docker.internal",
    )
    return any(ind in url_lower for ind in local_indicators)


async def _invoke_llm_adaptive(
    chat_model: Any,
    messages: list[Any],
    tracer: Any,
    db: AsyncSession,
) -> Any:
    """
    Invokes LLM adaptively:
    - For local endpoints (LM Studio, Ollama, local IP): No artificial timeout (runs until completion on slow hardware).
    - For cloud endpoints (OpenAI, Anthropic): 120s timeout protection against network hangs.
    """
    config = await get_active_llm_config_dict(db)
    is_local = is_local_llm_endpoint(
        config.get("api_base"), config.get("provider_name")
    )
    timeout_seconds = None if is_local else 120.0

    if timeout_seconds:
        llm_res = await asyncio.wait_for(
            chat_model.ainvoke(messages, config={"callbacks": [tracer]}),
            timeout=timeout_seconds,
        )
    else:
        llm_res = await chat_model.ainvoke(messages, config={"callbacks": [tracer]})
    await tracer.flush()
    return llm_res


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

MULTIPLE_CHOICE_QUESTION_PROMPT = """{persona_instruction}

You are conducting a live technical and behavioral mock interview.
Target Position: {position}
Company: {company_name}
Job Description Summary / Requirements:
{job_spec}

Candidate CV Summary:
{cv_summary}

Previous Interview Questions & Performance Summary:
{turns_summary}

Generate an objective MULTIPLE CHOICE interview challenge (4 options: A, B, C, D) relevant to the role, system architecture, engineering tradeoffs, or behavioral judgment.
One option must represent the optimal approach, while the others represent plausible alternatives with distinct drawbacks.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "question": "<The scenario description or question>",
  "question_type": "MULTIPLE_CHOICE",
  "options": [
    {{"key": "A", "text": "<Option A text>", "explanation": "<Why this option is correct or flawed>"}},
    {{"key": "B", "text": "<Option B text>", "explanation": "<Why this option is correct or flawed>"}},
    {{"key": "C", "text": "<Option C text>", "explanation": "<Why this option is correct or flawed>"}},
    {{"key": "D", "text": "<Option D text>", "explanation": "<Why this option is correct or flawed>"}}
  ],
  "correct_key": "<A, B, C, or D>"
}}
"""

MULTIPLE_CHOICE_EVALUATION_PROMPT = """{persona_instruction}

STRICT RULE: YOUR SOLE RESPONSIBILITY IS TO EVALUATE THE CANDIDATE'S MULTIPLE CHOICE SELECTION AND TECHNICAL CORRECTNESS.
YOU ARE STRICTLY FORBIDDEN FROM ASKING A NEW QUESTION.

Context (Target Role / JD):
{context_info}

Question Asked: {question_asked}
Options:
{options_text}

Candidate's Selected Option: {selected_option}
Candidate's Optional Rationale: {user_answer}

EVALUATION GUIDELINES FOR MULTIPLE CHOICE:
1. Identify the correct/optimal option among the choices provided.
2. If the candidate chose the correct option:
   - Award a score of 95-100.
   - "constructive_critique" MUST confirm that Option {selected_option} is Correct and concisely explain the core technical reason and architecture tradeoffs that make it the best solution.
   - DO NOT criticize the candidate for not writing a lengthy text rationale or justification, because written rationale is strictly optional in multiple choice.
3. If the candidate chose an incorrect or suboptimal option:
   - Award an appropriate score (0-40).
   - "constructive_critique" MUST state that Option {selected_option} is Incorrect, identify the correct option, and explain why the selected option is flawed/suboptimal and why the correct choice works.

Respond ONLY with a valid JSON object:
{{
  "score": <number between 0 and 100>,
  "star_presence": {{
    "situation": true,
    "task": true,
    "action": true,
    "result": true
  }},
  "strengths": ["<key concept or strength>"],
  "missing_gaps": ["<gap or misconception if incorrect>"],
  "constructive_critique": "<Concise statement indicating Correct/Incorrect and explaining why>",
  "exemplar_rewrite": "<The optimal option and concise technical explanation>"
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


def _normalize_mc_options(raw_options: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_options, list) or not raw_options:
        return [
            {
                "key": "A",
                "text": "Raft consensus with multi-region replication",
                "explanation": "Ensures strong consistency and partition tolerance.",
            },
            {
                "key": "B",
                "text": "Single primary database with sync replicas",
                "explanation": "Vulnerable to single point of failure latency bottlenecks.",
            },
            {
                "key": "C",
                "text": "Asynchronous cron batch writes",
                "explanation": "High data loss risk during failure.",
            },
            {
                "key": "D",
                "text": "Stateless app servers without state persistence",
                "explanation": "Does not address stateful persistence.",
            },
        ]
    keys = ["A", "B", "C", "D"]
    normalized = []
    for idx, opt in enumerate(raw_options[:4]):
        default_key = keys[idx] if idx < len(keys) else str(idx + 1)
        if isinstance(opt, dict):
            k = (
                str(
                    opt.get("key")
                    or opt.get("option")
                    or opt.get("letter")
                    or default_key
                )
                .strip()
                .upper()
            )
            t = str(
                opt.get("text")
                or opt.get("description")
                or opt.get("answer")
                or f"Option {k}"
            ).strip()
            e = opt.get("explanation")
            normalized.append(
                {
                    "key": k,
                    "text": t,
                    "explanation": str(e).strip() if e is not None else None,
                }
            )
        elif isinstance(opt, str):
            parts = (
                opt.split(")", 1)
                if ")" in opt
                else opt.split(".", 1)
                if "." in opt
                else [default_key, opt]
            )
            if len(parts) == 2 and len(parts[0].strip()) <= 2:
                k = parts[0].strip().upper()
                t = parts[1].strip()
            else:
                k = default_key
                t = opt.strip()
            normalized.append({"key": k, "text": t, "explanation": None})
    return normalized


def _normalize_evaluation_data(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    score_raw = raw.get("score")
    try:
        if isinstance(score_raw, str):
            score_clean = score_raw.split("/")[0].strip()
            score = float(score_clean)
        elif score_raw is not None:
            score = float(score_raw)
        else:
            score = 75.0
    except (ValueError, TypeError):
        score = 75.0

    star_raw = raw.get("star_presence")
    if not isinstance(star_raw, dict):
        star_raw = {}
    star_presence = {
        "situation": bool(star_raw.get("situation", True)),
        "task": bool(star_raw.get("task", True)),
        "action": bool(star_raw.get("action", True)),
        "result": bool(star_raw.get("result", False)),
    }

    strengths = raw.get("strengths") or []
    if isinstance(strengths, str):
        strengths = [strengths]
    elif not isinstance(strengths, list):
        strengths = []

    missing_gaps = raw.get("missing_gaps") or raw.get("gaps") or []
    if isinstance(missing_gaps, str):
        missing_gaps = [missing_gaps]
    elif not isinstance(missing_gaps, list):
        missing_gaps = []

    critique = (
        raw.get("constructive_critique")
        or raw.get("critique")
        or raw.get("feedback")
        or "Solid technical response."
    )
    exemplar = (
        raw.get("exemplar_rewrite")
        or raw.get("exemplar")
        or raw.get("exemplar_answer")
        or raw.get("optimal_answer")
        or "Comprehensive response with clear architecture and tradeoff reasoning."
    )

    return {
        "score": max(0.0, min(100.0, score)),
        "star_presence": star_presence,
        "strengths": [str(s) for s in strengths],
        "missing_gaps": [str(g) for g in missing_gaps],
        "constructive_critique": str(critique),
        "exemplar_rewrite": str(exemplar),
    }


class InterviewSimulatorService:
    @staticmethod
    async def get_context_for_application(
        db: AsyncSession, application_id: int | None
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
                    guide_qs = app_model.interview_guide_preferences.get(
                        "questions", []
                    )
                    if guide_qs:
                        opening_questions = [
                            q if isinstance(q, str) else q.get("question", str(q))
                            for q in guide_qs
                        ]

        # Fetch Candidate CV
        cv_stmt = (
            select(CandidateCVModel)
            .order_by(CandidateCVModel.created_at.desc())
            .limit(1)
        )
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
        db: AsyncSession,
        application_id: int | None,
        persona: str,
        question_mode: str = "TEXT_CONVERSATIONAL",
    ) -> InterviewSessionModel:
        ctx = await InterviewSimulatorService.get_context_for_application(
            db, application_id
        )
        persona_enum = (
            InterviewPersona(persona)
            if persona in InterviewPersona.__members__
            else InterviewPersona.TECHNICAL_BAR_RAISER
        )
        persona_inst = PERSONA_PROMPTS.get(
            persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        )

        first_turn = None
        if question_mode == "MULTIPLE_CHOICE":
            # Generate initial Multiple Choice challenge
            prompt = MULTIPLE_CHOICE_QUESTION_PROMPT.format(
                persona_instruction=persona_inst,
                position=ctx["position"],
                company_name=ctx["company_name"],
                job_spec=ctx["job_spec"][:1500],
                cv_summary=ctx["cv_summary"][:1500],
                turns_summary="Starting initial round.",
            )
            from app.services.postgres_tracer import PostgresTracer

            tracer = PostgresTracer()
            chat_model = await get_task_chat_model(db, task_type="INTERVIEW_GUIDE")
            parser = JsonOutputParser()

            try:
                llm_res = await _invoke_llm_adaptive(
                    chat_model,
                    [
                        SystemMessage(content=prompt),
                        HumanMessage(
                            content="Generate initial multiple choice challenge."
                        ),
                    ],
                    tracer,
                    db,
                )
                q_data = parser.parse(llm_res.content)
                raw_opts = q_data.get("options") if isinstance(q_data, dict) else None
                first_turn = {
                    "turn_index": 1,
                    "question": q_data.get(
                        "question",
                        "Which architectural strategy best provides high availability for distributed stateful services?",
                    )
                    if isinstance(q_data, dict)
                    else "Which architectural strategy best provides high availability for distributed stateful services?",
                    "question_type": "MULTIPLE_CHOICE",
                    "options": _normalize_mc_options(raw_opts),
                    "selected_option": None,
                    "user_answer": "",
                    "attempt_count": 0,
                    "evaluation": None,
                    "is_drill_down": False,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                logger.warning(
                    "LLM initial MC question generation failed: %s. Using default opening challenge.",
                    e,
                )
                first_turn = {
                    "turn_index": 1,
                    "question": "Which architectural strategy best balances low read latency and write consistency in high-traffic APIs?",
                    "question_type": "MULTIPLE_CHOICE",
                    "options": _normalize_mc_options(None),
                    "selected_option": None,
                    "user_answer": "",
                    "attempt_count": 0,
                    "evaluation": None,
                    "is_drill_down": False,
                    "created_at": datetime.now(UTC).isoformat(),
                }
        else:
            from app.services.postgres_tracer import PostgresTracer

            tracer = PostgresTracer()
            chat_model = await get_task_chat_model(db, task_type="INTERVIEW_GUIDE")
            prompt = QUESTION_GENERATION_SYSTEM_PROMPT.format(
                persona_instruction=persona_inst,
                position=ctx["position"],
                company_name=ctx["company_name"],
                job_spec=ctx["job_spec"][:1500],
                cv_summary=ctx["cv_summary"][:1500],
                turns_summary="Starting initial round. Generate a tailored opening challenge specifically testing the requirements of this role and candidate background.",
                persona_name=persona,
            )
            parser = JsonOutputParser()
            try:
                llm_res = await _invoke_llm_adaptive(
                    chat_model,
                    [
                        SystemMessage(content=prompt),
                        HumanMessage(
                            content="Generate tailored opening interview question."
                        ),
                    ],
                    tracer,
                    db,
                )
                q_data = parser.parse(llm_res.content)
                first_q = (
                    q_data.get("question")
                    if isinstance(q_data, dict)
                    else str(llm_res.content)
                )
            except Exception as e:
                logger.warning(
                    "LLM initial opening question generation failed: %s. Using default opening question.",
                    e,
                )
                first_q = (
                    ctx["opening_questions"][0]
                    if ctx.get("opening_questions")
                    else "Tell me about a complex technical challenge you engineered and how you handled key tradeoffs."
                )

            first_turn = {
                "turn_index": 1,
                "question": first_q,
                "question_type": "BEHAVIORAL_STAR",
                "options": None,
                "selected_option": None,
                "user_answer": "",
                "attempt_count": 0,
                "evaluation": None,
                "is_drill_down": False,
                "created_at": datetime.now(UTC).isoformat(),
            }

        session = InterviewSessionModel(
            application_id=application_id,
            persona=persona,
            question_mode=question_mode,
            status="IN_PROGRESS",
            turns_data=[first_turn],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def evaluate_answer(
        db: AsyncSession,
        session_id: int,
        turn_index: int,
        answer_text: str,
        selected_option: str | None = None,
    ) -> InterviewSessionModel:
        stmt = select(InterviewSessionModel).where(
            InterviewSessionModel.id == session_id
        )
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
            raise ValueError(f"Turn {turn_index} not found in session {session_id}.")

        ctx = await InterviewSimulatorService.get_context_for_application(
            db, session.application_id
        )
        persona_enum = (
            InterviewPersona(session.persona)
            if session.persona in InterviewPersona.__members__
            else InterviewPersona.TECHNICAL_BAR_RAISER
        )
        persona_inst = PERSONA_PROMPTS.get(
            persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        )

        from app.services.postgres_tracer import PostgresTracer

        tracer = PostgresTracer()

        is_mc = target_turn.get("question_type") == "MULTIPLE_CHOICE" or (
            target_turn.get("options") and len(target_turn.get("options")) > 0
        )

        if is_mc:
            raw_options = target_turn.get("options") or []
            options_lines = []
            for opt in raw_options:
                opt_key = opt.get("key", "")
                opt_text = opt.get("text", "")
                opt_expl = opt.get("explanation", "")
                line = f"- {opt_key}: {opt_text}"
                if opt_expl:
                    line += f" (Context/Explanation: {opt_expl})"
                options_lines.append(line)
            options_text = "\n".join(options_lines) or "A, B, C, D"

            prompt = MULTIPLE_CHOICE_EVALUATION_PROMPT.format(
                persona_instruction=persona_inst,
                context_info=f"Role: {ctx['position']} at {ctx['company_name']}\nJD: {ctx['job_spec'][:1000]}",
                question_asked=target_turn.get("question", ""),
                options_text=options_text,
                selected_option=selected_option
                or target_turn.get("selected_option")
                or "None specified",
                user_answer=answer_text or "No additional explanation provided.",
            )
        else:
            prompt = DECOUPLED_EVALUATION_SYSTEM_PROMPT.format(
                persona_instruction=persona_inst,
                context_info=f"Role: {ctx['position']} at {ctx['company_name']}\nJD: {ctx['job_spec'][:1000]}",
                question_asked=target_turn.get("question", ""),
                user_answer=answer_text,
            )

        chat_model = await get_task_chat_model(db, task_type="ASSESSMENT")
        parser = JsonOutputParser()
        try:
            llm_res = await _invoke_llm_adaptive(
                chat_model,
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content="Evaluate now."),
                ],
                tracer,
                db,
            )
            raw_eval = parser.parse(llm_res.content)
            eval_data = _normalize_evaluation_data(raw_eval)
        except Exception as e:
            logger.warning(
                "LLM turn evaluation failed: %s. Using standard baseline evaluation.", e
            )
            eval_data = _normalize_evaluation_data(None)

        attempt_cnt = target_turn.get("attempt_count", 0) + 1

        target_turn["user_answer"] = answer_text
        if selected_option is not None:
            target_turn["selected_option"] = selected_option
        target_turn["attempt_count"] = attempt_cnt
        target_turn["evaluation"] = eval_data
        target_turn["updated_at"] = datetime.now(UTC).isoformat()

        turns[target_turn_idx] = target_turn
        session.turns_data = turns
        flag_modified(session, "turns_data")

        # Safely recalculate overall score across evaluated turns
        evaluated_scores = []
        for t in turns:
            ev = t.get("evaluation")
            if isinstance(ev, dict) and "score" in ev:
                try:
                    s_val = float(ev["score"])
                    evaluated_scores.append(s_val)
                except (ValueError, TypeError):
                    pass
        if evaluated_scores:
            session.overall_score = round(
                sum(evaluated_scores) / len(evaluated_scores), 1
            )

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def generate_next_question(
        db: AsyncSession, session_id: int
    ) -> InterviewSessionModel:
        stmt = select(InterviewSessionModel).where(
            InterviewSessionModel.id == session_id
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        turns = list(session.turns_data or [])

        # Determine question type based on question_mode
        q_mode = (
            getattr(session, "question_mode", "TEXT_CONVERSATIONAL")
            or "TEXT_CONVERSATIONAL"
        )
        should_generate_mc = False
        if q_mode == "MULTIPLE_CHOICE":
            should_generate_mc = True
        elif q_mode == "HYBRID":
            # In hybrid mode, alternate between MC and CONVERSATIONAL
            last_turn = turns[-1] if turns else None
            if last_turn and last_turn.get("question_type") == "MULTIPLE_CHOICE":
                should_generate_mc = False
            else:
                should_generate_mc = True

        # Build concise already-asked question summary
        asked_topics = [
            f"- #{t.get('turn_index')}: {t.get('question', '')[:100]}"
            for t in turns
            if t.get("question")
        ]
        turns_summary = (
            "Already asked questions:\n" + "\n".join(asked_topics)
            if asked_topics
            else "None yet."
        )

        ctx = await InterviewSimulatorService.get_context_for_application(
            db, session.application_id
        )
        persona_enum = (
            InterviewPersona(session.persona)
            if session.persona in InterviewPersona.__members__
            else InterviewPersona.TECHNICAL_BAR_RAISER
        )
        persona_inst = PERSONA_PROMPTS.get(
            persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        )

        from app.services.postgres_tracer import PostgresTracer

        tracer = PostgresTracer()
        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_GUIDE")
        parser = JsonOutputParser()

        next_index = len(turns) + 1

        if should_generate_mc:
            prompt = MULTIPLE_CHOICE_QUESTION_PROMPT.format(
                persona_instruction=persona_inst,
                position=ctx["position"],
                company_name=ctx["company_name"],
                job_spec=ctx["job_spec"][:1500],
                cv_summary=ctx["cv_summary"][:1500],
                turns_summary=turns_summary,
            )
            try:
                llm_res = await _invoke_llm_adaptive(
                    chat_model,
                    [
                        SystemMessage(content=prompt),
                        HumanMessage(content="Generate next multiple choice question."),
                    ],
                    tracer,
                    db,
                )
                q_data = parser.parse(llm_res.content)
                raw_opts = q_data.get("options") if isinstance(q_data, dict) else None
                new_turn = {
                    "turn_index": next_index,
                    "question": q_data.get(
                        "question",
                        "Which design pattern best decouples system producers and consumers under bursty loads?",
                    )
                    if isinstance(q_data, dict)
                    else "Which design pattern best decouples system producers and consumers under bursty loads?",
                    "question_type": "MULTIPLE_CHOICE",
                    "options": _normalize_mc_options(raw_opts),
                    "selected_option": None,
                    "user_answer": "",
                    "attempt_count": 0,
                    "evaluation": None,
                    "is_drill_down": False,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                logger.warning("LLM next MC question generation failed: %s.", e)
                new_turn = {
                    "turn_index": next_index,
                    "question": "Which caching eviction policy is best suited for temporal burst access patterns?",
                    "question_type": "MULTIPLE_CHOICE",
                    "options": _normalize_mc_options(None),
                    "selected_option": None,
                    "user_answer": "",
                    "attempt_count": 0,
                    "evaluation": None,
                    "is_drill_down": False,
                    "created_at": datetime.now(UTC).isoformat(),
                }
        else:
            prompt = QUESTION_GENERATION_SYSTEM_PROMPT.format(
                persona_instruction=persona_inst,
                position=ctx["position"],
                company_name=ctx["company_name"],
                job_spec=ctx["job_spec"][:1500],
                cv_summary=ctx["cv_summary"][:1500],
                turns_summary=turns_summary,
                persona_name=session.persona,
            )
            try:
                llm_res = await _invoke_llm_adaptive(
                    chat_model,
                    [
                        SystemMessage(content=prompt),
                        HumanMessage(content="Generate next question."),
                    ],
                    tracer,
                    db,
                )
                q_data = parser.parse(llm_res.content)
                next_q = (
                    q_data.get(
                        "question", "Tell me about a project you are most proud of."
                    )
                    if isinstance(q_data, dict)
                    else "Tell me about a project you are most proud of."
                )
            except Exception as e:
                logger.warning(
                    "LLM next conversational question generation failed: %s.", e
                )
                next_q = "Tell me about a challenging project and how you engineered the solution."

            new_turn = {
                "turn_index": next_index,
                "question": next_q,
                "question_type": "BEHAVIORAL_STAR",
                "options": None,
                "selected_option": None,
                "user_answer": "",
                "attempt_count": 0,
                "evaluation": None,
                "is_drill_down": False,
                "created_at": datetime.now(UTC).isoformat(),
            }

        turns.append(new_turn)
        session.turns_data = turns
        flag_modified(session, "turns_data")

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def generate_drill_down(
        db: AsyncSession, session_id: int, turn_index: int | None = None
    ) -> InterviewSessionModel:
        stmt = select(InterviewSessionModel).where(
            InterviewSessionModel.id == session_id
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        turns = list(session.turns_data or [])
        if not turns:
            return await InterviewSimulatorService.generate_next_question(
                db, session_id
            )

        last_turn = turns[-1]
        if turn_index:
            for t in turns:
                if t.get("turn_index") == turn_index:
                    last_turn = t
                    break

        last_eval = last_turn.get("evaluation") or {}
        gaps = last_eval.get(
            "missing_gaps", ["Details on technical tradeoffs and metrics."]
        )

        persona_enum = (
            InterviewPersona(session.persona)
            if session.persona in InterviewPersona.__members__
            else InterviewPersona.TECHNICAL_BAR_RAISER
        )
        persona_inst = PERSONA_PROMPTS.get(
            persona_enum, PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        )

        prompt = DRILL_DOWN_SYSTEM_PROMPT.format(
            persona_instruction=persona_inst,
            last_question=last_turn.get("question", ""),
            last_answer=last_turn.get("user_answer", "N/A"),
            missing_gaps=", ".join(gaps) if isinstance(gaps, list) else str(gaps),
        )

        from app.services.postgres_tracer import PostgresTracer

        tracer = PostgresTracer()

        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_GUIDE")
        parser = JsonOutputParser()
        try:
            llm_res = await _invoke_llm_adaptive(
                chat_model,
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content="Generate drill-down question."),
                ],
                tracer,
                db,
            )
            q_data = parser.parse(llm_res.content)
            dd_q = (
                q_data.get(
                    "question",
                    "Can you elaborate on the technical tradeoffs you considered?",
                )
                if isinstance(q_data, dict)
                else "Can you elaborate on the technical tradeoffs you considered?"
            )
        except Exception as e:
            logger.warning("LLM drill-down generation failed: %s.", e)
            dd_q = "Can you walk through how you handled system failures or edge cases during that project?"

        next_index = len(turns) + 1
        new_turn = {
            "turn_index": next_index,
            "question": dd_q,
            "question_type": "DRILL_DOWN",
            "options": None,
            "selected_option": None,
            "user_answer": "",
            "attempt_count": 0,
            "evaluation": None,
            "is_drill_down": True,
            "created_at": datetime.now(UTC).isoformat(),
        }

        turns.append(new_turn)
        session.turns_data = turns
        flag_modified(session, "turns_data")

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def finalize_session(db: AsyncSession, session_id: int) -> dict[str, Any]:
        stmt = select(InterviewSessionModel).where(
            InterviewSessionModel.id == session_id
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")

        turns = list(session.turns_data or [])
        evaluated_scores = []
        for t in turns:
            ev = t.get("evaluation")
            if isinstance(ev, dict) and "score" in ev:
                try:
                    s_val = float(ev["score"])
                    evaluated_scores.append(s_val)
                except (ValueError, TypeError):
                    pass

        if evaluated_scores:
            overall = round(sum(evaluated_scores) / len(evaluated_scores), 1)
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
                "key_strengths": list(set(all_strengths))[:3]
                or ["Demonstrates solid engineering context."],
                "top_improvement_areas": list(set(all_gaps))[:3]
                or ["Include more quantitative metrics in responses."],
                "total_questions_evaluated": len(evaluated_scores),
            }
        else:
            overall = None
            readiness = "INCOMPLETE"
            summary_feedback = {
                "key_strengths": [
                    "Session was ended early before any questions were answered."
                ],
                "top_improvement_areas": [
                    "Answer simulation challenges to receive structured STAR feedback and readiness scoring."
                ],
                "total_questions_evaluated": 0,
            }

        session.overall_score = overall
        session.readiness_rating = readiness
        session.summary_feedback = summary_feedback
        session.status = "COMPLETED"
        session.completed_at = datetime.now(UTC)

        timeline_event_id = None
        if session.application_id and evaluated_scores:
            event = ApplicationEventModel(
                email_application_id=session.application_id,
                email_event_type="INTERVIEW",
                email_subject=f"Completed Mock Interview ({session.persona})",
                email_summary=f"Completed Mock Interview simulation with score {int(overall or 0)}/100 ({readiness}).",
                email_received_at=datetime.now(UTC),
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
        db: AsyncSession, session_id: int, custom_markdown: str | None = None
    ) -> ApplicationModel:
        stmt = select(InterviewSessionModel).where(
            InterviewSessionModel.id == session_id
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session or not session.application_id:
            raise ValueError(
                f"Valid interview session with application_id required for session {session_id}."
            )

        app_stmt = select(ApplicationModel).where(
            ApplicationModel.id == session.application_id
        )
        app_res = await db.execute(app_stmt)
        app_model = app_res.scalar_one_or_none()
        if not app_model:
            raise ValueError(f"Application {session.application_id} not found.")

        if custom_markdown:
            formatted_notes = custom_markdown
        else:
            fb = session.summary_feedback or {}
            strengths_list = "\n".join([f"- {s}" for s in fb.get("key_strengths", [])])
            gaps_list = "\n".join(
                [f"- {g}" for g in fb.get("top_improvement_areas", [])]
            )

            formatted_notes = f"""### Mock Interview Debrief ({session.persona})
**Date**: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}
**Readiness Rating**: {session.readiness_rating or "N/A"} (Score: {session.overall_score or 0}/100)

#### Top Strengths
{strengths_list if strengths_list else "- Solid participation."}

#### Priority Prep Gaps
{gaps_list if gaps_list else "- Continue refining STAR structure."}
"""

        existing_notes = app_model.notes or ""
        app_model.notes = (existing_notes + "\n\n" + formatted_notes).strip()
        db.add(app_model)
        await db.commit()
        await db.refresh(app_model)
        return app_model

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: int) -> None:
        stmt = select(InterviewSessionModel).where(
            InterviewSessionModel.id == session_id
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"Interview session {session_id} not found.")
        await db.delete(session)
        await db.commit()
