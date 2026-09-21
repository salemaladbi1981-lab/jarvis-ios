#!/usr/bin/env python3
"""Generate fail-closed Project Health metadata from completed CI job results."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN_PATH = ROOT / "docs" / "PROJECT-HEALTH-PLAN.json"
_FAILURE_RESULTS = {"failure", "cancelled", "timed_out", "action_required"}


def _value(env, key, default="unknown"):
    value = (env.get(key) or "").strip()
    return value or default


def _result(env, key):
    return _value(env, key).lower()


def _aggregate(results):
    values = list(results)
    if values and all(value == "success" for value in values):
        return "success"
    if any(value in _FAILURE_RESULTS for value in values):
        return "failure"
    return "unknown"


def _load_plan(path=DEFAULT_PLAN_PATH):
    """Load version-controlled milestone labels; malformed/missing plans fail closed."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        allowed = ("phase", "current_milestone", "next_milestone")
        return {
            key: str(data.get(key, "")).strip()
            for key in allowed
            if str(data.get(key, "")).strip()
        }
    except (OSError, ValueError, TypeError):
        return {}


def _planning_value(env, env_key, plan, plan_key):
    explicit = _value(env, env_key, default="")
    if explicit:
        return explicit, "github_repository_variables"
    fallback = str(plan.get(plan_key, "")).strip()
    if fallback:
        return fallback, "version_controlled_plan"
    return "unknown", "unknown"


def _run_url(env):
    server = _value(env, "GITHUB_SERVER_URL", default="")
    repository = _value(env, "GITHUB_REPOSITORY", default="")
    run_id = _value(env, "GITHUB_RUN_ID", default="")
    if server and repository and run_id:
        return f"{server.rstrip('/')}/{repository}/actions/runs/{run_id}"
    return ""


def build_metadata(env=None, plan_path=DEFAULT_PLAN_PATH, generated_at=None):
    """Return truthful CI metadata; absent evidence stays unknown.

    Repository variables remain authoritative. When they are not configured,
    milestone labels fall back to the reviewed version-controlled project plan.
    GitHub run/job fields are copied from GitHub-provided environment values;
    missing values remain empty/unknown rather than being guessed.
    """
    env = os.environ if env is None else env
    jobs = {
        "backend_tests": _result(env, "JARVIS_BACKEND_TEST_RESULT"),
        "ios": _result(env, "JARVIS_IOS_RESULT"),
        "mac": _result(env, "JARVIS_MAC_RESULT"),
    }
    tests_status = _aggregate((jobs["backend_tests"], jobs["mac"]))
    build_sha = _value(env, "GITHUB_SHA", default="")
    plan = _load_plan(plan_path)
    phase, phase_source = _planning_value(env, "JARVIS_CURRENT_PHASE", plan, "phase")
    current_milestone, current_source = _planning_value(
        env, "JARVIS_CURRENT_MILESTONE", plan, "current_milestone"
    )
    next_milestone, next_source = _planning_value(
        env, "JARVIS_NEXT_MILESTONE", plan, "next_milestone"
    )
    planning_sources = {phase_source, current_source, next_source}
    if planning_sources == {"github_repository_variables"}:
        milestone_source = "github_repository_variables"
    elif planning_sources == {"version_controlled_plan"}:
        milestone_source = "version_controlled_plan"
    elif "unknown" in planning_sources and len(planning_sources) == 1:
        milestone_source = "unknown"
    else:
        milestone_source = "mixed"

    generated_at = generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = _value(env, "GITHUB_RUN_ID", default="")
    run_number = _value(env, "GITHUB_RUN_NUMBER", default="")
    branch = _value(env, "GITHUB_REF_NAME", default="")

    return {
        "build_sha": build_sha,
        "ci_status": _aggregate(jobs.values()),
        "tests_status": tests_status,
        "phase": phase,
        "current_milestone": current_milestone,
        "next_milestone": next_milestone,
        "ci_run_id": run_id,
        "ci_run_number": run_number,
        "ci_run_url": _run_url(env),
        "ci_branch": branch,
        "metadata_generated_at": generated_at,
        "jobs": jobs,
        "evidence": {
            "build": "github_actions" if build_sha else "unknown",
            "ci": "github_actions",
            "tests": "github_actions",
            "milestones": milestone_source,
            "run": "github_actions" if run_id else "unknown",
        },
    }


def _write_env(path, metadata):
    """Write the exact secret-free environment keys consumed by GET /project/health."""
    jobs = metadata.get("jobs") or {}
    lines = [
        f"JARVIS_BUILD_SHA={metadata['build_sha']}",
        f"JARVIS_CI_STATUS={metadata['ci_status']}",
        f"JARVIS_TESTS_STATUS={metadata['tests_status']}",
        f"JARVIS_CURRENT_PHASE={metadata['phase']}",
        f"JARVIS_CURRENT_MILESTONE={metadata['current_milestone']}",
        f"JARVIS_NEXT_MILESTONE={metadata['next_milestone']}",
        f"JARVIS_CI_RUN_ID={metadata.get('ci_run_id', '')}",
        f"JARVIS_CI_RUN_NUMBER={metadata.get('ci_run_number', '')}",
        f"JARVIS_CI_RUN_URL={metadata.get('ci_run_url', '')}",
        f"JARVIS_CI_BRANCH={metadata.get('ci_branch', '')}",
        f"JARVIS_CI_METADATA_GENERATED_AT={metadata.get('metadata_generated_at', '')}",
        f"JARVIS_CI_BACKEND_STATUS={jobs.get('backend_tests', 'unknown')}",
        f"JARVIS_CI_IOS_STATUS={jobs.get('ios', 'unknown')}",
        f"JARVIS_CI_MAC_STATUS={jobs.get('mac', 'unknown')}",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="project-health-ci.json")
    parser.add_argument("--env-output", default="")
    parser.add_argument("--plan", default=str(DEFAULT_PLAN_PATH))
    args = parser.parse_args()

    metadata = build_metadata(plan_path=args.plan)
    Path(args.output).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.env_output:
        _write_env(args.env_output, metadata)


if __name__ == "__main__":
    main()
