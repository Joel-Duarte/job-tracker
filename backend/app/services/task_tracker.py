import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class TaskTracker:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, total_emails: int, account_id: Optional[int] = None) -> str:
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return task_id

    def update_progress_before_item(self, task_id: str, current_index: int, subject: str):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task["current_index"] = current_index
            task["current_subject"] = subject
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

    def record_item_success(self, task_id: str, is_application: bool):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if is_application:
                task["applications_updated"] += 1
            else:
                task["other_events_logged"] += 1
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

    def record_item_failure(self, task_id: str, error_msg: str):
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task["failed_count"] += 1
            task["errors"].append(error_msg)
            task["updated_at"] = datetime.now(timezone.utc).isoformat()

    def complete_task(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["current_subject"] = "Finished processing all emails."
            self._tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    def fail_task(self, task_id: str, error_msg: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["errors"].append(error_msg)
            self._tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t["status"] == status.lower()]
        return tasks


task_tracker = TaskTracker()