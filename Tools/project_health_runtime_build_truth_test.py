"""Regression: runtime Project Health preserves exact build/test truth independently from whole-job CI."""
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health

PASS = FAIL = 0
FIXED_NOW = datetime(2026, 9, 22, 22, 30, tzinfo=timezone.utc)


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def snapshot(overrides=None):
    env = {
        "JARVIS_BUILD_SHA": "a" * 40,
        "JARVIS_BUILD_STATUS": "success",
        "JARVIS_CI_STATUS": "success",
        "JARVIS_TESTS_STATUS": "success",
        "JARVIS_CI_RUN_ID": "401",
        "JARVIS_CI_RUN_NUMBER": "401",
        "JARVIS_CI_RUN_URL": "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/401",
        "JARVIS_CI_BRANCH": "chatgpt-overnight-2",
        "JARVIS_CI_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
        "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-22T22:20:00Z",
        "JARVIS_CI_BACKEND_STATUS": "success",
        "JARVIS_CI_IOS_STATUS": "success",
        "JARVIS_CI_MAC_STATUS": "success",
        "JARVIS_IOS_BUILD_STATUS": "success",
        "JARVIS_MAC_BUILD_STATUS": "success",
        "JARVIS_BACKEND_TEST_STATUS": "success",
        "JARVIS_MAC_TEST_STATUS": "success",
    }
    if overrides:
        env.update(overrides)
    return project_health.build_project_health(
        tasks=[],
        job_state_for=lambda _task_id: None,
        pending_approvals=[],
        capability_count=22,
        kill_switch_engaged=False,
        provider="openai",
        workspace_id="PERSONAL",
        environ=env,
        now=FIXED_NOW,
    )


green = snapshot()
check(
    "fresh exact step evidence reaches runtime as independent build/test aggregates",
    green["build_status"] == "success"
    and green["tests_status"] == "success"
    and green["ci_status"] == "success"
    and green["build_jobs"] == {"ios": "success", "mac": "success"}
    and green["test_jobs"] == {"backend_tests": "success", "mac": "success"},
)

post_build_failure = snapshot({"JARVIS_CI_STATUS": "failure", "JARVIS_CI_MAC_STATUS": "failure"})
check(
    "later mac job failure makes CI red without falsely failing successful build or tests",
    post_build_failure["ci_status"] == "failure"
    and post_build_failure["build_status"] == "success"
    and post_build_failure["tests_status"] == "success"
    and post_build_failure["ci_jobs"]["mac"] == "failure"
    and post_build_failure["build_jobs"]["mac"] == "success"
    and post_build_failure["test_jobs"]["mac"] == "success",
)

build_failure = snapshot({
    "JARVIS_BUILD_STATUS": "failure",
    "JARVIS_CI_STATUS": "failure",
    "JARVIS_TESTS_STATUS": "unknown",
    "JARVIS_CI_MAC_STATUS": "failure",
    "JARVIS_MAC_BUILD_STATUS": "failure",
    "JARVIS_MAC_TEST_STATUS": "unknown",
})
check(
    "real mac build failure stays red while skipped mac tests fail closed to unknown",
    build_failure["build_status"] == "failure"
    and build_failure["build_jobs"]["mac"] == "failure"
    and build_failure["tests_status"] == "unknown"
    and build_failure["test_jobs"]["mac"] == "unknown",
)

orphan_build_failure = snapshot({
    "JARVIS_BUILD_STATUS": "failure",
    "JARVIS_CI_STATUS": "unknown",
    "JARVIS_CI_MAC_STATUS": "unknown",
    "JARVIS_MAC_BUILD_STATUS": "failure",
})
check(
    "exact build failure remains an actionable blocker when containing CI job evidence is missing",
    orphan_build_failure["build_status"] == "failure"
    and orphan_build_failure["blocker_items"] == [
        {"type": "build_step", "job": "mac", "status": "failure"}
    ],
)

orphan_test_failure = snapshot({
    "JARVIS_TESTS_STATUS": "failure",
    "JARVIS_CI_STATUS": "unknown",
    "JARVIS_CI_MAC_STATUS": "unknown",
    "JARVIS_MAC_TEST_STATUS": "failure",
})
check(
    "exact test failure remains an actionable blocker when containing CI job evidence is missing",
    orphan_test_failure["tests_status"] == "failure"
    and orphan_test_failure["blocker_items"] == [
        {"type": "test_step", "job": "mac", "status": "failure"}
    ],
)

legacy_env = {
    "JARVIS_BUILD_SHA": "b" * 40,
    "JARVIS_CI_STATUS": "success",
    "JARVIS_TESTS_STATUS": "success",
    "JARVIS_CI_RUN_ID": "399",
    "JARVIS_CI_RUN_NUMBER": "399",
    "JARVIS_CI_RUN_URL": "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/399",
    "JARVIS_CI_BRANCH": "chatgpt-overnight-2",
    "JARVIS_CI_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-22T22:20:00Z",
    "JARVIS_CI_BACKEND_STATUS": "success",
    "JARVIS_CI_IOS_STATUS": "success",
    "JARVIS_CI_MAC_STATUS": "success",
}
legacy = project_health.build_project_health(
    tasks=[], job_state_for=lambda _task_id: None, pending_approvals=[], capability_count=0,
    kill_switch_engaged=False, provider="openai", workspace_id="PERSONAL",
    environ=legacy_env, now=FIXED_NOW,
)
check(
    "older metadata keeps test compatibility while refusing to invent build-step status",
    legacy["ci_status"] == "success"
    and legacy["tests_status"] == "success"
    and legacy["build_status"] == "unknown"
    and legacy["build_jobs"] == {"ios": "unknown", "mac": "unknown"}
    and legacy["test_jobs"] == {"backend_tests": "unknown", "mac": "unknown"},
)


missing_repository = snapshot({"JARVIS_CI_REPOSITORY": ""})
check(
    "green evidence without repository identity fails closed with an identity blocker",
    missing_repository["ci_status"] == "unknown"
    and missing_repository["build_status"] == "unknown"
    and missing_repository["tests_status"] == "unknown"
    and missing_repository["evidence"]["ci_run"] == "unknown"
    and missing_repository["evidence"]["ci_identity"] == "unknown"
    and any(item.get("type") == "ci_identity" for item in missing_repository["blocker_items"]),
)

mismatched_repository = snapshot({"JARVIS_CI_REPOSITORY": "other-owner/other-repo"})
check(
    "run URL and reported repository must agree before CI can be green",
    mismatched_repository["ci_status"] == "unknown"
    and mismatched_repository["evidence"]["ci_run"] == "unknown"
    and any(item.get("type") == "ci_identity" for item in mismatched_repository["blocker_items"]),
)

missing_build_identity = snapshot({"JARVIS_BUILD_SHA": ""})
check(
    "green CI without an exact build SHA fails closed instead of proving an unknown build",
    missing_build_identity["build_sha"] == ""
    and missing_build_identity["ci_status"] == "unknown"
    and missing_build_identity["build_status"] == "unknown"
    and missing_build_identity["tests_status"] == "unknown"
    and missing_build_identity["evidence"]["ci_run"] == "reported"
    and missing_build_identity["evidence"]["ci_identity"] == "unknown"
    and any(item.get("type") == "ci_identity" for item in missing_build_identity["blocker_items"]),
)

malformed_build_identity = snapshot({"JARVIS_BUILD_SHA": "not-a-sha"})
check(
    "malformed build identity is removed at the runtime response boundary",
    malformed_build_identity["build_sha"] == ""
    and malformed_build_identity["evidence"]["build"] == "unknown"
    and malformed_build_identity["ci_status"] == "unknown",
)

stale = snapshot({"JARVIS_CI_METADATA_GENERATED_AT": "2026-09-20T22:20:00Z"})
check(
    "stale success claims are downgraded consistently for CI, build, and tests",
    stale["ci_metadata_state"] == "stale"
    and stale["ci_status"] == "unknown"
    and stale["build_status"] == "unknown"
    and stale["tests_status"] == "unknown"
    and any(item.get("type") == "ci_metadata" and item.get("state") == "stale" for item in stale["blocker_items"]),
)

missing_exact_build = snapshot({"JARVIS_MAC_BUILD_STATUS": ""})
check(
    "partial exact build evidence cannot advertise an aggregate green build",
    missing_exact_build["build_status"] == "unknown"
    and missing_exact_build["build_jobs"] == {"ios": "success", "mac": "unknown"}
    and any(item.get("type") == "ci_evidence" for item in missing_exact_build["blocker_items"]),
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
