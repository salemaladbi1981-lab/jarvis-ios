"""Task worker — background execution pipeline (claim/lease + retry + recovery).

الحالة: QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED. الـclaim عبر fcntl.flock
(ملف، ليس memory-only) + lease زمني للاستئناف بعد crash. الـqueue persistent (jobs_index).
"""
from __future__ import annotations
import fcntl, json, os, time, uuid
import storage, tasks as tasks_mod, deliveries, conversation, messages, files_api
import agent_runner, kill_switch, audit

JOB_STATES = ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED")
TERMINAL = ("SUCCEEDED", "FAILED", "CANCELLED")

VALID_TRANSITIONS = {
    "QUEUED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"SUCCEEDED", "FAILED", "QUEUED", "CANCELLED"},
    "FAILED": {"QUEUED"},
    "SUCCEEDED": set(),
    "CANCELLED": set(),
}

LEASE_TTL = 120
MAX_ATTEMPTS = 3
BACKOFF_BASE = 5
JOB_INDEX = os.path.join(storage.ROOT, "jobs_index.json")
CLAIM_LOCK_PATH = os.path.join(storage.ROOT, "worker_claim.lock")

_RETRYABLE = ("timeout", "hermes_key_missing", "rate_limited", "connection", "network",
              "5xx", "temporarily", "overloaded", "worker_error")


def new_worker_id() -> str:
    return f"wkr-{uuid.uuid4().hex[:8]}"

def job_state_for(task_id):
    """job state لمهمة (أو None). تستخدمه الـendpoints لدمج حالة التنفيذ في الـtask."""
    return JobStore().get(task_id)


def enqueue(task_id, max_attempts=MAX_ATTEMPTS):
    """module-level wrapper — يُستدعى من tg_inbound + main.py."""
    return JobStore().enqueue(task_id, max_attempts)


def is_retryable(error: str) -> bool:
    e = (error or "").lower()
    return any(k in e for k in _RETRYABLE)


class JobStore:
    def _load(self) -> dict:
        return storage.load_jobs()

    def _save(self, d) -> None:
        storage.save_jobs(d)

    def get(self, task_id):
        return self._load().get(task_id)

    def enqueue(self, task_id, max_attempts=MAX_ATTEMPTS) -> dict:
        d = self._load()
        if task_id in d and d[task_id].get("state") not in TERMINAL:
            return {"ok": True, "job": d[task_id], "duplicate": True}
        now = time.time()
        job = {
            "task_id": task_id, "state": "QUEUED", "worker_id": None,
            "lease_expires_at": None, "attempts": 0, "max_attempts": max_attempts,
            "last_error": None, "next_attempt_at": None, "created_at": now, "updated_at": now,
            "history": [],
        }
        d[task_id] = job
        self._save(d)
        audit.log("job_queued", task_id=task_id)
        return {"ok": True, "job": job, "duplicate": False}

    def transition(self, task_id, new_state, **fields):
        if new_state not in JOB_STATES:
            return {"ok": False, "error": "bad_state"}
        d = self._load()
        job = d.get(task_id)
        if not job:
            return {"ok": False, "error": "no_job"}
        cur = job["state"]
        if new_state not in VALID_TRANSITIONS.get(cur, set()):
            return {"ok": False, "error": f"invalid_transition:{cur}->{new_state}"}
        now = time.time()
        job["state"] = new_state
        job["updated_at"] = now
        for k, v in fields.items():
            job[k] = v
        job.setdefault("history", []).append({"state": new_state, "ts": now, "detail": fields.get("detail", "")})
        d[task_id] = job
        self._save(d)
        audit.log("job_transition", task_id=task_id, from_state=cur, to_state=new_state)
        return {"ok": True, "job": job}

    def claim(self, task_id, worker_id, lease_ttl=LEASE_TTL):
        lock_f = open(CLAIM_LOCK_PATH, "a+")
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            d = self._load()
            job = d.get(task_id)
            if not job:
                return {"ok": False, "error": "no_job"}
            now = time.time()
            if job["state"] == "RUNNING":
                if job.get("lease_expires_at") and job["lease_expires_at"] > now:
                    return {"ok": False, "error": "already_claimed"}
                # stale lease → reclaim
            elif job["state"] != "QUEUED":
                return {"ok": False, "error": f"not_claimable:{job['state']}"}
            job["state"] = "RUNNING"
            job["worker_id"] = worker_id
            job["lease_expires_at"] = now + lease_ttl
            job["attempts"] = job.get("attempts", 0) + 1
            job["updated_at"] = now
            job.setdefault("history", []).append({"state": "RUNNING", "ts": now, "detail": f"claimed_by={worker_id}"})
            d[task_id] = job
            self._save(d)
            audit.log("job_claimed", task_id=task_id, worker_id=worker_id, attempt=job["attempts"])
            return {"ok": True, "job": job}
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)
            lock_f.close()

    def recover_stale(self, stale_after=LEASE_TTL) -> list:
        d = self._load()
        now = time.time()
        recovered = []
        for tid, job in d.items():
            if job["state"] == "RUNNING" and job.get("lease_expires_at") and job["lease_expires_at"] <= now:
                job["state"] = "QUEUED"
                job["worker_id"] = None
                job["lease_expires_at"] = None
                job["updated_at"] = now
                job.setdefault("history", []).append({"state": "QUEUED", "ts": now, "detail": "stale_recovered"})
                d[tid] = job
                recovered.append(tid)
                audit.log("job_stale_recovered", task_id=tid)
        if recovered:
            self._save(d)
        return recovered

    def list(self, state=None):
        out = list(self._load().values())
        if state:
            out = [j for j in out if j["state"] == state]
        return out

    def due(self) -> list:
        """QUEUED جاهزة للتنفيذ (احترام next_attempt_at للـbackoff)."""
        now = time.time()
        return [j for j in self._load().values() if j["state"] == "QUEUED"
                and (not j.get("next_attempt_at") or j["next_attempt_at"] <= now)]


def _load_context(task):
    conv = conversation.ConversationStore().get(task["conversation_id"], task["user_id"], task["workspace_id"])
    msgs = messages.MessageStore().list(task["conversation_id"])
    attachments = []
    for fid in task.get("attachment_ids", []):
        f = files_api.get_file(fid, task["user_id"], task["workspace_id"])
        attachments.append({
            "file_id": fid, "filename": f["filename"] if f else None,
            "owned": f is not None,
            "exists": bool(f and os.path.exists(f.get("storage_ref", ""))),
        })
    return {
        "conversation": conv,
        "history": msgs,
        "attachments": attachments,
        "task": {k: task[k] for k in ("task_id", "prompt", "selected_agent", "selected_capability") if k in task},
    }


def _run_agent(task, ctx, ident):
    agent_id = task.get("selected_agent") or "core_coordinator"
    return agent_runner.run_agent(agent_id, task["prompt"], ident)


def _create_delivery(task, result, ident):
    delivery_ids = []
    if result.get("answer"):
        d = deliveries.create_delivery(task["task_id"], ident["user_id"], "result.txt", "text",
                                       content=result["answer"], workspace_id=ident["workspace_id"])
        delivery_ids.append(d["delivery"]["delivery_id"])
    for f in result.get("files", []):
        d = deliveries.create_delivery(task["task_id"], ident["user_id"], f["filename"], f.get("dtype", "file"),
                                       content=f["content"], workspace_id=ident["workspace_id"])
        delivery_ids.append(d["delivery"]["delivery_id"])
    for did in delivery_ids:
        tasks_mod.add_output(task["task_id"], did)
        conversation.ConversationStore().add_ref(task["conversation_id"], "delivery_ids", did)
    if delivery_ids:
        messages.MessageStore().add(task["conversation_id"], "assistant", result.get("answer", ""),
                                    user_id=ident["user_id"], workspace_id=ident["workspace_id"],
                                    delivery_refs=delivery_ids)
    return delivery_ids


def _handle_failure(task_id, error, attempt, max_attempts, retryable):
    if retryable and attempt < max_attempts:
        delay = BACKOFF_BASE * (2 ** (attempt - 1))
        return JobStore().transition(task_id, "QUEUED", last_error=error,
                                     next_attempt_at=time.time() + delay, detail=f"retry_{attempt}")
    return JobStore().transition(task_id, "FAILED", last_error=error,
                                 detail="terminal" if not retryable else "max_attempts")


def process_task(task_id, run_fn=None):
    """claim → run → deliver/fail. run_fn(task, ctx, ident) قابل للحقن للاختبار."""
    worker_id = new_worker_id()
    store = JobStore()
    claim_r = store.claim(task_id, worker_id)
    if not claim_r["ok"]:
        return claim_r
    task = tasks_mod.get_task(task_id)
    if not task:
        store.transition(task_id, "FAILED", last_error="task_not_found")
        return {"ok": False, "error": "task_not_found"}
    if kill_switch.engaged():
        store.transition(task_id, "FAILED", last_error="kill_switch_engaged")
        return {"ok": False, "error": "kill_switch_engaged"}
    ident = {"user_id": task["user_id"], "workspace_id": task["workspace_id"],
             "conversation_id": task["conversation_id"]}
    ctx = _load_context(task)
    audit.log("job_execution_started", task_id=task_id, worker_id=worker_id)
    try:
        result = run_fn(task, ctx, ident) if run_fn is not None else _run_agent(task, ctx, ident)
    except Exception as e:
        result = {"ok": False, "retryable": True, "error": f"worker_error:{type(e).__name__}"}
    if result.get("ok"):
        dids = _create_delivery(task, result, ident)
        store.transition(task_id, "SUCCEEDED")
        audit.log("job_succeeded", task_id=task_id, delivery_ids=dids)
        return {"ok": True, "task_id": task_id, "delivery_ids": dids}
    err = result.get("error", "unknown")
    retryable = result.get("retryable", is_retryable(err))
    job = store.get(task_id)
    attempt = job.get("attempts", 0)
    max_a = job.get("max_attempts", MAX_ATTEMPTS)
    r = _handle_failure(task_id, err, attempt, max_a, retryable)
    audit.log("job_failed", task_id=task_id, error=err[:100], retryable=retryable,
              retried=(r["job"]["state"] == "QUEUED"))
    return {"ok": False, "error": err, "retryable": retryable, "state": r["job"]["state"]}


def run_queue(limit=10, run_fn=None):
    """يعالج المهام الجاهزة (QUEUED + next_attempt_at منقضي) مع استعادة stale أولًا."""
    store = JobStore()
    store.recover_stale()
    results = []
    for job in store.due():
        results.append(process_task(job["task_id"], run_fn))
        if len(results) >= limit:
            break
    return results


def request_cancel(task_id) -> dict:
    """cancel requested — يوثق الفرق بين الطلب والإيقاف الفعلي للـagent."""
    store = JobStore()
    job = store.get(task_id)
    if not job:
        return {"ok": False, "error": "no_job"}
    if job["state"] in ("SUCCEEDED", "FAILED"):
        return {"ok": False, "error": f"already_terminal:{job['state']}"}
    if job["state"] == "QUEUED":
        return store.transition(task_id, "CANCELLED", detail="cancel_requested")
    # RUNNING: نسجل طلب إلغاء لكن لا ندّعي إنهاء التنفيذ الفعلي
    d = store._load()
    j = d.get(task_id)
    j["cancel_requested"] = True
    d[task_id] = j
    store._save(d)
    audit.log("job_cancel_requested", task_id=task_id)
    return {"ok": True, "cancel_requested": True, "note": "execution_may_continue"}
