"""Regression: Project Health CI producer must fail closed on malformed run/build identity."""
import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Tools" / "project_health_ci_metadata.py"
PLAN = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"

spec = importlib.util.spec_from_file_location("project_health_ci_metadata", SCRIPT)
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


def base_env():
    return {
        "GITHUB_SHA": "abc1234",
        "GITHUB_RUN_ID": "35759164850",
        "GITHUB_RUN_NUMBER": "380",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
        "GITHUB_REF_NAME": "chatgpt-overnight-2",
        "JARVIS_BACKEND_TEST_RESULT": "success",
        "JARVIS_IOS_RESULT": "success",
        "JARVIS_MAC_RESULT": "success",
    }


valid = module.build_metadata(base_env(), plan_path=PLAN, generated_at="2026-09-22T17:21:22Z")
check("valid GitHub build identity is preserved", valid["build_sha"] == "abc1234")
check("valid GitHub run identity is preserved",
      valid["ci_run_id"] == "35759164850"
      and valid["ci_run_number"] == "380"
      and valid["ci_branch"] == "chatgpt-overnight-2"
      and valid["ci_run_url"].endswith("/actions/runs/35759164850")
      and valid["evidence"]["run"] == "github_actions")

poisoned = base_env()
poisoned["GITHUB_SHA"] = "abc1234\nJARVIS_CI_STATUS=failure"
poisoned["GITHUB_RUN_ID"] = "35759164850\nJARVIS_TESTS_STATUS=failure"
poisoned["GITHUB_RUN_NUMBER"] = "380\rJARVIS_CI_IOS_STATUS=failure"
poisoned["GITHUB_REF_NAME"] = "chatgpt-overnight-2\nJARVIS_CI_MAC_STATUS=failure"
poisoned_meta = module.build_metadata(poisoned, plan_path=PLAN, generated_at="2026-09-22T17:21:22Z")
check("multiline build SHA fails closed", poisoned_meta["build_sha"] == "" and poisoned_meta["evidence"]["build"] == "unknown")
check("multiline run identifiers fail closed",
      poisoned_meta["ci_run_id"] == ""
      and poisoned_meta["ci_run_number"] == ""
      and poisoned_meta["ci_run_url"] == ""
      and poisoned_meta["evidence"]["run"] == "unknown")
check("multiline branch fails closed", poisoned_meta["ci_branch"] == "")

bad_repository = base_env()
bad_repository["GITHUB_REPOSITORY"] = "salemaladbi1981-lab/jarvis-ios\nJARVIS_CI_STATUS=failure"
bad_repository_meta = module.build_metadata(bad_repository, plan_path=PLAN, generated_at="2026-09-22T17:21:22Z")
check("malformed repository cannot create a clickable run URL",
      bad_repository_meta["ci_run_id"] == "35759164850"
      and bad_repository_meta["ci_run_url"] == ""
      and bad_repository_meta["evidence"]["run"] == "unknown")

bad_server = base_env()
bad_server["GITHUB_SERVER_URL"] = "https://example.invalid"
bad_server_meta = module.build_metadata(bad_server, plan_path=PLAN, generated_at="2026-09-22T17:21:22Z")
check("non-GitHub server cannot create a run URL", bad_server_meta["ci_run_url"] == "" and bad_server_meta["evidence"]["run"] == "unknown")

oversized = base_env()
oversized["GITHUB_RUN_ID"] = "9" * 33
oversized["GITHUB_RUN_NUMBER"] = "8" * 33
oversized["GITHUB_REF_NAME"] = "b" * 201
oversized_meta = module.build_metadata(oversized, plan_path=PLAN, generated_at="2026-09-22T17:21:22Z")
check("oversized CI identity fails closed",
      oversized_meta["ci_run_id"] == ""
      and oversized_meta["ci_run_number"] == ""
      and oversized_meta["ci_branch"] == ""
      and oversized_meta["ci_run_url"] == "")

with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "project-health.env"
    module._write_env(out, poisoned_meta)
    text = out.read_text(encoding="utf-8")
check("rejected identity text cannot inject extra handoff keys",
      text.count("JARVIS_CI_STATUS=") == 1
      and text.count("JARVIS_TESTS_STATUS=") == 1
      and text.count("JARVIS_CI_IOS_STATUS=") == 1
      and text.count("JARVIS_CI_MAC_STATUS=") == 1
      and "JARVIS_CI_STATUS=failure" not in text
      and "JARVIS_TESTS_STATUS=failure" not in text)

print(f"\nproject health CI identity safety: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
