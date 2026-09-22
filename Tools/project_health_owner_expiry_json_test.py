"""Regression coverage for JSON-safe Project Health approval expiry values."""
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


def snapshot(expires):
    return project_health.build_project_health(
        tasks=[],
        job_state_for=lambda _task_id: None,
        pending_approvals=[{
            "approval_id": "approval-expiry",
            "agent": "core_operator",
            "action": "open_application",
            "expires": expires,
        }],
        capability_count=22,
        kill_switch_engaged=False,
        provider="openai",
        workspace_id="PERSONAL",
        environ={},
    )


for label, value in (
    ("nan", float("nan")),
    ("positive infinity", float("inf")),
    ("negative infinity", float("-inf")),
    ("oversized integer", 10 ** 5000),
):
    result = snapshot(value)
    action = result["owner_action_items"][0]
    check(f"{label} expiry is omitted", "expires" not in action)
    try:
        json.dumps(result, allow_nan=False)
        serializable = True
    except (TypeError, ValueError, OverflowError):
        serializable = False
    check(f"{label} cannot break strict JSON serialization", serializable)

finite = snapshot(1_800_000_000.25)
check(
    "finite numeric expiry remains available to the owner",
    finite["owner_action_items"][0].get("expires") == 1_800_000_000.25,
)

textual = snapshot("2026-09-22T18:00:00Z")
check(
    "bounded textual expiry remains available to the owner",
    textual["owner_action_items"][0].get("expires") == "2026-09-22T18:00:00Z",
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
