"""Regression: checked-in Project Health milestones must track the active user-approved priority."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"
plan = json.loads(PLAN.read_text(encoding="utf-8"))

current = str(plan.get("current_milestone", ""))
next_milestone = str(plan.get("next_milestone", ""))
owner_actions = plan.get("owner_actions") or []
action_text = " | ".join(str(item.get("action", "")) for item in owner_actions if isinstance(item, dict))

checks = {
    "plan schema carries reviewed owner-action evidence": plan.get("schema_version") == 4 and isinstance(owner_actions, list),
    "plan remains sourced from the user-approved priority plus completed device validation": plan.get("source") == "user-approved priority order and completed device validation",
    "phase advances to the approved Project Health production handoff": plan.get("phase") == "project-health-production-handoff",
    "current milestone is Project Health production handoff": "Project Health" in current and "production" in current.lower(),
    "completed Siri lock-screen gate is no longer reported as remaining": "Siri" not in current and "Siri/App Shortcuts" not in action_text,
    "completed AirPods/Shokz gate is no longer reported as remaining": "AirPods/Shokz" not in current and "AirPods/Shokz" not in action_text,
    "completed Mac permission validation is no longer reported as remaining": "Mac permissions" not in current and "macOS Accessibility" not in action_text,
    "completed Meeting handoff validation is no longer reported as remaining": "Meeting handoff" not in current and "Meeting handoff" not in action_text,
    "owner actions contain only the approved Project Health production handoff": len(owner_actions) == 1 and owner_actions[0].get("type") == "production_handoff" and "Project Health" in action_text and "production" in action_text.lower(),
    "next milestone is release readiness behind explicit approval": next_milestone.startswith("Release readiness") and "explicit user approval" in next_milestone,
    "completed Gold migration is no longer falsely reported as current": not current.startswith("Gold cinematic UI migration"),
    "completed Meeting foundation is no longer falsely reported as current or next": not current.startswith("Meeting foundation") and not next_milestone.startswith("Meeting foundation"),
    "release plan does not imply an unauthorized merge": "merge/TestFlight only with explicit user approval" in next_milestone,
}

failed = []
for name, ok in checks.items():
    print(("PASS" if ok else "FAIL") + ": " + name)
    if not ok:
        failed.append(name)

print(f"\nproject health priority progression: {len(checks)-len(failed)}/{len(checks)} checks passed")
if failed:
    raise SystemExit(1)
