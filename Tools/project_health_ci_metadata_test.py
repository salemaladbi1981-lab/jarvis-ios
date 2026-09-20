"""Project Health CI metadata handoff regression checks."""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
WORKFLOW = ROOT / ".github" / "workflows" / "ios-build.yml"
PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


spec = importlib.util.spec_from_file_location("project_health_ci_metadata", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
workflow = WORKFLOW.read_text(encoding="utf-8")

base = {
    "GITHUB_SHA": "abc123",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
    "JARVIS_CURRENT_PHASE": "4",
    "JARVIS_CURRENT_MILESTONE": "Project Health Monitor",
    "JARVIS_NEXT_MILESTONE": "Siri / App Intents foundation",
}
metadata = module.build_metadata(base)

check("green CI is reported only from completed job results",
      metadata["build_sha"] == "abc123" and
      metadata["ci_status"] == "success" and
      metadata["tests_status"] == "success" and
      metadata["jobs"] == {"backend_tests": "success", "ios": "success", "mac": "success"})

check("planning metadata comes from repository/deployment inputs",
      metadata["phase"] == "4" and
      metadata["current_milestone"] == "Project Health Monitor" and
      metadata["next_milestone"] == "Siri / App Intents foundation" and
      metadata["evidence"]["milestones"] == "github_repository_variables")

failed_ios = dict(base)
failed_ios["JARVIS_IOS_RESULT"] = "failure"
failed_meta = module.build_metadata(failed_ios)
check("iOS failure makes CI red without falsely failing backend/mac tests",
      failed_meta["ci_status"] == "failure" and failed_meta["tests_status"] == "success")

failed_tests = dict(base)
failed_tests["JARVIS_BACKEND_TEST_RESULT"] = "failure"
failed_test_meta = module.build_metadata(failed_tests)
check("backend test failure makes tests and CI fail",
      failed_test_meta["tests_status"] == "failure" and failed_test_meta["ci_status"] == "failure")

missing = {
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
}
missing_meta = module.build_metadata(missing)
check("missing SHA and milestone evidence fails closed",
      missing_meta["build_sha"] == "" and
      missing_meta["phase"] == "unknown" and
      missing_meta["current_milestone"] == "unknown" and
      missing_meta["next_milestone"] == "unknown" and
      missing_meta["evidence"]["build"] == "unknown" and
      missing_meta["evidence"]["milestones"] == "unknown")

with tempfile.TemporaryDirectory() as temp_dir:
    env_path = Path(temp_dir) / "project-health.env"
    module._write_env(env_path, metadata)
    env_text = env_path.read_text(encoding="utf-8")
check("env handoff matches keys consumed by project health endpoint",
      "JARVIS_BUILD_SHA=abc123" in env_text and
      "JARVIS_CI_STATUS=success" in env_text and
      "JARVIS_TESTS_STATUS=success" in env_text and
      "JARVIS_CURRENT_MILESTONE=Project Health Monitor" in env_text and
      "JARVIS_NEXT_MILESTONE=Siri / App Intents foundation" in env_text)

check("workflow emits metadata only after all verification jobs settle",
      "project-health-metadata:" in workflow and
      "needs: [backend-tests, ios, mac]" in workflow and
      "if: ${{ always() }}" in workflow and
      "python3 Tools/project_health_ci_metadata.py" in workflow)

check("workflow sources milestone labels from non-secret repository variables",
      "vars.JARVIS_CURRENT_PHASE" in workflow and
      "vars.JARVIS_CURRENT_MILESTONE" in workflow and
      "vars.JARVIS_NEXT_MILESTONE" in workflow)

check("workflow publishes a secret-free deployment handoff artifact",
      "name: project-health-metadata" in workflow and
      "project-health-ci.json" in workflow and
      "project-health.env" in workflow)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
