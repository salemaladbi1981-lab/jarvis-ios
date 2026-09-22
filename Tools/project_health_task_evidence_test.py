"""Regression coverage for resilient Project Health runtime task evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def snapshot(tasks, job_state_for):
    return project_health.build_project_health(
        tasks=tasks,
        job_state_for=job_state_for,
        pending_approvals=[],
        capability_count=22,
        kill_switch_engaged=False,
        provider="openai",
        workspace_id="PERSONAL",
        environ={},
    )


calls = []
invalid_id = snapshot(
    [{"task_id": ["not", "hashable"], "status": "ready"}],
    lambda task_id: calls.append(task_id),
)
check("malformed task id never reaches job lookup", calls == [])
check("malformed task id still preserves safe task status", invalid_id["task_states"] == {"READY": 1})
check(
    "malformed task id is surfaced as evidence blocker",
    {"type": "task_evidence", "state": "invalid_task_id"} in invalid_id["blocker_items"],
)


def raising_lookup(_task_id):
    raise RuntimeError("corrupt job store")


lookup_failure = snapshot(
    [{"task_id": "task-lookup", "status": "queued"}],
    raising_lookup,
)
check("job lookup failure does not break health response", lookup_failure["ok"] is True)
check("job lookup failure falls back to persisted task status", lookup_failure["task_states"] == {"QUEUED": 1})
check(
    "job lookup failure is visible to owner",
    {"type": "task_evidence", "state": "job_lookup_failed", "task_id": "task-lookup"}
    in lookup_failure["blocker_items"],
)

invalid_job = snapshot(
    [{"task_id": "task-job", "status": "ready"}],
    lambda _task_id: "RUNNING",
)
check("non-dict job state falls back safely", invalid_job["task_states"] == {"READY": 1})
check(
    "non-dict job state is surfaced as evidence blocker",
    {"type": "task_evidence", "state": "invalid_job_state", "task_id": "task-job"}
    in invalid_job["blocker_items"],
)

invalid_state = snapshot(
    [{"task_id": "task-state", "status": "ready"}],
    lambda _task_id: {"state": {"nested": "RUNNING"}},
)
check("malformed job state cannot become an unbounded task-state key", invalid_state["task_states"] == {"READY": 1})
check(
    "malformed job state is surfaced with safe source metadata",
    {"type": "task_evidence", "state": "invalid_state", "source": "job", "task_id": "task-state"}
    in invalid_state["blocker_items"],
)

valid = snapshot(
    [{"task_id": "task-valid", "status": "ready"}],
    lambda _task_id: {"state": "running"},
)
check("valid job state still overrides persisted task status", valid["task_states"] == {"RUNNING": 1})
check("valid running job remains counted active", valid["tasks_active"] == 1)
check("valid task adds no task-evidence blocker", not any(
    blocker.get("type") == "task_evidence" for blocker in valid["blocker_items"]
))

try:
    json.dumps(invalid_id, allow_nan=False)
    serializable = True
except (TypeError, ValueError, OverflowError):
    serializable = False
check("malformed task evidence cannot break strict JSON serialization", serializable)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
