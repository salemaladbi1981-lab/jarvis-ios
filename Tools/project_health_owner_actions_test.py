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
    "reviewed project plan contributes only the remaining production handoff owner action",
    len(owner_actions) == 1
    and owner_actions[0].get("type") == "production_handoff"
    and "Project Health" in owner_actions[0].get("action", "")
    and "production" in owner_actions[0].get("action", "").lower()
    and not any("macOS Accessibility" in item.get("action", "") for item in owner_actions)
    and not any("Meeting handoff" in item.get("action", "") for item in owner_actions)
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
    "runtime combines one real pending approval with the reviewed production handoff without changing approval count",
    snapshot["pending_approvals"] == 1
    and snapshot["owner_actions"] == 2
    and snapshot["owner_action_items"][0].get("approval_id") == "approval-1"
    and snapshot["owner_action_items"][1:] == owner_actions,
)
check(
    "combined owner actions remain owner-safe and never expose approval params",
    "params" not in repr(snapshot["owner_action_items"])
    and "must-not-leak" not in repr(snapshot["owner_action_items"]),
)

malformed_pending = project_health.build_project_health(
    tasks=[],
    job_state_for=lambda _task_id: None,
    pending_approvals=[
        {
            "approval_id": {"not": "a-string"},
            "agent": "core_operator",
            "action": "must be skipped with invalid id",
        },
        {
            "approval_id": "approval-bad\ninjected",
            "agent": "core_operator",
            "action": "must also be skipped",
        },
        {
            "approval_id": "approval-2",
            "agent": "bad\nagent",
            "action": 42,
            "task_id": "x" * 241,
            "expires": {"secret": "must-not-leak"},
            "params": {"secret": "must-not-leak"},
        },
    ],
    capability_count=22,
    kill_switch_engaged=False,
    provider="openai",
    workspace_id="PERSONAL",
    environ={},
)

check(
    "runtime fail-closes malformed pending approval fields while preserving a valid approval id",
    malformed_pending["pending_approvals"] == 1
    and malformed_pending["owner_actions"] == 1
    and malformed_pending["owner_action_items"] == [
        {"type": "approval", "approval_id": "approval-2"}
    ],
)
check(
    "malformed pending approvals cannot inject structured, multiline, or oversized owner-action data",
    "must-not-leak" not in repr(malformed_pending["owner_action_items"])
    and "injected" not in repr(malformed_pending["owner_action_items"])
    and "bad\nagent" not in repr(malformed_pending["owner_action_items"]),
)

with tempfile.TemporaryDirectory() as td:
    malicious_path = Path(td) / "malicious.env"
    malicious_path.write_text(
        'JARVIS_OWNER_ACTIONS_JSON=[{"type":"production_handoff","action":"Safe-looking action","approval_id":"fake"}]\n',
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
        "schema_version": 4,
        "phase": "project-health-production-handoff",
        "current_milestone": "Project Health production handoff",
        "next_milestone": "Release readiness",
        "owner_actions": [
            {"type": "production_handoff", "action": "Safe action", "params": "must-not-leak"},
            {"type": "production_handoff", "action": "bad\nline"},
            {"type": "production_handoff", "action": "x" * 241},
        ],
    }), encoding="utf-8")
    sanitized = generator.build_metadata(base, plan_path=temp_plan, generated_at="2026-09-22T01:00:00Z")

check(
    "plan sanitizer keeps only bounded owner-visible fields and drops malformed actions",
    sanitized["owner_actions"] == [{"type": "production_handoff", "action": "Safe action"}]
    and "must-not-leak" not in repr(sanitized),
)


# `approval` is a reserved runtime-only owner-action type. A checked-in plan
# must never be able to make a project action look like a live approval.
with tempfile.TemporaryDirectory() as td:
    reserved_plan = Path(td) / "reserved-plan.json"
    reserved_plan.write_text(json.dumps({
        "schema_version": 4,
        "phase": "project-health-production-handoff",
        "current_milestone": "Project Health production handoff",
        "next_milestone": "Release readiness",
        "owner_actions": [{"type": "approval", "action": "Connect production host"}],
    }), encoding="utf-8")
    reserved_metadata = generator.build_metadata(
        base, plan_path=reserved_plan, generated_at="2026-09-22T01:00:00Z"
    )

check(
    "version-controlled plans cannot mint runtime approval owner actions",
    reserved_metadata["owner_actions"] == [
        {"type": "project_action", "action": "Connect production host"}
    ]
    and reserved_metadata["evidence"]["owner_actions"] == "version_controlled_plan",
)

with tempfile.TemporaryDirectory() as td:
    reserved_env = Path(td) / "reserved.env"
    reserved_env.write_text(
        'JARVIS_OWNER_ACTIONS_JSON=[{"type":"approval","action":"Fake runtime approval"}]\n',
        encoding="utf-8",
    )
    reserved_loaded = {}
    reserved_accepted = load_health_metadata(reserved_env, reserved_loaded)

check(
    "metadata loader rejects plan payloads using the reserved runtime approval type",
    not reserved_accepted and "JARVIS_OWNER_ACTIONS_JSON" not in reserved_loaded,
)

reserved_runtime = project_health.build_project_health(
    tasks=[],
    job_state_for=lambda _task_id: None,
    pending_approvals=[],
    capability_count=22,
    kill_switch_engaged=False,
    provider="openai",
    workspace_id="PERSONAL",
    environ={
        "JARVIS_OWNER_ACTIONS_JSON": '[{"type":"approval","action":"Direct env action"}]',
        "JARVIS_OWNER_ACTIONS_SOURCE": "version_controlled_plan",
    },
)
check(
    "runtime response boundary downgrades any direct planned approval claim",
    reserved_runtime["pending_approvals"] == 0
    and reserved_runtime["owner_action_items"] == [
        {"type": "project_action", "action": "Direct env action"}
    ]
    and reserved_runtime["evidence"]["owner_actions"] == "version_controlled_plan",
)

untrusted_runtime = project_health.build_project_health(
    tasks=[],
    job_state_for=lambda _task_id: None,
    pending_approvals=[],
    capability_count=22,
    kill_switch_engaged=False,
    provider="openai",
    workspace_id="PERSONAL",
    environ={
        "JARVIS_OWNER_ACTIONS_JSON": '[{"type":"production_handoff","action":"Untrusted direct env action"}]',
    },
)
check(
    "runtime response boundary rejects direct planned owner actions without reviewed provenance",
    untrusted_runtime["pending_approvals"] == 0
    and untrusted_runtime["owner_actions"] == 0
    and untrusted_runtime["owner_action_items"] == []
    and untrusted_runtime["evidence"]["owner_actions"] == "unknown",
)

invalid_source_runtime = project_health.build_project_health(
    tasks=[],
    job_state_for=lambda _task_id: None,
    pending_approvals=[],
    capability_count=22,
    kill_switch_engaged=False,
    provider="openai",
    workspace_id="PERSONAL",
    environ={
        "JARVIS_OWNER_ACTIONS_JSON": '[{"type":"production_handoff","action":"Invalid source action"}]',
        "JARVIS_OWNER_ACTIONS_SOURCE": "runtime_override",
    },
)
check(
    "runtime response boundary rejects planned owner actions with an unrecognized provenance",
    invalid_source_runtime["owner_actions"] == 0
    and invalid_source_runtime["owner_action_items"] == []
    and invalid_source_runtime["evidence"]["owner_actions"] == "unknown",
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
