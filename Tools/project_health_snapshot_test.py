"""Regression checks for truthful Project Health runtime snapshots."""
from datetime import datetime, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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


env = {
    "JARVIS_BUILD_SHA": "886a4ca0dad781a0cec84de9eb952d9984af5308",
    "JARVIS_CI_STATUS": "failure",
    "JARVIS_TESTS_STATUS": "success",
    "JARVIS_CURRENT_PHASE": "stability-recovery",
    "JARVIS_CURRENT_MILESTONE": "Project Health Monitor",
    "JARVIS_NEXT_MILESTONE": "Siri / App Intents foundation",
    "JARVIS_CI_RUN_ID": "35616993206",
    "JARVIS_CI_RUN_NUMBER": "287",
    "JARVIS_CI_RUN_URL": "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35616993206",
    "JARVIS_CI_BRANCH": "chatgpt-overnight-2",
    "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-21T15:20:00Z",
    "JARVIS_CI_BACKEND_STATUS": "success",
    "JARVIS_CI_IOS_STATUS": "failure",
    "JARVIS_CI_MAC_STATUS": "success",
}

fixed_now = datetime(2026, 9, 21, 16, 0, tzinfo=timezone.utc)

tasks = [
    {"task_id": "queued-1", "status": "queued"},
    {"task_id": "done-1", "status": "succeeded"},
    {"task_id": "failed-1", "status": "succeeded"},
]


def job_state_for(task_id):
    if task_id == "failed-1":
        return {"state": "ERROR", "last_error": "sensitive internal text must not leak"}
    return None


pending = [{
    "approval_id": "approval-1",
    "agent": "core_operator",
    "action": "open_application",
    "task_id": "queued-1",
    "expires": 9999999999,
    "params": {"secret": "must-not-leak"},
}]

snapshot = project_health.build_project_health(
    tasks=tasks,
    job_state_for=job_state_for,
    pending_approvals=pending,
    capability_count=22,
    kill_switch_engaged=True,
    provider="openai",
    workspace_id="PERSONAL",
    environ=env,
    now=fixed_now,
)

check("build and planning metadata are surfaced exactly from injected evidence",
      snapshot["build_sha"] == env["JARVIS_BUILD_SHA"] and
      snapshot["phase"] == "stability-recovery" and
      snapshot["current_milestone"] == "Project Health Monitor" and
      snapshot["next_milestone"] == "Siri / App Intents foundation")

check("CI run identity and per-job results are surfaced for owner inspection",
      snapshot["ci_run_id"] == "35616993206" and
      snapshot["ci_run_number"] == "287" and
      snapshot["ci_run_url"].endswith("/35616993206") and
      snapshot["ci_branch"] == "chatgpt-overnight-2" and
      snapshot["ci_jobs"] == {"backend_tests": "success", "ios": "failure", "mac": "success"} and
      snapshot["ci"]["metadata_generated_at"] == "2026-09-21T15:20:00Z")

check("fresh CI metadata is explicitly age-grounded",
      snapshot["ci_metadata_state"] == "fresh" and
      snapshot["ci_metadata_age_seconds"] == 40 * 60)

check("runtime task counts use worker state when it is more authoritative",
      snapshot["tasks_total"] == 3 and
      snapshot["tasks_active"] == 1 and
      snapshot["tasks_failed"] == 1 and
      snapshot["task_states"] == {"QUEUED": 1, "SUCCEEDED": 1, "ERROR": 1})

blockers = snapshot["blocker_items"]
check("detailed blockers include failed runtime task, failed CI job, and kill switch",
      snapshot["blockers"] == 3 and
      {item["type"] for item in blockers} == {"task_failure", "ci_job", "kill_switch"} and
      any(item.get("task_id") == "failed-1" for item in blockers) and
      any(item.get("job") == "ios" for item in blockers))

check("blockers never expose worker error text",
      "sensitive internal text" not in repr(blockers) and "last_error" not in repr(blockers))

check("owner action count stays backward-compatible while sanitized details are added",
      snapshot["pending_approvals"] == 1 and snapshot["owner_actions"] == 1 and
      snapshot["owner_action_items"] == [{
          "type": "approval", "approval_id": "approval-1", "agent": "core_operator",
          "action": "open_application", "task_id": "queued-1", "expires": 9999999999,
      }] and "params" not in repr(snapshot["owner_action_items"]) and
      "must-not-leak" not in repr(snapshot["owner_action_items"]))

check("evidence labels distinguish reported build/CI/tests/run/freshness/milestones",
      snapshot["evidence"] == {
          "build": "reported", "ci": "reported", "tests": "reported",
          "ci_run": "reported", "ci_freshness": "fresh", "milestones": "reported",
      })

stale = project_health.build_project_health(
    tasks=[], job_state_for=lambda _: None, pending_approvals=[], capability_count=0,
    kill_switch_engaged=False, provider="openai", workspace_id="PERSONAL",
    environ={
        "JARVIS_CI_STATUS": "success",
        "JARVIS_TESTS_STATUS": "success",
        "JARVIS_CI_RUN_URL": "https://github.com/example/project/actions/runs/1",
        "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-19T15:20:00Z",
        "JARVIS_CI_BACKEND_STATUS": "success",
        "JARVIS_CI_IOS_STATUS": "success",
        "JARVIS_CI_MAC_STATUS": "success",
    },
    now=fixed_now,
)
check("stale CI artifact becomes an explicit blocker instead of current-looking success",
      stale["ci_metadata_state"] == "stale" and
      stale["ci_metadata_age_seconds"] > project_health.CI_METADATA_FRESHNESS_SECONDS and
      stale["blockers"] == 1 and
      stale["blocker_items"][0]["type"] == "ci_metadata" and
      stale["blocker_items"][0]["state"] == "stale" and
      stale["evidence"]["ci_freshness"] == "stale")

future = project_health.build_project_health(
    tasks=[], job_state_for=lambda _: None, pending_approvals=[], capability_count=0,
    kill_switch_engaged=False, provider="openai", workspace_id="PERSONAL",
    environ={"JARVIS_CI_METADATA_GENERATED_AT": "2026-09-22T16:00:00Z"},
    now=fixed_now,
)
check("materially future CI timestamps fail closed to unknown freshness",
      future["ci_metadata_state"] == "unknown" and
      future["ci_metadata_age_seconds"] is None and
      future["blockers"] == 0)

unknown = project_health.build_project_health(
    tasks=[], job_state_for=lambda _: None, pending_approvals=[], capability_count=0,
    kill_switch_engaged=False, provider="openai", workspace_id="PERSONAL", environ={},
    now=fixed_now,
)
check("missing deployment evidence fails closed instead of inventing health",
      unknown["phase"] == "unknown" and unknown["current_milestone"] == "unknown" and
      unknown["next_milestone"] == "unknown" and unknown["ci_status"] == "unknown" and
      unknown["tests_status"] == "unknown" and unknown["ci_run_id"] == "" and
      unknown["ci_run_url"] == "" and unknown["blockers"] == 0 and
      unknown["ci_metadata_state"] == "unknown" and
      unknown["evidence"]["ci_freshness"] == "unknown" and
      unknown["evidence"]["milestones"] == "unknown")

legacy_failure = project_health.build_project_health(
    tasks=[], job_state_for=lambda _: None, pending_approvals=[], capability_count=0,
    kill_switch_engaged=False, provider="openai", workspace_id="PERSONAL",
    environ={"JARVIS_CI_STATUS": "failure"}, now=fixed_now,
)
check("overall CI failure remains a blocker when legacy metadata lacks job results",
      legacy_failure["blockers"] == 1 and
      legacy_failure["blocker_items"] == [{"type": "ci", "status": "failure"}])

main_source = (BACKEND / "main.py").read_text(encoding="utf-8")
check("authenticated project health endpoint delegates snapshot construction to pure helper",
      'import project_health as project_health_mod' in main_source and
      'project_health_mod.build_project_health(' in main_source and
      'Depends(get_user_id)' in main_source and 'Depends(get_workspace)' in main_source)

check("legacy milestone fallbacks are removed from endpoint source",
      'Operator & Autopilot' not in main_source and
      'os.getenv("JARVIS_CURRENT_PHASE", "3.6")' not in main_source)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
