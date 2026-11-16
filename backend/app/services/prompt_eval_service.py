"""Concurrency-aware golden LLM evaluation service used by CLI scripts, pytest, and Settings Prompt Studio."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.core.database as db_module
from app.core.llm_factory import get_task_chat_model
from app.core.prompts import DEFAULT_PROMPTS, get_prompt_template, prompt_overrides
from app.models.ai_providers import AIProviderModel
from app.models.system_design import SystemDesignChallengeModel
from app.schemas.analytics import RoleAlignmentDossierPayload
from app.schemas.system_design import (
    CanvasDiagramSubmitRequest,
    DiagramCoachChatRequest,
)
from app.services.llm import (
    anonymize_and_parse_cv,
    assess_job_posting,
    extract_email_info,
    extract_job_spec,
    generate_application_answers,
    generate_cover_letter,
    resolve_email_match_tiebreaker,
)
from app.services.role_alignment_dossier_service import _extract_json_block
from app.services.system_design_service import SystemDesignService
from app.tests.golden.pipeline_golden import GOLDEN_PIPELINE_SCENARIOS
from app.tests.golden.system_design_golden import GOLDEN_SYSTEM_DESIGN_SCENARIOS

ALL_PIPELINES: tuple[str, ...] = (
    "system_design",
    "jd_extraction",
    "assessment",
    "email_extraction",
    "email_match_tiebreaker",
    "cover_letter",
    "application_qa",
    "cv_anonymization",
    "role_alignment_dossier",
    "interview_star_eval",
    "interview_mc_generator",
    "interview_mc_eval",
    "interview_drilldown",
    "interview_question_gen",
    "llm_judge",
    "agent_system",
    "system_design_interviewer",
    "system_design_coach",
)

PROMPT_TO_PIPELINE: dict[str, str] = {
    "jd_extraction": "jd_extraction",
    "assessment": "assessment",
    "email_extraction": "email_extraction",
    "email_match_tiebreaker": "email_match_tiebreaker",
    "cover_letter": "cover_letter",
    "application_qa": "application_qa",
    "cv_anonymization": "cv_anonymization",
    "role_alignment_dossier": "role_alignment_dossier",
    "interview_star_eval": "interview_star_eval",
    "interview_mc_generator": "interview_mc_generator",
    "interview_mc_eval": "interview_mc_eval",
    "interview_drilldown": "interview_drilldown",
    "interview_question_gen": "interview_question_gen",
    "llm_judge": "llm_judge",
    "agent_system": "agent_system",
    "system_design_interviewer": "system_design_interviewer",
    "system_design_reviewer": "system_design",
    "system_design_coach": "system_design_coach",
}


def get_golden_cases_count(prompt_name: str) -> int:
    """Return number of golden benchmark cases available for a prompt key."""
    pipeline = PROMPT_TO_PIPELINE.get(prompt_name)
    if not pipeline:
        return 0
    if pipeline == "system_design":
        return len(GOLDEN_SYSTEM_DESIGN_SCENARIOS)
    return sum(1 for sc in GOLDEN_PIPELINE_SCENARIOS if sc["pipeline"] == pipeline)


async def resolve_db_provider_concurrency(db: AsyncSession) -> tuple[int, str]:
    """Read active AI provider max_concurrency directly from DB without loopback HTTP."""
    stmt = select(AIProviderModel).order_by(AIProviderModel.id.asc())
    providers = (await db.execute(stmt)).scalars().all()
    active = [p for p in providers if p.is_active] or list(providers)
    if active and int(active[0].max_concurrency or 0) >= 1:
        return int(active[0].max_concurrency), f"provider:{active[0].name}"
    return 1, "fallback"


async def evaluate_system_design_inprocess(
    scenario: dict[str, Any], db: AsyncSession
) -> dict[str, Any]:
    """Evaluate one System Design blueprint scenario in-process (honors prompt_overrides contextvar)."""
    t0 = time.time()
    await SystemDesignService._ensure_challenges_seeded(db)
    challenge = (
        await db.execute(
            select(SystemDesignChallengeModel).where(
                SystemDesignChallengeModel.slug == scenario["challenge_slug"]
            )
        )
    ).scalar_one()

    sess = await SystemDesignService.start_session(
        db,
        challenge_id=int(challenge.id),
        mode="ADAPTIVE",
        variant_id=scenario.get("variant_id"),
    )
    sid = int(sess.id)
    failures: list[str] = []
    rev_secs = 0.0
    eval_secs = 0.0
    score = 0.0
    rating = ""

    try:
        await SystemDesignService.reveal_requirements_ledger(
            db, sid, lock_and_proceed=True
        )
        await SystemDesignService.submit_canvas_diagram(
            db,
            sid,
            CanvasDiagramSubmitRequest(
                nodes=scenario["nodes"],
                edges=scenario["edges"],
                notes=scenario.get("canvas_notes", ""),
            ),
        )
        t_rev = time.time()
        ctx_rev = await SystemDesignService.prepare_diagram_review_context(
            db, sid, use_web_search=False
        )
        inf_rev = await SystemDesignService.run_diagram_vlm_inference(db, ctx_rev)
        await SystemDesignService.persist_architecture_review(
            db, sid, inf_rev["review"]
        )
        rev_secs = round(time.time() - t_rev, 1)
        rev = inf_rev["review"] or {}

        missing_text = " ".join(rev.get("missing_components") or []).lower()
        complexity_text = " ".join(rev.get("unnecessary_complexity") or []).lower()
        for bad_term in scenario.get("forbidden_false_missing", []):
            if bad_term.lower() in missing_text:
                failures.append(
                    f"False missing component penalty: '{bad_term}' in {rev.get('missing_components')}"
                )
        for bad_term in scenario.get("forbidden_false_complexity", []):
            if bad_term.lower() in complexity_text:
                failures.append(
                    f"False complexity penalty: '{bad_term}' in {rev.get('unnecessary_complexity')}"
                )

        await SystemDesignService.send_defence_message(
            db, sid, scenario["defence_answer"]
        )
        t_eval = time.time()
        ctx_eval = await SystemDesignService.prepare_final_evaluation_context(db, sid)
        inf_eval = await SystemDesignService.run_final_evaluation_inference(
            db, ctx_eval
        )
        s_fin = await SystemDesignService.persist_final_evaluation(
            db, sid, inf_eval["evaluation"]
        )
        eval_secs = round(time.time() - t_eval, 1)
        score = float(s_fin.overall_score or 0.0)
        rating = str(s_fin.readiness_rating or "")
        if score < scenario["min_final_score"] or score > scenario["max_final_score"]:
            failures.append(
                f"Score {score} out of expected band [{scenario['min_final_score']}, {scenario['max_final_score']}]"
            )
    finally:
        try:
            await SystemDesignService.delete_session(db, sid)
        except Exception:
            pass

    return {
        "id": scenario["id"],
        "pipeline": "system_design",
        "passed": len(failures) == 0,
        "elapsed_secs": round(time.time() - t0, 1),
        "details": {
            "score": score,
            "rating": rating,
            "rev_secs": rev_secs,
            "eval_secs": eval_secs,
        },
        "failures": failures,
    }


async def evaluate_pipeline_scenario(
    scenario: dict[str, Any], db: AsyncSession
) -> dict[str, Any]:
    """Run one non-SD-review golden scenario against the live async service & active LLM."""
    t0 = time.time()
    pipeline = scenario["pipeline"]
    failures: list[str] = []
    details: dict[str, Any] = {}

    if pipeline == "jd_extraction":
        res = await extract_job_spec(
            db,
            scenario["raw_webpage_data"],
            title_hint=scenario.get("title_hint"),
            page_title=scenario.get("page_title"),
        )
        details = {
            "job_found": res.job_found,
            "company": res.company,
            "skills_count": len(res.extracted_skills),
            "salary_min": res.salary_min,
            "salary_max": res.salary_max,
        }
        if bool(res.job_found) != bool(scenario["expect_job_found"]):
            failures.append(
                f"Expected job_found={scenario['expect_job_found']}, got {res.job_found}"
            )
        if scenario["expect_job_found"]:
            exp_company = scenario.get("expected_company")
            if exp_company and exp_company.lower() not in (res.company or "").lower():
                failures.append(
                    f"Expected company '{exp_company}', got {res.company!r}"
                )
            for banned_comp in scenario.get("banned_companies") or []:
                if (res.company or "").strip().lower() == banned_comp.lower():
                    failures.append(
                        f"Extracted forbidden non-company value: {res.company!r}"
                    )
            skills_blob = " ".join(res.extracted_skills).lower()
            req_any = scenario.get("required_skills_any") or []
            if req_any and not any(s.lower() in skills_blob for s in req_any):
                failures.append(
                    f"None of {req_any} found in extracted_skills={res.extracted_skills}"
                )
            exp_min = scenario.get("expected_salary_min")
            exp_max = scenario.get("expected_salary_max")
            if exp_min is not None and res.salary_min != exp_min:
                failures.append(f"Expected salary_min={exp_min}, got {res.salary_min}")
            if exp_max is not None and res.salary_max != exp_max:
                failures.append(f"Expected salary_max={exp_max}, got {res.salary_max}")
            exp_cur = scenario.get("expected_currency")
            if exp_cur and (res.currency or "").upper() != exp_cur.upper():
                failures.append(f"Expected currency={exp_cur}, got {res.currency!r}")
            exp_per = scenario.get("expected_salary_period")
            if exp_per and (res.salary_period or "").upper() != exp_per.upper():
                failures.append(
                    f"Expected salary_period={exp_per}, got {res.salary_period!r}"
                )
            for field_name in scenario.get("must_be_null_if_unstated") or []:
                if getattr(res, field_name, None):
                    failures.append(
                        f"Expected '{field_name}' null when unstated, got {getattr(res, field_name)!r}"
                    )

    elif pipeline == "assessment":
        res = await assess_job_posting(
            db,
            job_description=scenario["job_description"],
            candidate_skills=scenario.get("candidate_skills"),
            candidate_cv=scenario.get("candidate_cv"),
            candidate_spoken_languages=scenario.get("candidate_spoken_languages"),
            candidate_years_of_experience=scenario.get("candidate_years_of_experience"),
            programmatic_baseline=scenario.get("programmatic_baseline"),
            matching_skills=scenario.get("matching_skills"),
            missing_skills=scenario.get("missing_skills"),
        )
        lang_res = res.language_match
        details = {
            "fit_score": res.fit_score,
            "recommendation": res.recommendation,
            "seniority_fit": res.seniority_fit,
            "lang_matched": lang_res.is_matched if lang_res else None,
            "missing_mandatory_langs": lang_res.missing_mandatory if lang_res else [],
        }
        if (
            res.fit_score < scenario["min_score"]
            or res.fit_score > scenario["max_score"]
        ):
            failures.append(
                f"fit_score {res.fit_score} out of [{scenario['min_score']}, {scenario['max_score']}]"
            )
        allowed_recs = scenario.get("allowed_recommendations") or []
        if allowed_recs and res.recommendation not in allowed_recs:
            failures.append(
                f"recommendation '{res.recommendation}' not in {allowed_recs}"
            )
        exp_seniority = scenario.get("expected_seniority_fit")
        if exp_seniority and (res.seniority_fit or "").upper() != exp_seniority.upper():
            failures.append(
                f"Expected seniority_fit={exp_seniority}, got {res.seniority_fit!r}"
            )
        exp_lang_match = scenario.get("expect_language_matched")
        if exp_lang_match is not None and lang_res is not None:
            if bool(lang_res.is_matched) != bool(exp_lang_match):
                failures.append(
                    f"Expected language_match.is_matched={exp_lang_match}, got {lang_res.is_matched} (missing={lang_res.missing_mandatory})"
                )
        if "expect_missing_mandatory_langs" in scenario and lang_res is not None:
            if (lang_res.missing_mandatory or []) != scenario[
                "expect_missing_mandatory_langs"
            ]:
                failures.append(
                    f"Expected missing_mandatory={scenario['expect_missing_mandatory_langs']}, got {lang_res.missing_mandatory}"
                )
        req_missing_langs = scenario.get("expect_missing_mandatory_any") or []
        if req_missing_langs and lang_res is not None:
            mm_blob = " ".join(
                (lang_res.missing_mandatory or []) + (res.critical_risks or [])
            ).lower()
            if not any(t.lower() in mm_blob for t in req_missing_langs):
                failures.append(
                    f"Expected {req_missing_langs} in missing_mandatory/risks, got {lang_res.missing_mandatory}"
                )
        banned_risks = scenario.get("banned_risk_substrings") or []
        if banned_risks:
            risk_blob = " ".join(
                (res.critical_risks or [])
                + (res.cons or [])
                + ([lang_res.warning] if lang_res and lang_res.warning else [])
                + (lang_res.missing_mandatory if lang_res else [])
            ).lower()
            for b in banned_risks:
                if b.lower() in risk_blob:
                    failures.append(f"Banned false risk leaked: '{b}'")
        gap_terms = scenario.get("expect_gap_terms_any") or []
        if gap_terms:
            gap_blob = " ".join(
                (res.missing_skills or [])
                + (res.critical_risks or [])
                + (res.cons or [])
                + [res.match_summary or ""]
            ).lower()
            if not any(term.lower() in gap_blob for term in gap_terms):
                failures.append(
                    f"None of expected gap terms {gap_terms} surfaced in assessment gaps"
                )
        if scenario.get("ban_pseudo_risks"):
            for r in res.critical_risks or []:
                rl = str(r).strip().lower()
                if rl.startswith("no critical risk") or rl == "none":
                    failures.append(f"Pseudo-risk leaked: {r!r}")
        for banned_comp in scenario.get("banned_companies") or []:
            if (res.company or "").strip().lower() == banned_comp.lower():
                failures.append(
                    f"Assessment leaked forbidden non-company value: {res.company!r}"
                )

    elif pipeline == "email_extraction":
        res = await extract_email_info(
            db,
            scenario["email_content"],
            sender=scenario.get("sender"),
            subject=scenario.get("subject"),
            date=scenario.get("date"),
        )
        details = {
            "email_type": res.email_type,
            "company": res.company,
            "status": res.status,
            "action_required": res.action_required,
            "due_date": res.due_date,
        }
        if bool(res.action_required) != bool(scenario["expect_action_required"]):
            failures.append(
                f"Expected action_required={scenario['expect_action_required']}, got {res.action_required}"
            )
        exp_company = scenario.get("expect_company")
        if exp_company and exp_company.lower() not in (res.company or "").lower():
            failures.append(f"Expected company '{exp_company}', got {res.company!r}")
        exp_status = scenario.get("expected_status_any") or []
        if exp_status and (res.status or "").upper() not in [
            s.upper() for s in exp_status
        ]:
            failures.append(f"Expected status in {exp_status}, got {res.status!r}")
        for banned_st in scenario.get("banned_status_values") or []:
            if (res.status or "").upper() == banned_st.upper():
                failures.append(
                    f"Thread-isolation leak: got banned status {res.status!r}"
                )
        for fld in scenario.get("expect_non_empty_fields") or []:
            if not getattr(res, fld, None):
                failures.append(f"Expected non-empty '{fld}', got None/empty")
        for fld in scenario.get("expect_null_fields") or []:
            if getattr(res, fld, None) not in (None, ""):
                failures.append(f"Expected null '{fld}', got {getattr(res, fld)!r}")

    elif pipeline == "email_match_tiebreaker":
        res = await resolve_email_match_tiebreaker(
            db,
            sender=scenario.get("sender"),
            subject=scenario.get("subject"),
            summary=scenario.get("summary"),
            extracted_company=scenario.get("extracted_company"),
            extracted_position=scenario.get("extracted_position"),
            candidates=scenario["candidates"],
        )
        details = {
            "matched_application_id": res.matched_application_id,
            "confidence": res.confidence,
            "reason": res.reason,
        }
        exp_id = scenario.get("expected_application_id")
        if exp_id is None:
            if (
                res.matched_application_id is not None
                and float(res.confidence or 0.0) >= 0.85
            ):
                failures.append(
                    f"Expected no confident match (null or confidence < 0.85), got id={res.matched_application_id} ({res.confidence})"
                )
        else:
            if res.matched_application_id != exp_id:
                failures.append(
                    f"Expected matched_application_id={exp_id}, got {res.matched_application_id}"
                )
            min_conf = scenario.get("min_confidence")
            if min_conf is not None and float(res.confidence or 0.0) < float(min_conf):
                failures.append(f"Confidence {res.confidence} below minimum {min_conf}")

    elif pipeline == "cover_letter":
        text = await generate_cover_letter(
            db,
            company_name=scenario["company_name"],
            position=scenario["position"],
            job_description=scenario["job_description"],
            candidate_cv=scenario["candidate_cv"],
            company_research=scenario.get("company_research"),
        )
        low = text.lower()
        details = {"length": len(text)}
        if len(text.strip()) < 100:
            failures.append(
                f"Cover letter suspiciously short ({len(text.strip())} chars)"
            )
        must_any = scenario.get("must_include_any") or []
        if must_any and not any(t.lower() in low for t in must_any):
            failures.append(f"None of grounded terms {must_any} found in cover letter")
        for bad in scenario.get("must_not_claim_unverified") or []:
            if bad.lower() in low:
                failures.append(f"Fabricated unverified claim detected: '{bad}'")
        if scenario.get("ban_unverified_percentages"):
            pct_hits = re.findall(r"\b\d+(?:\.\d+)?%", text)
            if pct_hits:
                failures.append(
                    f"Fabricated unverified percentage metric(s): {pct_hits}"
                )

    elif pipeline == "application_qa":
        answers = await generate_application_answers(
            db,
            company_name=scenario["company_name"],
            position=scenario["position"],
            job_description=scenario["job_description"],
            candidate_cv=scenario["candidate_cv"],
            questions=scenario["questions"],
            company_research=scenario.get("company_research"),
        )
        details = {"answers_count": len(answers)}
        if len(answers) < len(scenario["questions"]):
            failures.append(
                f"Expected {len(scenario['questions'])} answers, got {len(answers)}"
            )
        else:
            a1 = str(answers[0].get("answer") or "")
            a1_low = a1.lower()
            if not any(
                t.lower() in a1_low for t in scenario.get("q1_must_include_any") or []
            ):
                failures.append("Answer 1 did not cite any grounded CV/research term")
            max_w = scenario.get("max_words_q1")
            if max_w is not None and len(a1.split()) > int(max_w):
                failures.append(
                    f"Answer 1 exceeded max_words_q1={max_w}: got {len(a1.split())} words"
                )
            if scenario.get("ban_unverified_percentages"):
                pct_hits = re.findall(r"\b\d+(?:\.\d+)?%", a1)
                if pct_hits:
                    failures.append(
                        f"Answer 1 fabricated unverified percentage metric(s): {pct_hits}"
                    )
            if len(answers) >= 2:
                a2_low = str(answers[1].get("answer") or "").lower()
                gap_any = scenario.get("q2_must_acknowledge_gap_any") or []
                if gap_any and not any(t in a2_low for t in gap_any):
                    failures.append(
                        f"Answer 2 did not honestly acknowledge missing gap: {a2_low[:200]}"
                    )
                for bad in scenario.get("q2_must_not_claim") or []:
                    if bad.lower() in a2_low:
                        failures.append(
                            f"Answer 2 fabricated unverified claim: '{bad}'"
                        )

    elif pipeline == "cv_anonymization":
        res = await anonymize_and_parse_cv(db, scenario["raw_cv_text"])
        anon_low = (res.anonymized_resume or "").lower()
        details = {
            "skills_count": len(res.extracted_skills or []),
            "years_of_experience": res.total_years_experience,
        }
        for banned in scenario.get("banned_pii_terms") or []:
            if banned.lower() in anon_low:
                failures.append(f"PII leak survived in anonymized_resume: '{banned}'")
        skills_blob = " ".join(res.extracted_skills or []).lower()
        req_any = scenario.get("expected_skills_any") or []
        if req_any and not any(s.lower() in skills_blob for s in req_any):
            failures.append(
                f"None of {req_any} found in extracted_skills={res.extracted_skills}"
            )
        yoe = float(res.total_years_experience or 0.0)
        if yoe < float(scenario["min_years"]) or yoe > float(scenario["max_years"]):
            failures.append(
                f"years_of_experience {yoe} out of [{scenario['min_years']}, {scenario['max_years']}]"
            )

    elif pipeline == "role_alignment_dossier":
        template_str = await get_prompt_template(db, "role_alignment_dossier")
        prompt_tmpl = ChatPromptTemplate.from_template(template_str)
        cv_ctx = {
            "summary": "Backend & AI Engineer",
            "years_of_experience": scenario.get("candidate_years_of_experience"),
            "extracted_skills": scenario.get("candidate_skills") or [],
            "anonymized_text": scenario.get("candidate_cv") or "",
        }
        mkt_ctx = {
            "target_track": scenario["role_track"],
            "total_analyzed_jobs": scenario["total_analyzed_jobs"],
            "top_vocabulary_shifts": scenario.get("vocabulary_shifts") or [],
            "top_bullet_reframes": scenario.get("bullet_reframes") or [],
        }
        msgs = prompt_tmpl.format_messages(
            role_track=scenario["role_track"].upper(),
            candidate_cv=json.dumps(cv_ctx, indent=2),
            market_context=json.dumps(mkt_ctx, indent=2),
        )
        chat_model = await get_task_chat_model(db, task_type="ROLE_ALIGNMENT_DOSSIER")
        llm_res = await chat_model.ainvoke(msgs)
        raw_txt = getattr(llm_res, "content", str(llm_res))
        if isinstance(raw_txt, list):
            raw_txt = "".join(
                p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_txt
            )
        parsed = _extract_json_block(raw_txt)
        dossier_payload = RoleAlignmentDossierPayload.model_validate(parsed)
        details = {
            "bullet_rewrites": len(dossier_payload.bullet_rewrites),
            "talking_points": len(dossier_payload.talking_points),
        }
        if not dossier_payload.executive_fit.positioning_summary.strip():
            failures.append("Empty positioning_summary in dossier")
        if scenario.get("ban_unverified_percentages"):
            rewritten_blob = " ".join(
                b.rewritten_bullet for b in dossier_payload.bullet_rewrites
            )
            pct_hits = re.findall(r"\b\d+(?:\.\d+)?%", rewritten_blob)
            if pct_hits:
                failures.append(
                    f"Fabricated unverified percentage metric(s) in dossier bullet_rewrites: {pct_hits}"
                )

    elif pipeline == "interview_star_eval":
        from app.services.interview_simulator_service import (
            DECOUPLED_EVALUATION_SYSTEM_PROMPT,
            PERSONA_PROMPTS,
            InterviewPersona,
            _format_prompt_from_db,
            _invoke_llm_adaptive,
            _normalize_evaluation_data,
        )
        from app.services.postgres_tracer import PostgresTracer

        persona_inst = PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        prompt = await _format_prompt_from_db(
            db,
            "interview_star_eval",
            DECOUPLED_EVALUATION_SYSTEM_PROMPT,
            persona_instruction=persona_inst,
            context_info=f"Role: {scenario['position']} at {scenario['company_name']}\nJD: {scenario['job_spec']}",
            question_asked=scenario["question_asked"],
            user_answer=scenario["user_answer"],
        )
        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_STAR_EVAL")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [SystemMessage(content=prompt), HumanMessage(content="Evaluate now.")],
            PostgresTracer(),
            db,
        )
        raw_eval = JsonOutputParser().parse(llm_res.content)
        eval_data = _normalize_evaluation_data(raw_eval)
        score = float(eval_data.get("overall_score") or eval_data.get("score") or 0.0)
        details = {
            "score": score,
            "rubric_scores": eval_data.get("rubric_scores"),
        }
        if score < float(scenario["min_score"]) or score > float(scenario["max_score"]):
            failures.append(
                f"STAR score {score} out of [{scenario['min_score']}, {scenario['max_score']}]"
            )

    elif pipeline == "system_design_interviewer":
        await SystemDesignService._ensure_challenges_seeded(db)
        ch = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.slug == scenario["challenge_slug"]
                )
            )
        ).scalar_one()
        sess = await SystemDesignService.start_session(
            db,
            challenge_id=int(ch.id),
            mode="ADAPTIVE",
            variant_id=scenario.get("variant_id"),
        )
        sid = int(sess.id)
        try:
            updated = await SystemDesignService.send_requirements_message(
                db,
                sid,
                scenario["candidate_message"],
                request_hint=bool(scenario.get("request_hint", False)),
            )
            turns = [
                t
                for t in (updated.requirements_transcript or [])
                if t.get("role") == "interviewer"
            ]
            reply = str(turns[-1]["content"] if turns else "").strip()
            details = {"reply_len": len(reply)}
            low = reply.lower()
            must_any = scenario.get("must_include_any") or []
            if must_any and not any(t.lower() in low for t in must_any):
                failures.append(
                    f"Interviewer reply did not include expected signal {must_any}: {reply[:200]}"
                )
            for bad in scenario.get("must_not_contain_any") or []:
                if bad.lower() in low:
                    failures.append(
                        f"Interviewer reply contained banned phrase: '{bad}'"
                    )
        finally:
            try:
                await SystemDesignService.delete_session(db, sid)
            except Exception:
                pass

    elif pipeline == "system_design_coach":
        await SystemDesignService._ensure_challenges_seeded(db)
        ch = (
            await db.execute(
                select(SystemDesignChallengeModel).where(
                    SystemDesignChallengeModel.slug == scenario["challenge_slug"]
                )
            )
        ).scalar_one()
        sess = await SystemDesignService.start_session(
            db,
            challenge_id=int(ch.id),
            mode="ADAPTIVE",
            variant_id=scenario.get("variant_id"),
        )
        sid = int(sess.id)
        try:
            await SystemDesignService.reveal_requirements_ledger(
                db, sid, lock_and_proceed=True
            )
            coach_res = await SystemDesignService.send_diagram_coach_message(
                db,
                sid,
                DiagramCoachChatRequest(
                    message=scenario["message"],
                    cloud_provider=scenario.get("cloud_provider", "generic"),
                    current_nodes=scenario.get("current_nodes") or [],
                    current_edges=scenario.get("current_edges") or [],
                    current_notes=scenario.get("current_notes") or "",
                ),
            )
            reply = str(coach_res.reply or "").strip()
            actions = list(coach_res.suggested_actions or [])
            details = {"reply_len": len(reply), "actions_count": len(actions)}
            low = reply.lower()
            must_any = scenario.get("must_include_any") or []
            if must_any and not any(t.lower() in low for t in must_any):
                failures.append(
                    f"Coach reply missed expected guidance keywords {must_any}: {reply[:200]}"
                )
            if scenario.get("require_suggested_actions") and not actions:
                failures.append("Expected non-empty suggested_actions from Coach")
        finally:
            try:
                await SystemDesignService.delete_session(db, sid)
            except Exception:
                pass

    elif pipeline == "llm_judge":
        from app.services.llm_judge import audit_generation_grounding

        audit = await audit_generation_grounding(
            db,
            candidate_cv=scenario.get("candidate_cv") or "",
            generated_text=scenario["generated_text"],
            context_label=scenario["context_label"],
            task_type=scenario["task_type"],
            target_context=scenario.get("target_context"),
        )
        details = {
            "passed": audit.passed,
            "confidence": audit.confidence_score,
            "claims_count": len(audit.unverified_claims or []),
        }
        if bool(audit.passed) != bool(scenario["expected_passed"]):
            failures.append(
                f"Expected passed={scenario['expected_passed']}, got {audit.passed} "
                f"(claims={audit.unverified_claims}, critique={audit.critique[:180]})"
            )
        min_claims = int(scenario.get("expected_claims_count_min") or 0)
        if min_claims and len(audit.unverified_claims or []) < min_claims:
            failures.append(
                f"Expected >= {min_claims} unverified_claims, got {audit.unverified_claims}"
            )
        if scenario.get("expected_passed") and (audit.unverified_claims or []):
            failures.append(
                f"Passed audit must not list unverified_claims: {audit.unverified_claims}"
            )

    elif pipeline == "agent_system":
        from app.services.agent_tools import create_agent_tools

        sys_prompt = await get_prompt_template(db, "agent_system")
        tools = create_agent_tools(db, enable_web_search=True)
        chat_model = await get_task_chat_model(
            db, task_type="AGENT_CHAT", temperature=0.0
        )
        bound = chat_model.bind_tools(tools)
        response = await bound.ainvoke(
            [
                SystemMessage(content=sys_prompt),
                HumanMessage(content=scenario["user_prompt"]),
            ]
        )
        tool_calls = getattr(response, "tool_calls", None) or []
        called_names = [
            tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            for tc in tool_calls
        ]
        details = {"called_tools": called_names}
        expected_any = scenario.get("expected_tools_any") or []
        if not called_names:
            failures.append("Agent did not emit any tool calls")
        elif expected_any and not any(t in expected_any for t in called_names):
            failures.append(
                f"Called tools {called_names} did not match expected {expected_any}"
            )

    elif pipeline == "interview_mc_generator":
        from app.services.interview_simulator_service import (
            MULTIPLE_CHOICE_QUESTION_PROMPT,
            PERSONA_PROMPTS,
            InterviewPersona,
            _format_prompt_from_db,
            _invoke_llm_adaptive,
        )
        from app.services.postgres_tracer import PostgresTracer

        persona_inst = PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        prompt = await _format_prompt_from_db(
            db,
            "interview_mc_generator",
            MULTIPLE_CHOICE_QUESTION_PROMPT,
            persona_instruction=persona_inst,
            position=scenario["position"],
            company_name=scenario["company_name"],
            company_research_summary="General tech engineering benchmarks.",
            job_spec=scenario["job_spec"],
            cv_summary=scenario.get("candidate_cv") or "",
            turns_summary=scenario.get("turns_summary") or "Starting initial round.",
        )
        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_MC_GENERATOR")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=prompt),
                HumanMessage(content="Generate MC question."),
            ],
            PostgresTracer(),
            db,
        )
        q_data = JsonOutputParser().parse(llm_res.content)
        opts = q_data.get("options") if isinstance(q_data, dict) else []
        ck = str((q_data or {}).get("correct_key") or "").strip().upper()
        details = {"correct_key": ck, "options_count": len(opts or [])}
        if (
            not isinstance(q_data, dict)
            or not str(q_data.get("question") or "").strip()
        ):
            failures.append("Missing question text in MC generator output")
        if not isinstance(opts, list) or len(opts) != 4:
            failures.append(f"Expected 4 MC options, got {len(opts or [])}")
        elif any(
            not str(o.get("text") or "").strip() for o in opts if isinstance(o, dict)
        ):
            failures.append("MC option contains empty text")
        if ck not in {"A", "B", "C", "D"}:
            failures.append(f"Invalid correct_key '{ck}'")
        blob = json.dumps(q_data).lower()
        kw_any = scenario.get("expected_keywords_any") or []
        if kw_any and not any(k.lower() in blob for k in kw_any):
            failures.append(f"MC challenge lacked expected domain keywords {kw_any}")

    elif pipeline == "interview_mc_eval":
        from app.services.interview_simulator_service import (
            MULTIPLE_CHOICE_EVALUATION_PROMPT,
            PERSONA_PROMPTS,
            InterviewPersona,
            _format_prompt_from_db,
            _invoke_llm_adaptive,
            _normalize_evaluation_data,
        )
        from app.services.postgres_tracer import PostgresTracer

        persona_inst = PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        prompt = await _format_prompt_from_db(
            db,
            "interview_mc_eval",
            MULTIPLE_CHOICE_EVALUATION_PROMPT,
            persona_instruction=persona_inst,
            context_info=f"Role: {scenario['position']} at {scenario['company_name']}\nJD: {scenario['job_spec']}",
            question_asked=scenario["question_asked"],
            options_text=scenario["options_text"],
            selected_option=scenario["selected_option"],
            user_answer=scenario.get("user_answer") or "",
        )
        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_MC_EVAL")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=prompt),
                HumanMessage(content="Evaluate MC selection now."),
            ],
            PostgresTracer(),
            db,
        )
        eval_data = _normalize_evaluation_data(
            JsonOutputParser().parse(llm_res.content)
        )
        score = float(eval_data.get("overall_score") or eval_data.get("score") or 0.0)
        critique = str(eval_data.get("constructive_critique") or "")
        details = {"score": score, "critique_len": len(critique)}
        if score < float(scenario["min_score"]) or score > float(scenario["max_score"]):
            failures.append(
                f"MC eval score {score} outside [{scenario['min_score']}, {scenario['max_score']}]"
            )
        crit_low = critique.lower()
        crit_any = scenario.get("expected_critique_any") or []
        if crit_any and not any(t.lower() in crit_low for t in crit_any):
            failures.append(
                f"MC eval critique missed expected signal {crit_any}: {critique[:160]}"
            )

    elif pipeline == "interview_drilldown":
        from app.services.interview_simulator_service import (
            DRILL_DOWN_SYSTEM_PROMPT,
            PERSONA_PROMPTS,
            InterviewPersona,
            _format_prompt_from_db,
            _invoke_llm_adaptive,
        )
        from app.services.postgres_tracer import PostgresTracer

        persona_inst = PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        prompt = await _format_prompt_from_db(
            db,
            "interview_drilldown",
            DRILL_DOWN_SYSTEM_PROMPT,
            persona_instruction=persona_inst,
            last_question=scenario["last_question"],
            last_answer=scenario["last_answer"],
            missing_gaps=scenario["missing_gaps"],
        )
        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_DRILLDOWN")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=prompt),
                HumanMessage(content="Generate drill-down question."),
            ],
            PostgresTracer(),
            db,
        )
        q_data = JsonOutputParser().parse(llm_res.content)
        q_text = str((q_data or {}).get("question") or "").strip()
        details = {"question_len": len(q_text)}
        if not q_text:
            failures.append("Empty drill-down question returned")
        else:
            q_low = q_text.lower()
            kw_any = scenario.get("expected_keywords_any") or []
            if kw_any and not any(k.lower() in q_low for k in kw_any):
                failures.append(
                    f"Drill-down question did not probe missing gaps {kw_any}: {q_text[:180]}"
                )

    elif pipeline == "interview_question_gen":
        from app.services.interview_simulator_service import (
            PERSONA_PROMPTS,
            QUESTION_GENERATION_SYSTEM_PROMPT,
            InterviewPersona,
            _format_prompt_from_db,
            _invoke_llm_adaptive,
        )
        from app.services.postgres_tracer import PostgresTracer

        persona_inst = PERSONA_PROMPTS[InterviewPersona.TECHNICAL_BAR_RAISER]
        prompt = await _format_prompt_from_db(
            db,
            "interview_question_gen",
            QUESTION_GENERATION_SYSTEM_PROMPT,
            persona_instruction=persona_inst,
            persona_name="Technical Bar Raiser",
            position=scenario["position"],
            company_name=scenario["company_name"],
            company_research_summary="General engineering benchmarks.",
            job_spec=scenario["job_spec"],
            cv_summary=scenario.get("candidate_cv") or "",
            turns_summary=scenario.get("turns_summary") or "",
        )
        chat_model = await get_task_chat_model(db, task_type="INTERVIEW_QUESTION_GEN")
        llm_res = await _invoke_llm_adaptive(
            chat_model,
            [
                SystemMessage(content=prompt),
                HumanMessage(content="Generate next question."),
            ],
            PostgresTracer(),
            db,
        )
        q_data = JsonOutputParser().parse(llm_res.content)
        q_text = str((q_data or {}).get("question") or "").strip()
        details = {"question_len": len(q_text)}
        if not q_text:
            failures.append("Empty generated interview question")
        else:
            q_low = q_text.lower()
            kw_any = scenario.get("expected_keywords_any") or []
            if kw_any and not any(k.lower() in q_low for k in kw_any):
                failures.append(
                    f"Generated question lacked role/CV keywords {kw_any}: {q_text[:180]}"
                )

    else:
        failures.append(f"Unknown pipeline '{pipeline}'")

    return {
        "id": scenario["id"],
        "pipeline": pipeline,
        "passed": len(failures) == 0,
        "elapsed_secs": round(time.time() - t0, 1),
        "details": details,
        "failures": failures,
    }


async def run_inprocess_pipeline_scenarios(
    pipeline: str,
    *,
    concurrency: int = 3,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    override_prompts: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run all golden scenarios for one pipeline concurrently inside the active app DB."""
    sf = session_factory or db_module.AsyncSessionLocal
    if sf is None:
        raise RuntimeError("Database session factory is not initialized.")

    is_sd = pipeline == "system_design"
    scenarios = (
        list(GOLDEN_SYSTEM_DESIGN_SCENARIOS)
        if is_sd
        else [sc for sc in GOLDEN_PIPELINE_SCENARIOS if sc["pipeline"] == pipeline]
    )
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _run_one(sc: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            with prompt_overrides(override_prompts):
                async with sf() as db:
                    try:
                        if is_sd:
                            return await evaluate_system_design_inprocess(sc, db)
                        return await evaluate_pipeline_scenario(sc, db)
                    except Exception as exc:
                        return {
                            "id": sc["id"],
                            "pipeline": pipeline,
                            "passed": False,
                            "elapsed_secs": 0.0,
                            "details": {},
                            "failures": [f"Exception: {exc}"],
                        }

    t0 = time.time()
    results = list(await asyncio.gather(*(_run_one(sc) for sc in scenarios)))
    passed = sum(1 for r in results if r["passed"])
    return {
        "pipeline": pipeline,
        "concurrency": concurrency,
        "wall_secs": round(time.time() - t0, 1),
        "passed": passed,
        "total": len(results),
        "pass_rate": round((passed / len(results)) * 100.0, 1) if results else 0.0,
        "all_passed": passed == len(results),
        "results": results,
    }


async def evaluate_prompt_against_golden(
    db: AsyncSession,
    prompt_name: str,
    *,
    candidate_template: str | None = None,
    compare_default: bool = False,
    concurrency: int | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> dict[str, Any]:
    """Evaluate a Settings Prompt Studio template against golden cases (+ optional A/B vs factory default)."""
    if prompt_name not in DEFAULT_PROMPTS:
        raise ValueError(f"Prompt '{prompt_name}' not found.")
    pipeline = PROMPT_TO_PIPELINE.get(prompt_name)
    if not pipeline:
        raise ValueError(
            f"Prompt '{prompt_name}' does not have an offline-safe golden dataset yet."
        )

    eff_conc = concurrency
    conc_source = "explicit"
    if eff_conc is None or eff_conc < 1:
        eff_conc, conc_source = await resolve_db_provider_concurrency(db)

    if candidate_template is not None and candidate_template.strip():
        cand_override = {prompt_name: candidate_template}
        cand_source = "candidate_editor"
    else:
        saved_tmpl = await get_prompt_template(db, prompt_name, force_reload=True)
        cand_override = {prompt_name: saved_tmpl}
        cand_source = "saved_db_prompt"

    cand_run = await run_inprocess_pipeline_scenarios(
        pipeline,
        concurrency=eff_conc,
        session_factory=session_factory,
        override_prompts=cand_override,
    )

    baseline_run: dict[str, Any] | None = None
    delta_passed: int | None = None
    delta_pass_rate: float | None = None
    if compare_default:
        baseline_run = await run_inprocess_pipeline_scenarios(
            pipeline,
            concurrency=eff_conc,
            session_factory=session_factory,
            override_prompts={prompt_name: DEFAULT_PROMPTS[prompt_name]},
        )
        delta_passed = cand_run["passed"] - baseline_run["passed"]
        delta_pass_rate = round(cand_run["pass_rate"] - baseline_run["pass_rate"], 1)

    return {
        "prompt_name": prompt_name,
        "pipeline": pipeline,
        "candidate_source": cand_source,
        "concurrency": eff_conc,
        "concurrency_source": conc_source,
        "candidate_result": cand_run,
        "default_result": baseline_run,
        "delta_passed": delta_passed,
        "delta_pass_rate": delta_pass_rate,
    }
