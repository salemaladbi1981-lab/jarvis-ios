"""Regression checks: Project Health must not advertise stale/unproven green CI."""
from datetime import datetime, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health

PASS = FAIL = 0
NOW = datetime(2026, 9, 22, 3, 0, tzinfo=timezone.utc)


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def snapshot(env):
    return project_health.build_project_health(
        tasks=[],
        job_state_for=lambda _: None,
        pending_approvals=[],
        capability_count=22,
        kill_switch_engaged=False,
        provider="openai",
        workspace_id="PERSONAL",
        environ=env,
        now=NOW,
    )


success = {
    "JARVIS_BUILD_SHA": "c" * 40,
    "JARVIS_CI_STATUS": "success",
    "JARVIS_TESTS_STATUS": "success",
    "JARVIS_CI_BACKEND_STATUS": "success",
    "JARVIS_CI_IOS_STATUS": "success",
    "JARVIS_CI_MAC_STATUS": "success",
    "JARVIS_CI_RUN_ID": "359",
    "JARVIS_CI_RUN_URL": "https://github.com/example/project/actions/runs/359",
    "JARVIS_CI_BRANCH": "chatgpt-overnight-2",
    "JARVIS_CI_REPOSITORY": "example/project",
}

missing_timestamp = snapshot(success)
check(
    "success without freshness timestamp fails closed instead of looking green",
    missing_timestamp["ci_metadata_state"] == "unknown"
    and missing_timestamp["ci_status"] == "unknown"
    and missing_timestamp["tests_status"] == "unknown"
    and missing_timestamp["blockers"] == 1
    and missing_timestamp["blocker_items"][0]["type"] == "ci_metadata"
    and missing_timestamp["blocker_items"][0]["state"] == "unknown",
)

check(
    "raw reported CI remains available for diagnostics while display status is gated",
    missing_timestamp["ci"]["status"] == "success"
    and missing_timestamp["ci"]["tests_status"] == "success"
    and missing_timestamp["ci_jobs"] == {
        "backend_tests": "success", "ios": "success", "mac": "success"
    },
)

stale_env = dict(success)
stale_env["JARVIS_CI_METADATA_GENERATED_AT"] = "2026-09-20T00:00:00Z"
stale = snapshot(stale_env)
check(
    "stale successful artifact is downgraded to unknown display status",
    stale["ci_metadata_state"] == "stale"
    and stale["ci_status"] == "unknown"
    and stale["tests_status"] == "unknown"
    and stale["blocker_items"][0]["state"] == "stale",
)

fresh_env = dict(success)
fresh_env["JARVIS_CI_METADATA_GENERATED_AT"] = "2026-09-22T02:45:00Z"
fresh = snapshot(fresh_env)
check(
    "fresh successful artifact remains green",
    fresh["ci_metadata_state"] == "fresh"
    and fresh["ci_status"] == "success"
    and fresh["tests_status"] == "success"
    and fresh["blockers"] == 0,
)

legacy_failure = snapshot({"JARVIS_CI_STATUS": "failure"})
check(
    "failure remains visible without freshness proof and is not hidden by gating",
    legacy_failure["ci_status"] == "failure"
    and legacy_failure["tests_status"] == "unknown"
    and legacy_failure["blocker_items"] == [{"type": "ci", "status": "failure"}],
)

future_env = dict(success)
future_env["JARVIS_CI_METADATA_GENERATED_AT"] = "2026-09-22T05:00:00Z"
future = snapshot(future_env)
check(
    "materially future timestamp cannot produce green status",
    future["ci_metadata_state"] == "unknown"
    and future["ci_status"] == "unknown"
    and future["tests_status"] == "unknown"
    and future["blocker_items"][0]["type"] == "ci_metadata",
)

print(f"\nproject health freshness fail-closed: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
