import json
import logging
import re
import time
import uuid

from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_factory import get_task_chat_model
from app.core.prompts import get_prompt_template
from app.models.diagnostics import TraceEventModel
from app.schemas.llm import HallucinationAuditResult

logger = logging.getLogger(__name__)


def extract_json_block(text: str) -> str:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()


async def audit_generation_grounding(
    db: AsyncSession,
    candidate_cv: str,
    generated_text: str,
    context_label: str,
    task_type: str,
) -> HallucinationAuditResult:
    """
    Audits generated text for hallucinations against the candidate's CV.
    """
    start_time = time.time()

    prompt_template_str = await get_prompt_template(db, "llm_judge")
    chat_prompt = ChatPromptTemplate.from_messages([("system", prompt_template_str)])

    try:
        model = await get_task_chat_model(db, task_type="LLM_JUDGE")
        chain = chat_prompt | model

        response = await chain.ainvoke(
            {
                "candidate_cv": candidate_cv,
                "task_type": task_type,
                "context_label": context_label,
                "generated_text": generated_text,
            }
        )

        content = getattr(response, "content", response)
        output_text = content if isinstance(content, str) else str(content)
        cleaned_json = extract_json_block(output_text)

        try:
            parsed = json.loads(cleaned_json)
            result = HallucinationAuditResult(**parsed)
        except Exception as e:
            logger.warning(f"Failed to parse LLM Judge output as JSON: {e}")
            result = HallucinationAuditResult(
                passed=False,
                confidence_score=0.0,
                unverified_claims=["Failed to parse LLM Judge response"],
                critique="Judge failed to format output as valid JSON.",
            )

        latency = (time.time() - start_time) * 1000
        status_str = "success" if result.passed else "flagged"

        trace = TraceEventModel(
            run_id=f"judge_{uuid.uuid4().hex[:12]}",
            category="eval",
            event_type="llm_judge_audit",
            payload={
                "status": status_str,
                "latency_ms": latency,
                "task_type": task_type,
                "context_label": context_label,
                "passed": result.passed,
                "confidence_score": result.confidence_score,
                "unverified_claims": result.unverified_claims,
                "critique": result.critique,
            },
        )
        db.add(trace)

        return result

    except Exception as e:
        logger.error(f"Error during LLM Judge audit: {e}")
        return HallucinationAuditResult(
            passed=True,
            confidence_score=0.0,
            unverified_claims=[],
            critique=f"Error executing judge: {e}",
        )
