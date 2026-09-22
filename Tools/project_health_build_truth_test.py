"""Regression: Project Health CI handoff separates build/test truth from whole-job CI."""
import importlib.util
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

from project_health_metadata import load_health_metadata

SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
WORKFLOW = (ROOT / ".github" / "workflows" / "ios-build.yml").read_text(encoding="utf-8")
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"

spec = importlib.util.spec_from_file_location("project_health_ci_metadata_build_truth", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


base = {
    "GITHUB_SHA": "abc1234",
    "GITHUB_RUN_ID": "400",
    "GITHUB_RUN_NUMBER": "400",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
    "GITHUB_REF_NAME": "chatgpt-overnight-2",
    "JARVIS_BACKEND_TEST_RESULT": "success",
    "JARVIS_IOS_RESULT": "success",
    "JARVIS_MAC_RESULT": "success",
    "JARVIS_IOS_BUILD_RESULT": "success",
    "JARVIS_MAC_BUILD_RESULT": "success",
    "JARVIS_MAC_TEST_RESULT": "success",
}

green = module.build_metadata(base, plan_path=PLAN, generated_at="2026-09-22T21:00:00Z")
check(
    "precise step evidence produces independent green build and test aggregates",
    green["build_status"] == "success"
    and green["tests_status"] == "success"
    and green["build_jobs"] == {"ios": "success", "mac": "success"}
    and green["test_jobs"] == {"backend_tests": "success", "mac": "success"}
    and green["evidence"]["build_status"] == "github_actions_steps"
    and green["evidence"]["tests"] == "github_actions_steps",
)

# A screenshot/post-build failure makes the whole mac job red, but exact build/test
# steps remain green. Project Health must preserve that distinction.
post_build_failure = dict(base)
post_build_failure["JARVIS_MAC_RESULT"] = "failure"
separated = module.build_metadata(post_build_failure, plan_path=PLAN, generated_at="2026-09-22T21:00:00Z")
check(
    "later mac job failure makes CI red without falsely failing build or tests",
    separated["ci_status"] == "failure"
    and separated["jobs"]["mac"] == "failure"
    and separated["build_status"] == "success"
    and separated["tests_status"] == "success",
)

build_failure = dict(base)
build_failure["JARVIS_MAC_RESULT"] = "failure"
build_failure["JARVIS_MAC_BUILD_RESULT"] = "failure"
build_failure["JARVIS_MAC_TEST_RESULT"] = "skipped"
failed = module.build_metadata(build_failure, plan_path=PLAN, generated_at="2026-09-22T21:00:00Z")
check(
    "real mac build failure is red while skipped tests fail closed to unknown",
    failed["build_status"] == "failure"
    and failed["build_jobs"]["mac"] == "failure"
    and failed["tests_status"] == "unknown"
    and failed["test_jobs"]["mac"] == "unknown",
)

legacy = dict(base)
legacy.pop("JARVIS_IOS_BUILD_RESULT")
legacy.pop("JARVIS_MAC_BUILD_RESULT")
legacy.pop("JARVIS_MAC_TEST_RESULT")
legacy_meta = module.build_metadata(legacy, plan_path=PLAN, generated_at="2026-09-22T21:00:00Z")
check(
    "older workflow input falls back conservatively and labels weaker evidence",
    legacy_meta["build_status"] == "success"
    and legacy_meta["tests_status"] == "success"
    and legacy_meta["evidence"]["build_status"] == "github_actions_jobs_fallback"
    and legacy_meta["evidence"]["tests"] == "github_actions_jobs_fallback",
)

with tempfile.TemporaryDirectory() as td:
    env_path = Path(td) / "project-health.env"
    module._write_env(env_path, green)
    loaded = {}
    ok = load_health_metadata(env_path, loaded)
    check(
        "secret-free handoff carries precise build and test step statuses through runtime allow-list",
        ok
        and loaded.get("JARVIS_BUILD_STATUS") == "success"
        and loaded.get("JARVIS_IOS_BUILD_STATUS") == "success"
        and loaded.get("JARVIS_MAC_BUILD_STATUS") == "success"
        and loaded.get("JARVIS_BACKEND_TEST_STATUS") == "success"
        and loaded.get("JARVIS_MAC_TEST_STATUS") == "success",
    )

check(
    "workflow publishes exact iOS/mac build and mac test step outcomes",
    "id: ios_build" in WORKFLOW
    and "id: mac_build" in WORKFLOW
    and "id: mac_tests" in WORKFLOW
    and "build_result: ${{ steps.ios_build.outcome }}" in WORKFLOW
    and "build_result: ${{ steps.mac_build.outcome }}" in WORKFLOW
    and "test_result: ${{ steps.mac_tests.outcome }}" in WORKFLOW
    and "JARVIS_IOS_BUILD_RESULT: ${{ needs.ios.outputs.build_result }}" in WORKFLOW
    and "JARVIS_MAC_BUILD_RESULT: ${{ needs.mac.outputs.build_result }}" in WORKFLOW
    and "JARVIS_MAC_TEST_RESULT: ${{ needs.mac.outputs.test_result }}" in WORKFLOW,
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
