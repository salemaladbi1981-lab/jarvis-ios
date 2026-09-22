"""Regression coverage for reviewed Project Health owner/device actions."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"
GENERATOR = ROOT / "Tools" / "project_health_ci_metadata.py"
sys.path.insert(0, str(BACKEND))

import project_health
from project_health_metadata import load_health_metadata

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


spec = importlib.util.spec_from_file_location("project_health_ci_metadata", GENERATOR)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

base = {
    "GITHUB_SHA": "abc1234",
    "GITHUB_RUN_ID": "35673020612",
    "GITHUB_RUN_NUMBER": "349",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
}
metadata = generator.build_metadata(base, plan_path=PLAN, generated_at="2026-09-22T01:00:00Z")
owner_actions = metadata.get("owner_actions") or []

check(
    "reviewed project plan contributes the four current device-only owner actions",
    len(owner_actions) == 4
    and {item.get("type") for item in owner_actions} == {"device_validation"}
    and any("Siri/App Shortcuts" in item.get("action", "") for item in owner_actions)
    and any("AirPods/Shokz" in item.get("action", "") for item in owner_actions)
    and any("macOS Accessibility" in item.get("action", "") for item in owner_actions)
    and any("Meeting handoff" in item.get("action", "") for item in owner_actions)
    and metadata["evidence"]["owner_actions"] == "version_controlled_plan",
)

with tempfile.TemporaryDirectory() as td:
    env_path = Path(td) / "project-health.env"
    generator._write_env(env_path, metadata)
    env_text = env_path.read_text(encoding="utf-8")
    action_lines = [line for line in env_text.splitlines() if line.startswith("JARVIS_OWNER_ACTIONS_JSON=")]
    loaded = {}
    accepted = load_health_metadata(env_path, loaded)

check(
    "owner actions are handed off as one compact allow-listed JSON environment value",
    len(action_lines) == 1
    and "\n" not in action_lines[0]
    and accepted
    and json.loads(loaded["JARVIS_OWNER_ACTIONS_JSON"]) == owner_actions,
)

snapshot = project_health.build_project_health(
    tasks=[],
    job_state_for=lambda _task_id: None,
    pending_approvals=[{
        "approval_id": "approval-1",
        "agent": "core_operator",
        "action": "open_application",
        "params": {"secret": "must-not-leak"},
    }],
    capability_count=22,
    kill_switch_engaged=False,
    provider="openai",
    workspace_id="PERSONAL",
    environ=loaded,
)

check(
    "runtime combines real pending approvals with reviewed device actions without changing approval count",
    snapshot["pending_approvals"] == 1
    and snapshot["owner_actions"] == 5
    and snapshot["owner_action_items"][0].get("approval_id") == "approval-1"
    and snapshot["owner_action_items"][1:] == owner_actions,
)
check(
    "combined owner actions remain owner-safe and never expose approval params",
    "params" not in repr(snapshot["owner_action_items"])
    and "must-not-leak" not in repr(snapshot["owner_action_items"]),
)

with tempfile.TemporaryDirectory() as td:
    malicious_path = Path(td) / "malicious.env"
    malicious_path.write_text(
        'JARVIS_OWNER_ACTIONS_JSON=[{"type":"device_validation","action":"Safe-looking action","approval_id":"fake"}]\n',
        encoding="utf-8",
    )
    malicious_loaded = {}
    malicious_accepted = load_health_metadata(malicious_path, malicious_loaded)

check(
    "runtime metadata loader rejects owner-action fields that could impersonate an approval",
    not malicious_accepted and "JARVIS_OWNER_ACTIONS_JSON" not in malicious_loaded,
)

with tempfile.TemporaryDirectory() as td:
    temp_plan = Path(td) / "plan.json"
    temp_plan.write_text(json.dumps({
        "phase": "device-validation",
        "current_milestone": "Device checks",
        "next_milestone": "Release readiness",
        "owner_actions": [
            {"type": "device_validation", "action": "Safe action", "params": "must-not-leak"},
            {"type": "device_validation", "action": "bad\nline"},
            {"type": "device_validation", "action": "x" * 241},
        ],
    }), encoding="utf-8")
    sanitized = generator.build_metadata(base, plan_path=temp_plan, generated_at="2026-09-22T01:00:00Z")

check(
    "plan sanitizer keeps only bounded owner-visible fields and drops malformed actions",
    sanitized["owner_actions"] == [{"type": "device_validation", "action": "Safe action"}]
    and "must-not-leak" not in repr(sanitized),
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
