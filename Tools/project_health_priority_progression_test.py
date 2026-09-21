"""Regression: checked-in Project Health milestones must track the active user-approved priority."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"
plan = json.loads(PLAN.read_text(encoding="utf-8"))

checks = {
    "plan schema remains evidence-compatible": plan.get("schema_version") == 2,
    "plan remains sourced from user-approved priority order": plan.get("source") == "user-approved priority order",
    "current milestone advances to Gold cinematic UI migration": str(plan.get("current_milestone", "")).startswith("Gold cinematic UI migration"),
    "next milestone advances to Meeting foundation": str(plan.get("next_milestone", "")).startswith("Meeting foundation"),
    "Mac Operator is no longer falsely reported as current": not str(plan.get("current_milestone", "")).startswith("Mac Operator"),
    "Meeting is next but not falsely reported as current": not str(plan.get("current_milestone", "")).startswith("Meeting"),
}

failed = []
for name, ok in checks.items():
    print(("PASS" if ok else "FAIL") + ": " + name)
    if not ok:
        failed.append(name)

print(f"\nproject health priority progression: {len(checks)-len(failed)}/{len(checks)} checks passed")
if failed:
    raise SystemExit(1)
