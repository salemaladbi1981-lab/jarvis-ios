"""Regression: Project Health planning facts must track the completed device gate."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
actions = plan.get("owner_actions") or []
action_text = " ".join(str(item.get("action", "")) for item in actions if isinstance(item, dict))

check("plan schema is current", int(plan.get("schema_version", 0)) >= 4)
check(
    "current phase is the approved Project Health production handoff",
    plan.get("phase") == "project-health-production-handoff"
    and "Project Health" in plan.get("current_milestone", "")
    and "production" in plan.get("current_milestone", "").lower(),
)
check(
    "next milestone keeps release actions behind explicit approval",
    "Release readiness" in plan.get("next_milestone", "")
    and "explicit user approval" in plan.get("next_milestone", ""),
)
check(
    "completed Mac permission and EventKit meeting validations are no longer advertised as owner actions",
    "Accessibility" not in action_text
    and "EventKit" not in action_text
    and "Meeting handoff" not in action_text,
)
check(
    "remaining owner action is scoped only to the already-approved Project Health production handoff",
    len(actions) == 1
    and actions[0].get("type") == "production_handoff"
    and "Project Health" in actions[0].get("action", "")
    and "production" in actions[0].get("action", "").lower(),
)
check(
    "planning strings stay bounded and single-line for the CI env handoff",
    all(
        isinstance(plan.get(key), str)
        and plan.get(key)
        and "\n" not in plan.get(key)
        and "\r" not in plan.get(key)
        and len(plan.get(key)) <= 240
        for key in ("phase", "current_milestone", "next_milestone")
    ),
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
