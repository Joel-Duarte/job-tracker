import uuid
from datetime import UTC, datetime
from typing import Any


class TaskTracker:
    def __init__(self):
        self._tasks: dict[str, dict[str, Any]] = {}

    def create_task(self, total_emails: int, account_id: int | None = None) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "task_id": task_id,
            "account_id": account_id,
            "status": "processing",  # 'processing', 'completed', 'failed'
            "current_index": 0,
            "total_emails": total_emails,
            "current_subject": "Starting intake...",
            "applications_updated": 0,
            "other_events_logged": 0,
            "failed_count": 0,
            "errors": [],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        return task_id

    def update_progress_before_item(
        self, task_id: str, current_index: int, subject: str
    ):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task["current_index"] = current_index
            task["current_subject"] = subject
            task["updated_at"] = datetime.now(UTC).isoformat()

    def record_item_success(self, task_id: str, is_application: bool):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if is_application:
                task["applications_updated"] += 1
            else:
                task["other_events_logged"] += 1
            task["updated_at"] = datetime.now(UTC).isoformat()

    def record_item_failure(self, task_id: str, error_msg: str):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task["failed_count"] += 1
            task["errors"].append(error_msg)
            task["updated_at"] = datetime.now(UTC).isoformat()

    def complete_task(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["current_subject"] = "Finished processing all emails."
            self._tasks[task_id]["updated_at"] = datetime.now(UTC).isoformat()

    def fail_task(self, task_id: str, error_msg: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["errors"].append(error_msg)
            self._tasks[task_id]["updated_at"] = datetime.now(UTC).isoformat()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._tasks.get(task_id)

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status.lower()]
        return tasks


task_tracker = TaskTracker()
