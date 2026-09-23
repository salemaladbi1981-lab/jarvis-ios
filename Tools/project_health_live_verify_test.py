"""Regression checks for the read-only Project Health live verifier."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Tools"))

from project_health_live_verify import assess_snapshot, validate_url  # noqa: E402

PASS = FAIL = 0
EXPECTED_SHA = "a" * 40
EXPECTED_BRANCH = "chatgpt-overnight-2"
EXPECTED_REPOSITORY = "salemaladbi1981-lab/jarvis-ios"
EXPECTED_RUN_ID = "123456"
EXPECTED_RUN_NUMBER = "409"


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def green_snapshot():
    return {
        "build_sha": EXPECTED_SHA,
        "ci_branch": EXPECTED_BRANCH,
        "ci_repository": EXPECTED_REPOSITORY,
        "ci_run_id": EXPECTED_RUN_ID,
        "ci_run_number": EXPECTED_RUN_NUMBER,
        "ci_run_url": f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/{EXPECTED_RUN_ID}",
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


def verdict(snapshot, **overrides):
    values = {
        "expected_sha": EXPECTED_SHA,
        "expected_branch": EXPECTED_BRANCH,
        "expected_repository": EXPECTED_REPOSITORY,
        "expected_run_id": EXPECTED_RUN_ID,
        "expected_run_number": EXPECTED_RUN_NUMBER,
    }
    values.update(overrides)
    return assess_snapshot(snapshot, **values)


base = green_snapshot()
check("green exact live snapshot passes", verdict(base)["ok"])

missing_expected = verdict(base, expected_run_id="")
check("caller must provide exact GitHub run identity", "expected_identity" in missing_expected["failed_checks"])

wrong_sha = dict(base, build_sha="b" * 40)
check("wrong deployed SHA fails closed", "build_identity" in verdict(wrong_sha)["failed_checks"])

wrong_branch = dict(base, ci_branch="main")
check("wrong deployed branch fails closed", "branch_identity" in verdict(wrong_branch)["failed_checks"])

wrong_repo = dict(base, ci_repository="other/repo")
check("wrong deployed repository fails closed", "repository_identity" in verdict(wrong_repo)["failed_checks"])

wrong_run_id = dict(base, ci_run_id="654321")
check("wrong live GitHub run id fails closed", "run_id_identity" in verdict(wrong_run_id)["failed_checks"])

wrong_run_number = dict(base, ci_run_number="410")
check("wrong live GitHub run number fails closed", "run_number_identity" in verdict(wrong_run_number)["failed_checks"])

wrong_run_url = dict(base, ci_run_url=f"https://github.com/{EXPECTED_REPOSITORY}/actions/runs/654321")
check("wrong live GitHub run URL fails closed", "run_url_identity" in verdict(wrong_run_url)["failed_checks"])

stale = dict(base, ci_metadata_state="stale")
check("stale CI metadata cannot pass", "freshness" in verdict(stale)["failed_checks"])

bad_tests = dict(base, tests_status="failure")
check("failing tests remain visible", "tests" in verdict(bad_tests)["failed_checks"])

blocked = dict(base, blockers=1, blocker_items=[{"type": "ci_job"}])
check("live blockers prevent readiness", "blockers" in verdict(blocked)["failed_checks"])

missing_blocker_contract = dict(base)
missing_blocker_contract.pop("blockers")
missing_blocker_contract.pop("blocker_items")
missing_blocker_verdict = verdict(missing_blocker_contract)
check(
    "missing blocker plumbing fails closed",
    "blocker_coherence" in missing_blocker_verdict["failed_checks"]
    and "blockers" in missing_blocker_verdict["failed_checks"],
)

string_blocker_count = dict(base, blockers="0")
check(
    "string blocker count cannot impersonate runtime contract",
    "blocker_coherence" in verdict(string_blocker_count)["failed_checks"],
)

missing_evidence = dict(base, evidence={"build": "reported"})
check("missing runtime evidence fails closed", "reported_evidence" in verdict(missing_evidence)["failed_checks"])

owner_mismatch = dict(base, owner_actions=2)
check("owner-action count must match sanitized items", "owner_action_coherence" in verdict(owner_mismatch)["failed_checks"])

missing_owner_contract = dict(base)
missing_owner_contract.pop("owner_actions")
missing_owner_contract.pop("owner_action_items")
check(
    "missing owner-action plumbing fails closed",
    "owner_action_coherence" in verdict(missing_owner_contract)["failed_checks"],
)

bool_owner_count = dict(base, owner_actions=False, owner_action_items=[])
check(
    "boolean owner-action count cannot impersonate integer contract",
    "owner_action_coherence" in verdict(bool_owner_count)["failed_checks"],
)

no_milestone_source = dict(base, evidence=dict(base["evidence"], milestone_source="unknown"))
check(
    "live milestones need trusted provenance",
    "milestone_provenance" in verdict(no_milestone_source)["failed_checks"],
)

no_owner_source = dict(base, evidence=dict(base["evidence"], owner_actions="unknown"))
check(
    "live owner actions need trusted provenance",
    "owner_action_provenance" in verdict(no_owner_source)["failed_checks"],
)

empty_owner = dict(base, owner_actions=0, owner_action_items=[], evidence=dict(base["evidence"], owner_actions="unknown"))
check(
    "no owner actions does not require invented provenance",
    verdict(empty_owner)["ok"],
)

missing_owner_evidence_map = dict(base["evidence"])
missing_owner_evidence_map.pop("owner_actions")
missing_owner_evidence = dict(
    base,
    owner_actions=0,
    owner_action_items=[],
    evidence=missing_owner_evidence_map,
)
check(
    "zero owner actions still requires an explicit provenance state",
    "owner_action_provenance" in verdict(missing_owner_evidence)["failed_checks"],
)

result = verdict(base)
check(
    "verdict is sanitized and omits owner payloads",
    "owner_action_items" not in result and "evidence" not in result and result["owner_actions"] == 1,
)
check("verdict reports exact run identity", result["ci_run_id"] == EXPECTED_RUN_ID and result["ci_run_number"] == EXPECTED_RUN_NUMBER)

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
