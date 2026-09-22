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
    "plan schema carries reviewed owner-action evidence": plan.get("schema_version") == 3 and isinstance(owner_actions, list),
    "plan remains sourced from user-approved priority order": plan.get("source") == "user-approved priority order",
    "phase advances to device validation after all five build priorities": plan.get("phase") == "device-validation",
    "current milestone is device-only validation and final stabilization": current.startswith("Device-only validation & final stabilization"),
    "current milestone names the remaining Siri lock-screen device gate": "Siri lock-screen" in current,
    "current milestone preserves AirPods/Shokz device validation": "AirPods/Shokz" in current,
    "current milestone preserves real Mac permission validation": "Mac permissions" in current,
    "current milestone preserves real iPhone Meeting handoff validation": "Meeting handoff" in current,
    "owner actions match the four remaining physical-device gates": len(owner_actions) == 4 and "Siri/App Shortcuts" in action_text and "AirPods/Shokz" in action_text and "macOS Accessibility" in action_text and "Meeting handoff" in action_text,
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
