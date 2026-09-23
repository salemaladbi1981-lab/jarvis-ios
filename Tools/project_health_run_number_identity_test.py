"""Regression: green Project Health requires a complete GitHub Actions run identity."""
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))
import project_health

NOW = datetime(2026, 9, 23, 8, 1, tzinfo=timezone.utc)
BASE = {
    "JARVIS_BUILD_SHA": "a" * 40,
    "JARVIS_CI_STATUS": "success",
    "JARVIS_BUILD_STATUS": "success",
    "JARVIS_TESTS_STATUS": "success",
    "JARVIS_CI_RUN_ID": "35831325170",
    "JARVIS_CI_RUN_NUMBER": "419",
    "JARVIS_CI_RUN_URL": "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35831325170",
    "JARVIS_CI_BRANCH": "chatgpt-overnight-2",
    "JARVIS_CI_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-23T08:00:00Z",
    "JARVIS_CI_BACKEND_STATUS": "success",
    "JARVIS_CI_IOS_STATUS": "success",
    "JARVIS_CI_MAC_STATUS": "success",
    "JARVIS_IOS_BUILD_STATUS": "success",
    "JARVIS_MAC_BUILD_STATUS": "success",
    "JARVIS_BACKEND_TEST_STATUS": "success",
    "JARVIS_MAC_TEST_STATUS": "success",
}


def snapshot(overrides=None):
    env = dict(BASE)
    if overrides:
        env.update(overrides)
    return project_health.build_project_health(
        tasks=[], job_state_for=lambda _: None, pending_approvals=[], capability_count=22,
        kill_switch_engaged=False, provider="openai", workspace_id="PERSONAL",
        environ=env, now=NOW,
    )


def assert_unknown_identity(result):
    assert result["ci_status"] == "unknown"
    assert result["build_status"] == "unknown"
    assert result["tests_status"] == "unknown"
    assert result["evidence"]["ci_identity"] == "unknown"
    assert any(item.get("type") == "ci_identity" for item in result["blocker_items"])


healthy = snapshot()
assert healthy["ci_status"] == "success"
assert healthy["build_status"] == "success"
assert healthy["tests_status"] == "success"
assert healthy["evidence"]["ci_identity"] == "reported"
assert healthy["blockers"] == 0

for missing_or_bad in ({"JARVIS_CI_RUN_NUMBER": ""}, {"JARVIS_CI_RUN_NUMBER": "unknown"}, {"JARVIS_CI_RUN_NUMBER": "419x"}):
    assert_unknown_identity(snapshot(missing_or_bad))

print("project health complete GitHub run identity: PASS")
