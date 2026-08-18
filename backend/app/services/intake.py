import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.graph_state import JobTrackerState
from app.schemas.intake import EmailPayload
from app.services.intake_graph import intake_graph
from app.services.llm import extract_email_info
from app.services.postgres_tracer import PostgresTracer
from app.services.task_tracker import task_tracker

logger = logging.getLogger(__name__)

__all__ = [
    "extract_email_info",
    "process_email_batch_sequential",
    "process_single_email_graph",
]


async def process_single_email_graph(
    db: AsyncSession,
    email: EmailPayload,
    task_id: str,
) -> JobTrackerState:
    """Executes the LangGraph StateGraph pipeline for a single email payload."""
    received_at_str = (
        email.received_at.isoformat()
        if hasattr(email.received_at, "isoformat")
        else str(email.received_at)
        if email.received_at
        else None
    )

    message_id = getattr(email, "message_id", None)

    state_input: JobTrackerState = {
        "message_id": message_id,
        "conversation_id": email.conversation_id,
        "sender": getattr(email, "sender", None),
        "subject": email.subject,
        "body": email.body,
        "received_at": received_at_str,
    }

    # Use a combined thread_id so each email gets a unique pipeline checkpoint thread
    thread_id = f"{task_id}_{message_id}" if message_id else task_id

    result = await intake_graph.ainvoke(
        state_input,
        config={
            "configurable": {"db": db, "thread_id": thread_id},
            "callbacks": [PostgresTracer()],
        },
    )
    return result


async def process_email_batch_sequential(
    db: AsyncSession,
    emails: list[EmailPayload],
    task_id: str,
) -> None:
    """Sequentially routes emails through the compiled LangGraph pipeline."""
    for index, email in enumerate(emails, start=1):
        task_tracker.update_progress_before_item(
            task_id=task_id,
            current_index=index,
            subject=email.subject,
        )

        try:
            result = await process_single_email_graph(db, email, task_id)

            if result.get("is_duplicate"):
                logger.info("Skipped duplicate email: '%s'", email.subject)
                continue

            if result.get("staging_item_id"):
                task_tracker.record_item_success(task_id=task_id, is_application=False)
            else:
                task_tracker.record_item_success(
                    task_id=task_id,
                    is_application=result.get("is_application", False),
                )
        except Exception as err:
            await db.rollback()
            error_msg = f"Failed processing email '{email.subject}': {err!s}"
            logger.error(error_msg, exc_info=True)
            task_tracker.record_item_failure(task_id=task_id, error_msg=error_msg)

    task_tracker.complete_task(task_id)
