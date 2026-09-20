#!/usr/bin/env python3
"""Generate fail-closed Project Health metadata from completed CI job results."""
import argparse
import json
import os
from pathlib import Path

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


def build_metadata(env=None):
    """Return truthful CI metadata; absent evidence stays unknown."""
    env = os.environ if env is None else env
    jobs = {
        "backend_tests": _result(env, "JARVIS_BACKEND_TEST_RESULT"),
        "ios": _result(env, "JARVIS_IOS_RESULT"),
        "mac": _result(env, "JARVIS_MAC_RESULT"),
    }
    tests_status = _aggregate((jobs["backend_tests"], jobs["mac"]))
    build_sha = _value(env, "GITHUB_SHA", default="")
    planning_keys = (
        "JARVIS_CURRENT_PHASE",
        "JARVIS_CURRENT_MILESTONE",
        "JARVIS_NEXT_MILESTONE",
    )

    return {
        "build_sha": build_sha,
        "ci_status": _aggregate(jobs.values()),
        "tests_status": tests_status,
        "phase": _value(env, "JARVIS_CURRENT_PHASE"),
        "current_milestone": _value(env, "JARVIS_CURRENT_MILESTONE"),
        "next_milestone": _value(env, "JARVIS_NEXT_MILESTONE"),
        "jobs": jobs,
        "evidence": {
            "build": "github_actions" if build_sha else "unknown",
            "ci": "github_actions",
            "tests": "github_actions",
            "milestones": "github_repository_variables"
            if any(_value(env, key) != "unknown" for key in planning_keys)
            else "unknown",
        },
    }


def _write_env(path, metadata):
    """Write the exact environment keys consumed by GET /project/health."""
    lines = [
        f"JARVIS_BUILD_SHA={metadata['build_sha']}",
        f"JARVIS_CI_STATUS={metadata['ci_status']}",
        f"JARVIS_TESTS_STATUS={metadata['tests_status']}",
        f"JARVIS_CURRENT_PHASE={metadata['phase']}",
        f"JARVIS_CURRENT_MILESTONE={metadata['current_milestone']}",
        f"JARVIS_NEXT_MILESTONE={metadata['next_milestone']}",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="project-health-ci.json")
    parser.add_argument("--env-output", default="")
    args = parser.parse_args()

    metadata = build_metadata()
    Path(args.output).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.env_output:
        _write_env(args.env_output, metadata)


if __name__ == "__main__":
    main()
