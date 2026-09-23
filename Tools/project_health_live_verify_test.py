"""Regression checks for the read-only Project Health live verifier."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))

from project_health_live_verify import assess_snapshot, validate_url  # noqa: E402

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def green_snapshot():
    return {
        "build_sha": "a" * 40,
        "ci_branch": "chatgpt-overnight-2",
        "ci_run_id": "123456",
        "ci_run_number": "409",
        "ci_status": "success",
        "build_status": "success",
        "tests_status": "success",
        "ci_metadata_state": "fresh",
        "blockers": 0,
        "blocker_items": [],
        "owner_actions": 1,
        "owner_action_items": [{"type": "owner", "action": "review release"}],
        "phase": "project-health-production-handoff",
        "current_milestone": "Verify live Project Health",
        "next_milestone": "Release readiness",
        "evidence": {
            "build": "reported",
            "ci": "reported",
            "tests": "reported",
            "ci_run": "reported",
            "ci_freshness": "fresh",
            "milestones": "reported",
            "milestone_source": "version_controlled_plan",
            "owner_actions": "version_controlled_plan",
        },
    }


base = green_snapshot()
expected_sha = "a" * 40
expected_branch = "chatgpt-overnight-2"

check("green exact live snapshot passes", assess_snapshot(base, expected_sha, expected_branch)["ok"])

missing_expected = assess_snapshot(base, "", expected_branch)
check("caller must provide an explicit expected build identity", "expected_identity" in missing_expected["failed_checks"])

wrong_sha = dict(base, build_sha="b" * 40)
check("wrong deployed SHA fails closed", "build_identity" in assess_snapshot(wrong_sha, expected_sha, expected_branch)["failed_checks"])

wrong_branch = dict(base, ci_branch="main")
check("wrong deployed branch fails closed", "branch_identity" in assess_snapshot(wrong_branch, expected_sha, expected_branch)["failed_checks"])

stale = dict(base, ci_metadata_state="stale")
check("stale CI metadata cannot pass", "freshness" in assess_snapshot(stale, expected_sha, expected_branch)["failed_checks"])

bad_tests = dict(base, tests_status="failure")
check("failing tests remain visible", "tests" in assess_snapshot(bad_tests, expected_sha, expected_branch)["failed_checks"])

blocked = dict(base, blockers=1, blocker_items=[{"type": "ci_job"}])
check("live blockers prevent readiness", "blockers" in assess_snapshot(blocked, expected_sha, expected_branch)["failed_checks"])

missing_evidence = dict(base, evidence={"build": "reported"})
check("missing runtime evidence fails closed", "reported_evidence" in assess_snapshot(missing_evidence, expected_sha, expected_branch)["failed_checks"])

owner_mismatch = dict(base, owner_actions=2)
check("owner-action count must match sanitized items", "owner_action_coherence" in assess_snapshot(owner_mismatch, expected_sha, expected_branch)["failed_checks"])

no_milestone_source = dict(base, evidence=dict(base["evidence"], milestone_source="unknown"))
check(
    "live milestones need trusted provenance",
    "milestone_provenance" in assess_snapshot(no_milestone_source, expected_sha, expected_branch)["failed_checks"],
)

no_owner_source = dict(base, evidence=dict(base["evidence"], owner_actions="unknown"))
check(
    "live owner actions need trusted provenance",
    "owner_action_provenance" in assess_snapshot(no_owner_source, expected_sha, expected_branch)["failed_checks"],
)

empty_owner = dict(base, owner_actions=0, owner_action_items=[], evidence=dict(base["evidence"], owner_actions="unknown"))
check(
    "no owner actions does not require invented provenance",
    assess_snapshot(empty_owner, expected_sha, expected_branch)["ok"],
)

result = assess_snapshot(base, expected_sha, expected_branch)
check(
    "verdict is sanitized and omits owner payloads",
    "owner_action_items" not in result and "evidence" not in result and result["owner_actions"] == 1,
)

check("canonical HTTPS URL is accepted", validate_url("https://jarvis.example/project/health") == "https://jarvis.example/project/health")
for unsafe in (
    "http://jarvis.example/project/health",
    "https://user:secret@jarvis.example/project/health",
    "https://jarvis.example/project/health?token=secret",
    "https://jarvis.example/project/health#fragment",
):
    try:
        validate_url(unsafe)
        rejected = False
    except ValueError:
        rejected = True
    check("unsafe live URL rejected: " + unsafe.split(":", 1)[0], rejected)

print(f"\nproject health live verifier: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
