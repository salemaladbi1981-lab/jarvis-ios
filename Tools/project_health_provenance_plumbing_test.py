"""Regression: CI planning/owner provenance must survive the runtime handoff."""
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "phase3" / "backend"
TOOLS = ROOT / "Tools"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TOOLS))

import project_health
import project_health_metadata
import project_health_ci_metadata

PASS = FAIL = 0
def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    PASS += int(bool(condition)); FAIL += int(not condition)

env = {
    "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "123", "GITHUB_RUN_NUMBER": "9",
    "GITHUB_REF_NAME": "chatgpt-overnight-2", "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "JARVIS_BACKEND_TEST_RESULT": "success", "JARVIS_IOS_RESULT": "success", "JARVIS_MAC_RESULT": "success",
    "JARVIS_IOS_BUILD_RESULT": "success", "JARVIS_MAC_BUILD_RESULT": "success", "JARVIS_MAC_TEST_RESULT": "success",
}
metadata = project_health_ci_metadata.build_metadata(env=env, generated_at="2026-09-23T00:00:00Z")
with tempfile.TemporaryDirectory() as d:
    path = Path(d) / "project-health.env"
    project_health_ci_metadata._write_env(path, metadata)
    text = path.read_text()
    check("env handoff carries milestone provenance", "JARVIS_MILESTONE_SOURCE=version_controlled_plan" in text)
    check("env handoff carries owner-action provenance", "JARVIS_OWNER_ACTIONS_SOURCE=version_controlled_plan" in text)
    loaded = {}
    check("runtime loader accepts generated provenance", project_health_metadata.load_health_metadata(path, loaded))
    snap = project_health.build_project_health(
        tasks=[], job_state_for=lambda _id: None, pending_approvals=[], capability_count=0,
        kill_switch_engaged=False, provider="test", workspace_id="PERSONAL", environ=loaded,
        now=datetime(2026, 9, 23, 0, 5, tzinfo=timezone.utc),
    )
    check("runtime reports exact milestone source", snap["evidence"]["milestone_source"] == "version_controlled_plan")
    expected_owner = "version_controlled_plan" if snap["owner_action_items"] else "unknown"
    check("runtime owner provenance never invents plan actions", snap["evidence"]["owner_actions"] == expected_owner)

    poisoned = text.replace("JARVIS_MILESTONE_SOURCE=version_controlled_plan", "JARVIS_MILESTONE_SOURCE=untrusted")
    bad = Path(d) / "bad.env"; bad.write_text(poisoned)
    loaded_bad = {}
    check("unknown provenance values are dropped", project_health_metadata.load_health_metadata(bad, loaded_bad) and "JARVIS_MILESTONE_SOURCE" not in loaded_bad)

runtime_only = project_health.build_project_health(
    tasks=[], job_state_for=lambda _id: None,
    pending_approvals=[{"approval_id": "a1", "action": "open_application"}], capability_count=0,
    kill_switch_engaged=False, provider="test", workspace_id="PERSONAL", environ={},
)
check("runtime approvals have explicit provenance", runtime_only["evidence"]["owner_actions"] == "runtime_approvals")

print(f"\nproject health provenance plumbing: {PASS}/{PASS+FAIL} checks passed")
sys.exit(1 if FAIL else 0)
