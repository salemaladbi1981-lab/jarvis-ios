"""Truthful Project Health snapshot assembly.

This module is intentionally pure: it receives runtime task/approval data and
reads only allow-listed Project Health environment variables. It never reaches
GitHub, changes state, or exposes approval params/secrets.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os

ACTIVE_TASK_STATES = frozenset({"QUEUED", "RUNNING", "PROCESSING"})
FAILED_TASK_STATES = frozenset({"FAILED", "ERROR"})
CI_JOB_ENV = {
    "backend_tests": "JARVIS_CI_BACKEND_STATUS",
    "ios": "JARVIS_CI_IOS_STATUS",
    "mac": "JARVIS_CI_MAC_STATUS",
}
VALID_STATUSES = frozenset({"success", "failure", "unknown"})
CI_METADATA_FRESHNESS_SECONDS = 24 * 60 * 60
CI_METADATA_FUTURE_SKEW_SECONDS = 5 * 60


def _text(env, key, default=""):
    return str(env.get(key, default) or default).strip()


def _status(env, key):
    value = _text(env, key, "unknown").lower()
    return value if value in VALID_STATUSES else "unknown"


def _reported(value):
    value = str(value or "").strip().lower()
    return "reported" if value and value != "unknown" else "unknown"


def _planning_evidence(phase, current_milestone, next_milestone):
    values = [phase, current_milestone, next_milestone]
    known = sum(1 for value in values if _reported(value) == "reported")
    if known == len(values):
        return "reported"
    if known:
        return "partial"
    return "unknown"


def _parse_timestamp(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _ci_metadata_freshness(generated_at, now=None):
    """Return freshness of the CI artifact without making a network request.

    A mounted Project Health artifact can remain present after it stops being
    representative of the current build. Treat metadata older than 24 hours as
    stale and reject timestamps materially in the future. Small clock skew is
    tolerated and clamped to age zero.
    """
    generated = _parse_timestamp(generated_at)
    if generated is None:
        return {"state": "unknown", "age_seconds": None}

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)

    age = (current - generated).total_seconds()
    if age < -CI_METADATA_FUTURE_SKEW_SECONDS:
        return {"state": "unknown", "age_seconds": None}

    age_seconds = max(0, int(age))
    state = "fresh" if age_seconds <= CI_METADATA_FRESHNESS_SECONDS else "stale"
    return {"state": state, "age_seconds": age_seconds}


def _ci_snapshot(env):
    jobs = {name: _status(env, key) for name, key in CI_JOB_ENV.items()}
    return {
        "status": _status(env, "JARVIS_CI_STATUS"),
        "tests_status": _status(env, "JARVIS_TESTS_STATUS"),
        "run_id": _text(env, "JARVIS_CI_RUN_ID"),
        "run_number": _text(env, "JARVIS_CI_RUN_NUMBER"),
        "run_url": _text(env, "JARVIS_CI_RUN_URL"),
        "branch": _text(env, "JARVIS_CI_BRANCH"),
        "metadata_generated_at": _text(env, "JARVIS_CI_METADATA_GENERATED_AT"),
        "jobs": jobs,
    }


def _owner_action_items(pending_approvals):
    """Return only fields the owner needs to decide; never echo params/payloads."""
    items = []
    for approval in pending_approvals or []:
        if not isinstance(approval, dict):
            continue
        item = {"type": "approval"}
        for key in ("approval_id", "agent", "action", "task_id", "expires"):
            value = approval.get(key)
            if value is not None:
                item[key] = value
        items.append(item)
    return items


def build_project_health(
    *,
    tasks,
    job_state_for,
    pending_approvals,
    capability_count,
    kill_switch_engaged,
    provider,
    workspace_id,
    environ=None,
    now=None,
):
    """Build a backward-compatible, evidence-rich Project Health response."""
    env = os.environ if environ is None else environ
    task_list = [task for task in (tasks or []) if isinstance(task, dict)]
    state_counts = {}
    active = 0
    failed = 0
    blocker_items = []

    for task in task_list:
        task_id = task.get("task_id")
        job_state = job_state_for(task_id) if task_id else None
        state = (job_state or {}).get("state") or task.get("status") or "UNKNOWN"
        state = str(state).upper()
        state_counts[state] = state_counts.get(state, 0) + 1
        if state in ACTIVE_TASK_STATES:
            active += 1
        if state in FAILED_TASK_STATES:
            failed += 1
            blocker = {"type": "task_failure", "state": state}
            if task_id:
                blocker["task_id"] = task_id
            blocker_items.append(blocker)

    ci = _ci_snapshot(env)
    freshness = _ci_metadata_freshness(ci["metadata_generated_at"], now=now)
    failed_ci_jobs = []
    for job, status in ci["jobs"].items():
        if status == "failure":
            failed_ci_jobs.append(job)
            blocker = {"type": "ci_job", "job": job, "status": status}
            if ci["run_url"]:
                blocker["run_url"] = ci["run_url"]
            blocker_items.append(blocker)

    # Preserve an overall failure even if older metadata lacks per-job results.
    if ci["status"] == "failure" and not failed_ci_jobs:
        blocker = {"type": "ci", "status": "failure"}
        if ci["run_url"]:
            blocker["run_url"] = ci["run_url"]
        blocker_items.append(blocker)

    # A previously successful artifact is not current evidence forever. Surface
    # staleness as an explicit owner-safe blocker instead of silently presenting
    # old CI as if it were current.
    if freshness["state"] == "stale":
        blocker = {
            "type": "ci_metadata",
            "state": "stale",
            "age_seconds": freshness["age_seconds"],
        }
        if ci["run_url"]:
            blocker["run_url"] = ci["run_url"]
        blocker_items.append(blocker)

    if kill_switch_engaged:
        blocker_items.append({"type": "kill_switch", "state": "engaged"})

    owner_action_items = _owner_action_items(pending_approvals)
    phase = _text(env, "JARVIS_CURRENT_PHASE", "unknown")
    current_milestone = _text(env, "JARVIS_CURRENT_MILESTONE", "unknown")
    next_milestone = _text(env, "JARVIS_NEXT_MILESTONE", "unknown")
    build_sha = _text(env, "JARVIS_BUILD_SHA")

    return {
        "ok": True,
        "phase": phase,
        "current_milestone": current_milestone,
        "next_milestone": next_milestone,
        "build_sha": build_sha,
        "ci_status": ci["status"],
        "tests_status": ci["tests_status"],
        "ci_run_id": ci["run_id"],
        "ci_run_number": ci["run_number"],
        "ci_run_url": ci["run_url"],
        "ci_branch": ci["branch"],
        "ci_metadata_generated_at": ci["metadata_generated_at"],
        "ci_metadata_state": freshness["state"],
        "ci_metadata_age_seconds": freshness["age_seconds"],
        "ci_jobs": ci["jobs"],
        "ci": ci,
        "provider": provider,
        "kill_switch": bool(kill_switch_engaged),
        "workspace_id": workspace_id,
        "tasks_total": len(task_list),
        "tasks_active": active,
        "tasks_failed": failed,
        "task_states": state_counts,
        "pending_approvals": len(owner_action_items),
        # Keep numeric legacy fields for existing clients, add detailed arrays beside them.
        "owner_actions": len(owner_action_items),
        "owner_action_items": owner_action_items,
        "capability_count": int(capability_count or 0),
        "blockers": len(blocker_items),
        "blocker_items": blocker_items,
        "evidence": {
            "build": _reported(build_sha),
            "ci": _reported(ci["status"]),
            "tests": _reported(ci["tests_status"]),
            "ci_run": "reported" if ci["run_id"] and ci["run_url"] else "unknown",
            "ci_freshness": freshness["state"],
            "milestones": _planning_evidence(phase, current_milestone, next_milestone),
        },
    }
