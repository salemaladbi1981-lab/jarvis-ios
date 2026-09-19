"""Task model + states (uploaded→queued→ingesting→analyzing→processing→generating→rendering→ready/failed)."""
from __future__ import annotations
import time
import storage

TASK_STATES = ["uploaded","queued","ingesting","analyzing","processing","generating","rendering","ready","failed"]
_STATE_ORDER = {s: i for i, s in enumerate(TASK_STATES)}


def create_task(user_id, session_id, conversation_id, prompt,
                attachment_ids=None, selected_agent=None, selected_capability=None,
                workspace_id="PERSONAL") -> dict:
    task_id = storage.new_id()
    task = {
        "task_id": task_id, "user_id": user_id, "workspace_id": workspace_id,
        "session_id": session_id,
        "conversation_id": conversation_id, "prompt": prompt,
        "attachment_ids": attachment_ids or [],
        "selected_agent": selected_agent, "selected_capability": selected_capability,
        "active_skills": [], "status": "uploaded", "progress": 0,
        "outputs": [], "created_at": time.time(), "completed_at": None, "error": None,
    }
    tasks = storage.load_tasks()
    tasks[task_id] = task
    storage.save_tasks(tasks)
    return task


def get_task(task_id: str, user_id: str = None, workspace_id: str = None) -> dict | None:
    """ownership + workspace isolation: يُرجع المهمة فقط لصاحبها في مساحتها."""
    t = storage.load_tasks().get(task_id)
    if not t:
        return None
    if user_id and t.get("user_id") != user_id:
        return None
    if workspace_id is not None and t.get("workspace_id") != workspace_id:
        return None
    return t


def list_tasks(user_id=None, workspace_id=None) -> list:
    tasks = storage.load_tasks()
    out = list(tasks.values())
    if user_id:
        out = [t for t in out if t.get("user_id") == user_id]
    if workspace_id is not None:
        out = [t for t in out if t.get("workspace_id") == workspace_id]
    return out


def set_status(task_id: str, status: str, progress: int = None, error: str = None) -> dict:
    if status not in TASK_STATES:
        return {"ok": False, "error": "bad_status"}
    tasks = storage.load_tasks()
    t = tasks.get(task_id)
    if not t:
        return {"ok": False, "error": "not_found"}
    t["status"] = status
    if progress is not None:
        t["progress"] = progress
    if error is not None:
        t["error"] = error
    if status in ("ready", "failed"):
        t["completed_at"] = time.time()
    tasks[task_id] = t
    storage.save_tasks(tasks)
    return {"ok": True, "task": t}


def add_output(task_id: str, delivery_id: str) -> dict:
    tasks = storage.load_tasks()
    t = tasks.get(task_id)
    if not t:
        return {"ok": False, "error": "not_found"}
    if delivery_id not in t["outputs"]:
        t["outputs"].append(delivery_id)
    tasks[task_id] = t
    storage.save_tasks(tasks)
    return {"ok": True, "task": t}
