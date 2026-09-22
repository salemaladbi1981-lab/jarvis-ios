#!/usr/bin/env python3
"""Validate the actual current CI Project Health artifact through runtime code.

This runs only after the GitHub Actions verification jobs have settled and the
metadata pair has been generated. It proves the real artifact can be consumed
by the same safe loader and snapshot assembler used by the backend.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

from project_health import build_project_health
from project_health_metadata import load_health_metadata

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def main():
    env_path = Path(sys.argv[1] if len(sys.argv) > 1 else "project-health.env")
    json_path = Path(sys.argv[2] if len(sys.argv) > 2 else "project-health-ci.json")

    try:
        metadata = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        print(f"FAIL: unreadable metadata JSON: {exc}")
        return 1

    loaded = {}
    check("actual CI env artifact loads through runtime allow-list", load_health_metadata(env_path, loaded))

    snapshot = build_project_health(
        tasks=[],
        job_state_for=lambda _task_id: None,
        pending_approvals=[],
        capability_count=0,
        kill_switch_engaged=False,
        provider="ci-smoke",
        workspace_id="PERSONAL",
        environ=loaded,
    )

    expected_run_id = os.environ.get("GITHUB_RUN_ID", "")
    expected_run_number = os.environ.get("GITHUB_RUN_NUMBER", "")
    expected_branch = os.environ.get("GITHUB_REF_NAME", "")
    expected_sha = os.environ.get("GITHUB_SHA", "")
    server = os.environ.get("GITHUB_SERVER_URL", "").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    expected_url = f"{server}/{repository}/actions/runs/{expected_run_id}" if server and repository and expected_run_id else ""

    check(
        "runtime snapshot carries the exact current GitHub build identity",
        snapshot["build_sha"] == metadata.get("build_sha") == expected_sha
        and snapshot["ci_run_id"] == metadata.get("ci_run_id") == expected_run_id
        and snapshot["ci_run_number"] == metadata.get("ci_run_number") == expected_run_number
        and snapshot["ci_branch"] == metadata.get("ci_branch") == expected_branch
        and snapshot["ci_run_url"] == metadata.get("ci_run_url") == expected_url,
    )

    jobs = metadata.get("jobs") or {}
    check(
        "runtime snapshot preserves generated CI and test results",
        snapshot["ci_status"] == metadata.get("ci_status")
        and snapshot["tests_status"] == metadata.get("tests_status")
        and snapshot["ci_jobs"] == jobs,
    )

    check(
        "runtime snapshot carries reviewed milestone data",
        snapshot["phase"] == metadata.get("phase")
        and snapshot["current_milestone"] == metadata.get("current_milestone")
        and snapshot["next_milestone"] == metadata.get("next_milestone")
        and all(str(snapshot[key]).strip().lower() not in {"", "unknown"}
                for key in ("phase", "current_milestone", "next_milestone")),
    )

    check(
        "freshly generated CI evidence is reported as fresh and grounded",
        snapshot["ci_metadata_state"] == "fresh"
        and snapshot["evidence"]["build"] == "reported"
        and snapshot["evidence"]["ci"] == "reported"
        and snapshot["evidence"]["tests"] == "reported"
        and snapshot["evidence"]["ci_run"] == "reported"
        and snapshot["evidence"]["ci_freshness"] == "fresh"
        and snapshot["evidence"]["milestones"] == "reported",
    )

    if metadata.get("ci_status") == "success":
        check("green current CI artifact produces no CI blockers", snapshot["blockers"] == 0)
    else:
        check(
            "non-green current CI artifact remains visible as a blocker",
            any(item.get("type") in {"ci", "ci_job"} for item in snapshot["blocker_items"]),
        )

    check(
        "CI smoke introduces no synthetic owner action",
        snapshot["owner_actions"] == 0 and snapshot["owner_action_items"] == [],
    )

    print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
