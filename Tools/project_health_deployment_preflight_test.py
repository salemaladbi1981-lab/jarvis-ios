"""Regression checks for the offline Project Health deployment preflight."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "Tools" / "project_health_deployment_preflight.py"
PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


spec = importlib.util.spec_from_file_location("project_health_deployment_preflight", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SHA = "a" * 40
BRANCH = "chatgpt-overnight-2"
REPOSITORY = "salemaladbi1981-lab/jarvis-ios"
RUN_ID = "35794818108"
NOW = datetime(2026, 9, 23, 0, 0, 0, tzinfo=timezone.utc)


def metadata_text(**overrides):
    values = {
        "JARVIS_BUILD_SHA": SHA,
        "JARVIS_BUILD_STATUS": "success",
        "JARVIS_CI_STATUS": "success",
        "JARVIS_TESTS_STATUS": "success",
        "JARVIS_CURRENT_PHASE": "project-health-production-handoff",
        "JARVIS_CURRENT_MILESTONE": "Project Health production handoff",
        "JARVIS_NEXT_MILESTONE": "Release readiness",
        "JARVIS_OWNER_ACTIONS_JSON": '[{"type":"production_handoff","action":"verify deployment"}]',
        "JARVIS_MILESTONE_SOURCE": "version_controlled_plan",
        "JARVIS_OWNER_ACTIONS_SOURCE": "version_controlled_plan",
        "JARVIS_CI_RUN_ID": RUN_ID,
        "JARVIS_CI_RUN_NUMBER": "406",
        "JARVIS_CI_RUN_URL": f"https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/{RUN_ID}",
        "JARVIS_CI_BRANCH": BRANCH,
        "JARVIS_CI_REPOSITORY": REPOSITORY,
        "JARVIS_CI_METADATA_GENERATED_AT": "2026-09-22T23:04:56Z",
        "JARVIS_CI_BACKEND_STATUS": "success",
        "JARVIS_CI_IOS_STATUS": "success",
        "JARVIS_CI_MAC_STATUS": "success",
        "JARVIS_IOS_BUILD_STATUS": "success",
        "JARVIS_MAC_BUILD_STATUS": "success",
        "JARVIS_BACKEND_TEST_STATUS": "success",
        "JARVIS_MAC_TEST_STATUS": "success",
    }
    values.update(overrides)
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


with tempfile.TemporaryDirectory() as temp_dir:
    path = Path(temp_dir) / "project-health.env"
    path.write_text(metadata_text(), encoding="utf-8")
    good = module.preflight(path, SHA, BRANCH, now=NOW)

    check(
        "fresh green metadata for exact build and branch passes preflight",
        good["ok"] is True
        and good["failed_checks"] == []
        and good["ci_status"] == "success"
        and good["build_status"] == "success"
        and good["tests_status"] == "success"
        and good["ci_metadata_state"] == "fresh"
        and good["blockers"] == 0
        and good["owner_actions"] == 1
        and good["milestone_source"] == "version_controlled_plan"
        and good["owner_actions_source"] == "version_controlled_plan",
    )

    wrong_repo = module.preflight(path, SHA, BRANCH, now=NOW, expected_repository="other/repo")
    check(
        "candidate repository identity mismatch is rejected before cutover",
        wrong_repo["ok"] is False and wrong_repo["failed_checks"] == ["metadata_rejected"],
    )

    mismatch = module.preflight(path, "b" * 40, BRANCH, now=NOW)
    check(
        "candidate build identity mismatch is rejected before cutover",
        mismatch["ok"] is False
        and mismatch["failed_checks"] == ["metadata_rejected"],
    )

    stale = module.preflight(
        path,
        SHA,
        BRANCH,
        now=datetime(2026, 9, 25, 0, 0, 0, tzinfo=timezone.utc),
    )
    check(
        "stale CI evidence blocks deployment readiness",
        stale["ok"] is False
        and "freshness" in stale["failed_checks"]
        and stale["ci_metadata_state"] == "stale"
        and stale["blockers"] >= 1,
    )

    path.write_text(
        metadata_text(JARVIS_MAC_TEST_STATUS="failure"),
        encoding="utf-8",
    )
    failed_test = module.preflight(path, SHA, BRANCH, now=NOW)
    check(
        "exact failing test step blocks readiness even if aggregate metadata claims success",
        failed_test["ok"] is False
        and "tests" in failed_test["failed_checks"]
        and "blockers" in failed_test["failed_checks"]
        and failed_test["tests_status"] == "failure",
    )

    path.write_text(metadata_text(JARVIS_CI_RUN_URL=""), encoding="utf-8")
    missing_run = module.preflight(path, SHA, BRANCH, now=NOW)
    check(
        "green metadata without inspectable run identity fails closed",
        missing_run["ok"] is False
        and "run_identity" in missing_run["failed_checks"]
        and missing_run["ci_status"] == "unknown"
        and missing_run["blockers"] >= 1,
    )

    path.write_text(metadata_text(JARVIS_MILESTONE_SOURCE="unknown"), encoding="utf-8")
    missing_milestone_source = module.preflight(path, SHA, BRANCH, now=NOW)
    check(
        "reported milestones without provenance cannot pass deployment preflight",
        missing_milestone_source["ok"] is False
        and "milestone_provenance" in missing_milestone_source["failed_checks"],
    )

    path.write_text(metadata_text(JARVIS_OWNER_ACTIONS_SOURCE="unknown"), encoding="utf-8")
    missing_owner_source = module.preflight(path, SHA, BRANCH, now=NOW)
    check(
        "planned owner actions without provenance cannot pass deployment preflight",
        missing_owner_source["ok"] is False
        and "owner_action_provenance" in missing_owner_source["failed_checks"]
        and missing_owner_source["owner_actions"] == 1,
    )

    path.write_text(metadata_text(JARVIS_CURRENT_MILESTONE="unknown"), encoding="utf-8")
    missing_plan = module.preflight(path, SHA, BRANCH, now=NOW)
    check(
        "incomplete planning evidence blocks deployment readiness",
        missing_plan["ok"] is False
        and "planning_evidence" in missing_plan["failed_checks"],
    )


source = SCRIPT.read_text(encoding="utf-8")
check(
    "preflight remains offline and does not mutate deployment state",
    "requests" not in source
    and "urllib" not in source
    and "subprocess" not in source
    and "cloudflare" not in source.lower()
    and "gcloud" not in source.lower(),
)

print(f"\nproject health deployment preflight: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
