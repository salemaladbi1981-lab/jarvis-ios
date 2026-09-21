"""Project Health CI metadata handoff regression checks."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
WORKFLOW = ROOT / ".github" / "workflows" / "ios-build.yml"
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"
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
plan = json.loads(PLAN.read_text(encoding="utf-8"))

base = {
    "GITHUB_SHA": "abc1234",
    "GITHUB_RUN_ID": "35603375966",
    "GITHUB_RUN_NUMBER": "277",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
    "JARVIS_CURRENT_PHASE": "4",
    "JARVIS_CURRENT_MILESTONE": "Project Health Monitor",
    "JARVIS_NEXT_MILESTONE": "Siri / App Intents foundation",
}
metadata = module.build_metadata(base, plan_path=PLAN, generated_at="2026-09-21T13:10:00Z")

check("green CI is reported only from completed job results",
      metadata["build_sha"] == "abc1234" and
      metadata["ci_status"] == "success" and
      metadata["tests_status"] == "success" and
      metadata["jobs"] == {"backend_tests": "success", "ios": "success", "mac": "success"})

check("CI run identity is grounded in GitHub-provided runtime values",
      metadata["ci_run_id"] == "35603375966" and
      metadata["ci_run_number"] == "277" and
      metadata["ci_branch"] == "chatgpt-overnight-2" and
      metadata["ci_run_url"] == "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35603375966" and
      metadata["metadata_generated_at"] == "2026-09-21T13:10:00Z" and
      metadata["evidence"]["run"] == "github_actions")

check("repository variables remain authoritative for planning metadata",
      metadata["phase"] == "4" and
      metadata["current_milestone"] == "Project Health Monitor" and
      metadata["next_milestone"] == "Siri / App Intents foundation" and
      metadata["evidence"]["milestones"] == "github_repository_variables")

fallback_env = {
    "GITHUB_SHA": "abc1234",
    "GITHUB_RUN_ID": "35603375966",
    "GITHUB_RUN_NUMBER": "277",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
}
fallback_meta = module.build_metadata(fallback_env, plan_path=PLAN, generated_at="2026-09-21T13:10:00Z")
check("reviewed version-controlled plan fills missing repository variables",
      fallback_meta["phase"] == plan["phase"] and
      fallback_meta["current_milestone"] == plan["current_milestone"] and
      fallback_meta["next_milestone"] == plan["next_milestone"] and
      fallback_meta["evidence"]["milestones"] == "version_controlled_plan")

partial = dict(fallback_env)
partial["JARVIS_CURRENT_MILESTONE"] = "Deployment-owned milestone"
partial_meta = module.build_metadata(partial, plan_path=PLAN, generated_at="2026-09-21T13:10:00Z")
check("explicit planning values override the plan without hiding mixed evidence",
      partial_meta["current_milestone"] == "Deployment-owned milestone" and
      partial_meta["phase"] == plan["phase"] and
      partial_meta["next_milestone"] == plan["next_milestone"] and
      partial_meta["evidence"]["milestones"] == "mixed")

failed_ios = dict(base)
failed_ios["JARVIS_IOS_RESULT"] = "failure"
failed_meta = module.build_metadata(failed_ios, plan_path=PLAN, generated_at="2026-09-21T13:10:00Z")
check("iOS failure makes CI red without falsely failing backend/mac tests",
      failed_meta["ci_status"] == "failure" and failed_meta["tests_status"] == "success")

failed_tests = dict(base)
failed_tests["JARVIS_BACKEND_TEST_RESULT"] = "failure"
failed_test_meta = module.build_metadata(failed_tests, plan_path=PLAN, generated_at="2026-09-21T13:10:00Z")
check("backend test failure makes tests and CI fail",
      failed_test_meta["tests_status"] == "failure" and failed_test_meta["ci_status"] == "failure")

with tempfile.TemporaryDirectory() as temp_dir:
    missing_plan = Path(temp_dir) / "missing-plan.json"
    missing_meta = module.build_metadata(fallback_env, plan_path=missing_plan, generated_at="2026-09-21T13:10:00Z")
    malformed_plan = Path(temp_dir) / "malformed-plan.json"
    malformed_plan.write_text("{not-json", encoding="utf-8")
    malformed_meta = module.build_metadata(fallback_env, plan_path=malformed_plan, generated_at="2026-09-21T13:10:00Z")

check("missing or malformed plan fails closed to unknown planning metadata",
      missing_meta["phase"] == "unknown" and
      missing_meta["current_milestone"] == "unknown" and
      missing_meta["next_milestone"] == "unknown" and
      missing_meta["evidence"]["milestones"] == "unknown" and
      malformed_meta["current_milestone"] == "unknown")

check("checked-in plan matches approved priority order",
      str(plan.get("current_milestone", "")).startswith("Project Health Monitor") and
      str(plan.get("next_milestone", "")).startswith("Siri / App Intents + Shortcuts") and
      plan.get("source") == "user-approved priority order")

with tempfile.TemporaryDirectory() as temp_dir:
    env_path = Path(temp_dir) / "project-health.env"
    module._write_env(env_path, fallback_meta)
    env_text = env_path.read_text(encoding="utf-8")
check("env handoff carries real plan and CI run evidence consumed by project health runtime",
      "JARVIS_BUILD_SHA=abc1234" in env_text and
      "JARVIS_CI_STATUS=success" in env_text and
      "JARVIS_TESTS_STATUS=success" in env_text and
      "JARVIS_CI_RUN_ID=35603375966" in env_text and
      "JARVIS_CI_RUN_NUMBER=277" in env_text and
      "JARVIS_CI_BRANCH=chatgpt-overnight-2" in env_text and
      "JARVIS_CI_BACKEND_STATUS=success" in env_text and
      "JARVIS_CI_IOS_STATUS=success" in env_text and
      "JARVIS_CI_MAC_STATUS=success" in env_text and
      f"JARVIS_CURRENT_MILESTONE={plan['current_milestone']}" in env_text and
      f"JARVIS_NEXT_MILESTONE={plan['next_milestone']}" in env_text)

check("workflow emits metadata only after all verification jobs settle",
      "project-health-metadata:" in workflow and
      "needs: [backend-tests, ios, mac]" in workflow and
      "if: ${{ always() }}" in workflow and
      "python3 Tools/project_health_ci_metadata.py" in workflow)

check("workflow still permits repository-variable overrides",
      "vars.JARVIS_CURRENT_PHASE" in workflow and
      "vars.JARVIS_CURRENT_MILESTONE" in workflow and
      "vars.JARVIS_NEXT_MILESTONE" in workflow)

check("workflow publishes a secret-free deployment handoff artifact",
      "name: project-health-metadata" in workflow and
      "project-health-ci.json" in workflow and
      "project-health.env" in workflow)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
