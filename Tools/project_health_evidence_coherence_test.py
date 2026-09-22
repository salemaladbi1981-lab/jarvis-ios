"""Regression: fresh Project Health can only be green with coherent CI evidence."""
from datetime import datetime, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health

PASS = FAIL = 0
NOW = datetime(2026, 9, 22, 7, 0, tzinfo=timezone.utc)


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def snapshot(overrides=None):
    env = {
        "JARVIS_CI_STATUS": "success",
        "JARVIS_TESTS_STATUS": "success",
        "JARVIS_CI_RUN_ID": "36700000000",
        "JARVIS_CI_RUN_URL": "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/36700000000",
        "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-22T06:55:00Z",
        "JARVIS_CI_BACKEND_STATUS": "success",
        "JARVIS_CI_IOS_STATUS": "success",
        "JARVIS_CI_MAC_STATUS": "success",
    }
    if overrides:
        env.update(overrides)
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


coherent = snapshot()
check(
    "fresh success with run identity and all required jobs remains green",
    coherent["ci_status"] == "success"
    and coherent["tests_status"] == "success"
    and coherent["blockers"] == 0,
)

missing_identity = snapshot({"JARVIS_CI_RUN_URL": ""})
check(
    "fresh aggregate success without inspectable run identity fails closed",
    missing_identity["ci_status"] == "unknown"
    and missing_identity["tests_status"] == "unknown"
    and missing_identity["blocker_items"] == [
        {"type": "ci_evidence", "state": "incomplete"}
    ],
)

partial_jobs = snapshot({"JARVIS_CI_IOS_STATUS": "unknown"})
check(
    "fresh CI success with an unproven required build job cannot look green",
    partial_jobs["ci_status"] == "unknown"
    and partial_jobs["tests_status"] == "success"
    and partial_jobs["blocker_items"] == [
        {"type": "ci_evidence", "state": "incomplete"}
    ],
)

partial_tests = snapshot({"JARVIS_CI_MAC_STATUS": "unknown"})
check(
    "fresh tests success requires every test-bearing job to be successful",
    partial_tests["ci_status"] == "unknown"
    and partial_tests["tests_status"] == "unknown"
    and partial_tests["blocker_items"] == [
        {"type": "ci_evidence", "state": "incomplete"}
    ],
)

contradictory_failure = snapshot({"JARVIS_CI_IOS_STATUS": "failure"})
check(
    "explicit required-job failure overrides contradictory aggregate success",
    contradictory_failure["ci_status"] == "failure"
    and contradictory_failure["tests_status"] == "success"
    and contradictory_failure["blockers"] == 1
    and contradictory_failure["blocker_items"][0]["type"] == "ci_job"
    and contradictory_failure["blocker_items"][0]["job"] == "ios",
)

backend_failure = snapshot({"JARVIS_CI_BACKEND_STATUS": "failure"})
check(
    "backend test job failure overrides both CI and tests success claims",
    backend_failure["ci_status"] == "failure"
    and backend_failure["tests_status"] == "failure"
    and backend_failure["blockers"] == 1
    and backend_failure["blocker_items"][0]["job"] == "backend_tests",
)

print(f"\nproject health evidence coherence: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
