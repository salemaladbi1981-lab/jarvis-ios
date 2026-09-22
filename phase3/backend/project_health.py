"""Truthful Project Health snapshot assembly.

This module is intentionally pure: it receives runtime task/approval data and
reads only allow-listed Project Health environment variables. It never reaches
GitHub, changes state, or exposes approval params/secrets.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os

ACTIVE_TASK_STATES = frozenset({"QUEUED", "RUNNING", "PROCESSING"})
FAILED_TASK_STATES = frozenset({"FAILED", "ERROR"})
CI_JOB_ENV = {
    "backend_tests": "JARVIS_CI_BACKEND_STATUS",
    "ios": "JARVIS_CI_IOS_STATUS",
    "mac": "JARVIS_CI_MAC_STATUS",
}
TEST_JOB_NAMES = ("backend_tests", "mac")
VALID_STATUSES = frozenset({"success", "failure", "unknown"})
CI_METADATA_FRESHNESS_SECONDS = 24 * 60 * 60
CI_METADATA_FUTURE_SKEW_SECONDS = 5 * 60
_OWNER_ACTION_FIELDS = ("type", "action", "agent", "task_id")
_MAX_OWNER_ACTIONS = 20
_MAX_OWNER_ACTION_FIELD_LENGTH = 240
_MAX_OWNER_EXPIRY_ABS = 10 ** 20
_MAX_TASK_STATE_LENGTH = 64


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


def _freshness_gated_status(status, freshness_state):
    """Never advertise green evidence unless its CI metadata is current.

    Failures stay visible even when metadata freshness is unavailable because
    suppressing a warning would be less safe. Success is downgraded to unknown
    unless the artifact has a valid, fresh timestamp.
    """
    normalized = str(status or "unknown").strip().lower()
    if normalized == "failure":
        return "failure"
    if freshness_state == "fresh" and normalized in VALID_STATUSES:
        return normalized
    return "unknown"


def _ci_success_evidence_present(ci):
    """Return true when CI carries any success claim that needs freshness proof."""
    if ci.get("status") == "success" or ci.get("tests_status") == "success":
        return True
    return any(status == "success" for status in (ci.get("jobs") or {}).values())


def _ci_run_identity_present(ci):
    """A green CI claim must be tied to an inspectable GitHub Actions run."""
    return bool(ci.get("run_id") and ci.get("run_url"))


def _evidence_gated_status(status, freshness_state, ci, required_jobs):
    """Fail closed when aggregate success disagrees with required CI evidence.

    Freshness alone is not sufficient proof of a green build: a successful
    aggregate must have an inspectable run identity and every required job must
    itself be successful. Any explicit required-job failure remains visible even
    if a corrupt/incomplete aggregate claims success or unknown.
    """
    jobs = ci.get("jobs") or {}
    required = [jobs.get(name, "unknown") for name in required_jobs]
    if any(job_status == "failure" for job_status in required):
        return "failure"

    gated = _freshness_gated_status(status, freshness_state)
    if gated != "success":
        return gated
    if not _ci_run_identity_present(ci):
        return "unknown"
    if not required or not all(job_status == "success" for job_status in required):
        return "unknown"
    return "success"


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


def _bounded_owner_text(value):
    """Return one bounded owner-visible line, or None for malformed data."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or "\n" in value or "\r" in value:
        return None
    if len(value) > _MAX_OWNER_ACTION_FIELD_LENGTH:
        return None
    return value


def _bounded_owner_expiry(value):
    """Return a JSON-safe owner-visible expiry, or None for malformed data."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if abs(value) <= _MAX_OWNER_EXPIRY_ABS else None
    if isinstance(value, float):
        if math.isfinite(value) and abs(value) <= _MAX_OWNER_EXPIRY_ABS:
            return value
        return None
    return _bounded_owner_text(value)


def _task_state(value):
    """Return a bounded task/job state for aggregation, or None if malformed."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or "\n" in value or "\r" in value:
        return None
    if len(value) > _MAX_TASK_STATE_LENGTH:
        return None
    return value.upper()


def _owner_action_items(pending_approvals):
    """Return only bounded fields the owner needs to decide; never echo params/payloads.

    Runtime approvals are treated as untrusted input at this response boundary.
    A malformed approval identifier is skipped entirely because it cannot support
    a real owner decision. Other malformed display fields are omitted while the
    valid approval remains visible.
    """
    items = []
    for approval in pending_approvals or []:
        if not isinstance(approval, dict):
            continue
        approval_id = _bounded_owner_text(approval.get("approval_id"))
        if not approval_id:
            continue

        item = {"type": "approval", "approval_id": approval_id}
        for key in ("agent", "action", "task_id"):
            field = _bounded_owner_text(approval.get(key))
            if field:
                item[key] = field

        expires = _bounded_owner_expiry(approval.get("expires"))
        if expires is not None:
            item["expires"] = expires
        items.append(item)
    return items


def _planned_owner_action_items(env):
    """Decode reviewed device/project actions from the Project Health artifact.

    The runtime accepts only a bounded, owner-safe schema. Invalid JSON or any
    unexpected/oversized values fail closed to an empty list; plan actions can
    never impersonate an approval because approval identifiers are not accepted.
    """
    raw = _text(env, "JARVIS_OWNER_ACTIONS_JSON")
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(value, list):
        return []

    items = []
    for candidate in value[:_MAX_OWNER_ACTIONS]:
        if not isinstance(candidate, dict):
            continue
        item = {}
        for key in _OWNER_ACTION_FIELDS:
            field = _bounded_owner_text(candidate.get(key))
            if field:
                item[key] = field
        if item.get("action"):
            item.setdefault("type", "project_action")
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
        raw_task_id = task.get("task_id")
        task_id = _bounded_owner_text(raw_task_id) if raw_task_id is not None else None
        if raw_task_id is not None and task_id is None:
            blocker_items.append({"type": "task_evidence", "state": "invalid_task_id"})

        job_state = None
        if task_id:
            try:
                candidate_job_state = job_state_for(task_id)
            except Exception:
                blocker_items.append({
                    "type": "task_evidence",
                    "state": "job_lookup_failed",
                    "task_id": task_id,
                })
            else:
                if candidate_job_state is None:
                    pass
                elif isinstance(candidate_job_state, dict):
                    job_state = candidate_job_state
                else:
                    blocker_items.append({
                        "type": "task_evidence",
                        "state": "invalid_job_state",
                        "task_id": task_id,
                    })

        state = None
        if job_state is not None:
            raw_job_state = job_state.get("state")
            state = _task_state(raw_job_state)
            if raw_job_state is not None and state is None:
                blocker = {"type": "task_evidence", "state": "invalid_state", "source": "job"}
                if task_id:
                    blocker["task_id"] = task_id
                blocker_items.append(blocker)

        if state is None:
            raw_task_state = task.get("status")
            state = _task_state(raw_task_state)
            if raw_task_state is not None and state is None:
                blocker = {"type": "task_evidence", "state": "invalid_state", "source": "task"}
                if task_id:
                    blocker["task_id"] = task_id
                blocker_items.append(blocker)

        state = state or "UNKNOWN"
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
    effective_ci_status = _evidence_gated_status(
        ci["status"], freshness["state"], ci, tuple(CI_JOB_ENV)
    )
    effective_tests_status = _evidence_gated_status(
        ci["tests_status"], freshness["state"], ci, TEST_JOB_NAMES
    )
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
    # old CI as if it were current. A present-but-unparseable or materially-future
    # timestamp is also evidence corruption/skew and must be visible to the owner.
    # Missing freshness proof is likewise a blocker whenever the artifact makes
    # any success claim; otherwise old metadata could still look green to clients.
    if freshness["state"] == "stale":
        blocker = {
            "type": "ci_metadata",
            "state": "stale",
            "age_seconds": freshness["age_seconds"],
        }
        if ci["run_url"]:
            blocker["run_url"] = ci["run_url"]
        blocker_items.append(blocker)
    elif freshness["state"] == "unknown" and (
        ci["metadata_generated_at"] or _ci_success_evidence_present(ci)
    ):
        blocker = {"type": "ci_metadata", "state": "unknown"}
        if ci["run_url"]:
            blocker["run_url"] = ci["run_url"]
        blocker_items.append(blocker)

    # Even fresh metadata cannot be called green when its aggregate success is
    # missing run identity or required-job success. Surface the inconsistency as
    # one owner-safe blocker; explicit job failures already have their own blocker.
    if freshness["state"] == "fresh" and not failed_ci_jobs and (
        (ci["status"] == "success" and effective_ci_status != "success")
        or (ci["tests_status"] == "success" and effective_tests_status != "success")
    ):
        blocker_items.append({"type": "ci_evidence", "state": "incomplete"})

    if kill_switch_engaged:
        blocker_items.append({"type": "kill_switch", "state": "engaged"})

    approval_action_items = _owner_action_items(pending_approvals)
    planned_action_items = _planned_owner_action_items(env)
    owner_action_items = approval_action_items + planned_action_items
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
        # Display-facing statuses are freshness/evidence-gated. Raw reported values
        # remain available in the nested `ci` object for diagnostics inspection.
        "ci_status": effective_ci_status,
        "tests_status": effective_tests_status,
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
        "pending_approvals": len(approval_action_items),
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
