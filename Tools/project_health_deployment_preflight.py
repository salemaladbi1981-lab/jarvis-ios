#!/usr/bin/env python3
"""Offline, secret-free Project Health deployment preflight.

Validates a CI handoff artifact against the exact build/branch intended for a
candidate deployment. It performs no network calls and mutates no production
state, so it can run on a staging host before any origin/tunnel cutover.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "phase3" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from project_health import build_project_health  # noqa: E402
from project_health_metadata import load_health_metadata  # noqa: E402

EXPECTED_REPOSITORY = "salemaladbi1981-lab/jarvis-ios"


def _parse_now(value):
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("--now must include a timezone")
    return parsed.astimezone(timezone.utc)


def preflight(
    metadata_path,
    expected_sha,
    expected_branch,
    now=None,
    expected_repository=EXPECTED_REPOSITORY,
    expected_run_id="",
    expected_run_number="",
):
    """Return a sanitized readiness verdict for one exact candidate CI run."""
    expected_sha = str(expected_sha or "").strip()
    expected_branch = str(expected_branch or "").strip()
    expected_repository = str(expected_repository or "").strip()
    expected_run_id = str(expected_run_id or "").strip()
    expected_run_number = str(expected_run_number or "").strip()
    if not expected_run_id.isdigit() or not expected_run_number.isdigit():
        return {
            "ok": False,
            "failed_checks": ["expected_run_identity"],
            "build_sha": expected_sha,
            "ci_branch": expected_branch,
        }
    env = {
        "JARVIS_BUILD_SHA": expected_sha,
        "JARVIS_CI_BRANCH": expected_branch,
        "JARVIS_CI_REPOSITORY": expected_repository,
        "JARVIS_CI_RUN_ID": expected_run_id,
        "JARVIS_CI_RUN_NUMBER": expected_run_number,
    }

    if not load_health_metadata(metadata_path, env):
        return {
            "ok": False,
            "failed_checks": ["metadata_rejected"],
            "build_sha": expected_sha,
            "ci_branch": expected_branch,
        }

    snapshot = build_project_health(
        tasks=[],
        job_state_for=lambda _task_id: None,
        pending_approvals=[],
        capability_count=0,
        kill_switch_engaged=False,
        provider="deployment-preflight",
        workspace_id="deployment-preflight",
        environ=env,
        now=now,
    )

    evidence = snapshot.get("evidence") if isinstance(snapshot.get("evidence"), dict) else {}
    owner_actions = int(snapshot.get("owner_actions") or 0)
    milestone_source = evidence.get("milestone_source", "unknown")
    owner_actions_source = evidence.get("owner_actions", "unknown")

    checks = {
        "build_identity": snapshot.get("build_sha") == expected_sha,
        "branch_identity": snapshot.get("ci_branch") == expected_branch,
        "repository_identity": snapshot.get("ci_repository") == expected_repository,
        "ci": snapshot.get("ci_status") == "success",
        "build": snapshot.get("build_status") == "success",
        "tests": snapshot.get("tests_status") == "success",
        "freshness": snapshot.get("ci_metadata_state") == "fresh",
        "run_identity": evidence.get("ci_run") == "reported",
        "planning_evidence": evidence.get("milestones") == "reported",
        "milestone_provenance": milestone_source in {
            "github_repository_variables", "version_controlled_plan", "mixed"
        },
        "owner_action_provenance": owner_actions == 0 or owner_actions_source in {
            "version_controlled_plan", "runtime_approvals", "mixed"
        },
        "blockers": int(snapshot.get("blockers") or 0) == 0,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]

    return {
        "ok": not failed_checks,
        "failed_checks": failed_checks,
        "build_sha": snapshot.get("build_sha") or "",
        "ci_branch": snapshot.get("ci_branch") or "",
        "ci_repository": snapshot.get("ci_repository") or "",
        "ci_run_id": snapshot.get("ci_run_id") or "",
        "ci_run_number": snapshot.get("ci_run_number") or "",
        "ci_status": snapshot.get("ci_status") or "unknown",
        "build_status": snapshot.get("build_status") or "unknown",
        "tests_status": snapshot.get("tests_status") or "unknown",
        "ci_metadata_state": snapshot.get("ci_metadata_state") or "unknown",
        "blockers": int(snapshot.get("blockers") or 0),
        "owner_actions": owner_actions,
        "phase": snapshot.get("phase") or "unknown",
        "current_milestone": snapshot.get("current_milestone") or "unknown",
        "next_milestone": snapshot.get("next_milestone") or "unknown",
        "milestone_source": milestone_source,
        "owner_actions_source": owner_actions_source,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-repository", default=EXPECTED_REPOSITORY)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-run-number", required=True)
    parser.add_argument("--now", default="")
    args = parser.parse_args()

    try:
        now = _parse_now(args.now)
    except ValueError as exc:
        print(json.dumps({"ok": False, "failed_checks": ["invalid_now"], "error": str(exc)}))
        return 2

    result = preflight(
        args.metadata,
        args.expected_sha,
        args.expected_branch,
        now=now,
        expected_repository=args.expected_repository,
        expected_run_id=args.expected_run_id,
        expected_run_number=args.expected_run_number,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
