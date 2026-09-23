"""Regression: Project Health trusts only the reviewed planning schema."""
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
spec = importlib.util.spec_from_file_location("project_health_ci_metadata", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BASE = {
    "GITHUB_SHA": "abc1234",
    "GITHUB_RUN_ID": "1",
    "GITHUB_RUN_NUMBER": "1",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
}


def build_from(plan):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return module.build_metadata(BASE, plan_path=path, generated_at="2026-09-23T07:00:00Z")

valid = build_from({
    "schema_version": 4,
    "phase": "project-health-production-handoff",
    "current_milestone": "Deploy Project Health",
    "next_milestone": "Release readiness",
    "owner_actions": [{"type": "production_handoff", "action": "Complete production handoff"}],
})
assert valid["current_milestone"] == "Deploy Project Health"
assert valid["evidence"]["milestones"] == "version_controlled_plan"
assert valid["evidence"]["owner_actions"] == "version_controlled_plan"

for schema in (None, 3, 5, "4"):
    rejected = build_from({
        "schema_version": schema,
        "phase": "project-health-production-handoff",
        "current_milestone": "Must not be trusted",
        "next_milestone": "Must not be trusted either",
        "owner_actions": [{"type": "production_handoff", "action": "Must not surface"}],
    })
    assert rejected["phase"] == "unknown"
    assert rejected["current_milestone"] == "unknown"
    assert rejected["next_milestone"] == "unknown"
    assert rejected["owner_actions"] == []
    assert rejected["evidence"]["milestones"] == "unknown"
    assert rejected["evidence"]["owner_actions"] == "unknown"

print("project health reviewed plan schema guard: PASS")
