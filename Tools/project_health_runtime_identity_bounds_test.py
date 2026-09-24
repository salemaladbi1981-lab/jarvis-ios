"""Regression: Project Health bounds CI identity at both handoff and response boundaries."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

# project_health treats CI metadata older than 24h as stale, which changes which
# blockers are raised. A hardcoded timestamp therefore turned this suite red one day
# after it was written, on every commit. Generate a fresh stamp instead.
FRESH_GENERATED_AT = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health
import project_health_metadata

PASS = FAIL = 0

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
        job_state_for=lambda _task_id: None,
        pending_approvals=[],
        capability_count=1,
        kill_switch_engaged=False,
        provider="test",
        workspace_id="ws-ci-bounds",
        environ=env,
    )

base = {
    "JARVIS_BUILD_SHA": "a" * 40,
    "JARVIS_CI_STATUS": "success",
    "JARVIS_BUILD_STATUS": "success",
    "JARVIS_TESTS_STATUS": "success",
    "JARVIS_CI_BACKEND_STATUS": "success",
    "JARVIS_CI_IOS_STATUS": "success",
    "JARVIS_CI_MAC_STATUS": "success",
    "JARVIS_IOS_BUILD_STATUS": "success",
    "JARVIS_MAC_BUILD_STATUS": "success",
    "JARVIS_BACKEND_TEST_STATUS": "success",
    "JARVIS_MAC_TEST_STATUS": "success",
    "JARVIS_CI_RUN_ID": "35822449946",
    "JARVIS_CI_RUN_NUMBER": "416",
    "JARVIS_CI_RUN_URL": "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35822449946",
    "JARVIS_CI_BRANCH": "chatgpt-overnight-2",
    "JARVIS_CI_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "JARVIS_CI_METADATA_GENERATED_AT": FRESH_GENERATED_AT,
}

valid = snapshot(base)
check("bounded CI identity is preserved", valid["ci_run_id"] == "35822449946" and valid["ci_run_number"] == "416")
check("canonical run URL/repository are preserved", valid["ci_run_url"] == base["JARVIS_CI_RUN_URL"] and valid["ci_repository"] == base["JARVIS_CI_REPOSITORY"])

poisoned = dict(base)
poisoned.update({
    "JARVIS_CI_RUN_ID": "9" * 33,
    "JARVIS_CI_RUN_NUMBER": "8" * 33,
    "JARVIS_CI_BRANCH": "b" * 201,
    "JARVIS_CI_REPOSITORY": ("r" * 190) + "/" + ("x" * 20),
    "JARVIS_CI_RUN_URL": "https://example.invalid/actions/runs/35822449946",
})
bad = snapshot(poisoned)
check("oversized run identifiers fail closed at runtime", bad["ci_run_id"] == "" and bad["ci_run_number"] == "")
check("oversized branch and repository are not reflected", bad["ci_branch"] == "" and bad["ci_repository"] == "")
check("non-canonical run URL is not reflected", bad["ci_run_url"] == "")
check("corrupt identity cannot prove green CI", bad["ci_status"] == "unknown" and bad["evidence"]["ci_identity"] == "unknown")
check("corrupt green identity surfaces an owner-safe blocker", any(x.get("type") == "ci_identity" for x in bad["blocker_items"]))

timestamp_poisoned = dict(base)
timestamp_poisoned["JARVIS_CI_METADATA_GENERATED_AT"] = FRESH_GENERATED_AT + ("x" * 64)
bad_timestamp = snapshot(timestamp_poisoned)
check("malformed CI timestamp is bounded and not reflected", bad_timestamp["ci_metadata_generated_at"] == "" and bad_timestamp["ci_metadata_state"] == "unknown")
check("malformed timestamp surfaces metadata blocker", any(x.get("type") == "ci_metadata" and x.get("state") == "unknown" for x in bad_timestamp["blocker_items"]))

with tempfile.TemporaryDirectory() as td:
    handoff = Path(td) / "project-health.env"
    handoff.write_text(
        "JARVIS_CI_RUN_ID=" + ("9" * 33) + "\n"
        "JARVIS_CI_RUN_NUMBER=" + ("8" * 33) + "\n"
        "JARVIS_CI_REPOSITORY=" + (("r" * 190) + "/" + ("x" * 20)) + "\n"
        "JARVIS_CI_RUN_URL=https://github.com/" + (("r" * 190) + "/" + ("x" * 20)) + "/actions/runs/999\n",
        encoding="utf-8",
    )
    env = {}
    loaded = project_health_metadata.load_health_metadata(handoff, env)

check("all-invalid handoff fails closed", loaded is False)
check("oversized CI identifiers are rejected by handoff loader", "JARVIS_CI_RUN_ID" not in env and "JARVIS_CI_RUN_NUMBER" not in env)
check("oversized repository/run URL are rejected by handoff loader", "JARVIS_CI_REPOSITORY" not in env and "JARVIS_CI_RUN_URL" not in env)

print(f"\nproject health runtime identity bounds: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
