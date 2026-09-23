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
import re
from urllib.parse import urlparse

ACTIVE_TASK_STATES = frozenset({"QUEUED", "RUNNING", "PROCESSING"})
FAILED_TASK_STATES = frozenset({"FAILED", "ERROR"})
CI_JOB_ENV = {
    "backend_tests": "JARVIS_CI_BACKEND_STATUS",
    "ios": "JARVIS_CI_IOS_STATUS",
    "mac": "JARVIS_CI_MAC_STATUS",
}
BUILD_JOB_ENV = {
    "ios": "JARVIS_IOS_BUILD_STATUS",
    "mac": "JARVIS_MAC_BUILD_STATUS",
}
TEST_STEP_ENV = {
    "backend_tests": "JARVIS_BACKEND_TEST_STATUS",
    "mac": "JARVIS_MAC_TEST_STATUS",
}
TEST_JOB_NAMES = ("backend_tests", "mac")
VALID_STATUSES = frozenset({"success", "failure", "unknown"})
CI_METADATA_FRESHNESS_SECONDS = 24 * 60 * 60
CI_METADATA_FUTURE_SKEW_SECONDS = 5 * 60
_OWNER_ACTION_FIELDS = ("type", "action", "agent", "task_id")
_RESERVED_PLANNED_OWNER_ACTION_TYPES = frozenset({"approval"})
_MAX_OWNER_ACTIONS = 20
_MAX_OWNER_ACTION_FIELD_LENGTH = 240
_MAX_OWNER_EXPIRY_ABS = 10 ** 20
_MAX_TASK_STATE_LENGTH = 64
_MAX_RUNTIME_FIELD_LENGTH = 240
_MAX_BUILD_SHA_LENGTH = 40
_MAX_CI_ID_LENGTH = 32
_MAX_BRANCH_LENGTH = 200
_MAX_REPOSITORY_LENGTH = 200
_MAX_RUN_URL_LENGTH = 512
_MAX_CI_TIMESTAMP_LENGTH = 32
_BUILD_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_DIGITS_RE = re.compile(r"^[0-9]+$")
_GITHUB_RUN_PATH_RE = re.compile(r"^/([^/]+/[^/]+)/actions/runs/([0-9]+)/?$")
_GENERATED_AT_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_MILESTONE_SOURCES = frozenset({"github_repository_variables", "version_controlled_plan", "mixed", "unknown"})
_OWNER_ACTION_SOURCES = frozenset({"version_controlled_plan", "unknown"})


def _text(env, key, default=""):
    return str(env.get(key, default) or default).strip()


def _bounded_runtime_text(value, default="", max_length=_MAX_RUNTIME_FIELD_LENGTH):
    """Return a single bounded runtime evidence line, failing closed when malformed."""
    value = str(value or "").strip()
    if not value or "\n" in value or "\r" in value or len(value) > max_length:
        return default
    return value


def _status(env, key):
    value = _text(env, key, "unknown").lower()
    return value if value in VALID_STATUSES else "unknown"


def _reported(value):
    value = str(value or "").strip().lower()
    return "reported" if value and value != "unknown" else "unknown"


def _provenance(env, key, allowed):
    value = _text(env, key, "unknown").lower()
    return value if value in allowed else "unknown"


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
    """Return true when any CI/build/test success claim needs freshness proof."""
    if any(ci.get(key) == "success" for key in ("status", "build_status", "tests_status")):
        return True
    for key in ("jobs", "build_jobs", "test_jobs"):
        if any(status == "success" for status in (ci.get(key) or {}).values()):
            return True
    return False


def _valid_build_sha(value):
    """Return a bounded Git commit identity or fail closed to an empty value."""
    text = _bounded_runtime_text(value, max_length=_MAX_BUILD_SHA_LENGTH)
    return text if _BUILD_SHA_RE.fullmatch(text) else ""


def _valid_ci_digits(value):
    """Return one bounded numeric GitHub Actions identifier."""
    text = _bounded_runtime_text(value, max_length=_MAX_CI_ID_LENGTH)
    return text if _DIGITS_RE.fullmatch(text) else ""


def _valid_ci_branch(value):
    return _bounded_runtime_text(value, max_length=_MAX_BRANCH_LENGTH)


def _valid_ci_repository(value):
    text = _bounded_runtime_text(value, max_length=_MAX_REPOSITORY_LENGTH)
    return text if _REPOSITORY_RE.fullmatch(text) else ""


def _valid_ci_generated_at(value):
    """Reflect only the bounded UTC timestamp shape emitted by CI."""
    text = _bounded_runtime_text(value, max_length=_MAX_CI_TIMESTAMP_LENGTH)
    if not text or not _GENERATED_AT_RE.fullmatch(text):
        return ""
    return text if _parse_timestamp(text) is not None else ""


def _valid_ci_run_url(value):
    """Reflect only a bounded canonical public GitHub Actions run URL."""
    text = _bounded_runtime_text(value, max_length=_MAX_RUN_URL_LENGTH)
    if not text:
        return ""
    parsed = urlparse(text)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return ""
    match = _GITHUB_RUN_PATH_RE.fullmatch(parsed.path)
    if not match:
        return ""
    repository = match.group(1)
    if len(repository) > _MAX_REPOSITORY_LENGTH or not _REPOSITORY_RE.fullmatch(repository):
        return ""
    return text


def _ci_run_identity_present(ci):
    """Require one coherent public GitHub Actions run identity before showing green.

    A run id + URL pair is not enough: run number, URL repository, reported
    repository, branch, and run id must all be present; URL repository/run id agree. This keeps a copied or
    partially stripped CI artifact from proving the wrong repository as healthy.
    """
    run_id = str(ci.get("run_id") or "").strip()
    run_number = str(ci.get("run_number") or "").strip()
    run_url = str(ci.get("run_url") or "").strip()
    branch = str(ci.get("branch") or "").strip()
    repository = str(ci.get("repository") or "").strip()
    if (
        not run_id.isdigit()
        or not run_number.isdigit()
        or not branch
        or "\n" in branch
        or "\r" in branch
        or not _REPOSITORY_RE.fullmatch(repository)
    ):
        return False

    parsed = urlparse(run_url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return False
    match = _GITHUB_RUN_PATH_RE.fullmatch(parsed.path)
    return bool(match and match.group(1) == repository and match.group(2) == run_id)


def _ci_identity_complete(ci, build_sha):
    """Return true only when green CI is anchored to an exact build and run."""
    return bool(_valid_build_sha(build_sha) and _ci_run_identity_present(ci))


def _evidence_gated_status(status, freshness_state, ci, required_jobs, job_statuses=None, build_sha=""):
    """Fail closed when aggregate success disagrees with its required evidence.

    Freshness alone is not sufficient proof of green: a successful aggregate
    needs an inspectable run identity and every required job/step must itself be
    successful. Explicit required failures remain visible even when an aggregate
    is corrupt, stale, incomplete, or unknown.
    """
    jobs = (ci.get("jobs") or {}) if job_statuses is None else (job_statuses or {})
    required = [jobs.get(name, "unknown") for name in required_jobs]
    if any(job_status == "failure" for job_status in required):
        return "failure"

    gated = _freshness_gated_status(status, freshness_state)
    if gated != "success":
        return gated
    if not _ci_identity_complete(ci, build_sha):
        return "unknown"
    if not required or not all(job_status == "success" for job_status in required):
        return "unknown"
    return "success"


def _ci_snapshot(env):
    jobs = {name: _status(env, key) for name, key in CI_JOB_ENV.items()}
    build_jobs = {name: _status(env, key) for name, key in BUILD_JOB_ENV.items()}
    test_jobs = {name: _status(env, key) for name, key in TEST_STEP_ENV.items()}
    return {
        "status": _status(env, "JARVIS_CI_STATUS"),
        "build_status": _status(env, "JARVIS_BUILD_STATUS"),
        "tests_status": _status(env, "JARVIS_TESTS_STATUS"),
        "run_id": _valid_ci_digits(_text(env, "JARVIS_CI_RUN_ID")),
        "run_number": _valid_ci_digits(_text(env, "JARVIS_CI_RUN_NUMBER")),
        "run_url": _valid_ci_run_url(_text(env, "JARVIS_CI_RUN_URL")),
        "branch": _valid_ci_branch(_text(env, "JARVIS_CI_BRANCH")),
        "repository": _valid_ci_repository(_text(env, "JARVIS_CI_REPOSITORY")),
        "metadata_generated_at": _valid_ci_generated_at(_text(env, "JARVIS_CI_METADATA_GENERATED_AT")),
        "jobs": jobs,
        "build_jobs": build_jobs,
        "test_jobs": test_jobs,
        "has_build_job_evidence": any(_text(env, key) for key in BUILD_JOB_ENV.values()),
        "has_test_job_evidence": any(_text(env, key) for key in TEST_STEP_ENV.values()),
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
            if item.get("type", "").lower() in _RESERVED_PLANNED_OWNER_ACTION_TYPES:
                item["type"] = "project_action"
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
    build_sha = _valid_build_sha(_text(env, "JARVIS_BUILD_SHA"))
    identity_complete = _ci_identity_complete(ci, build_sha)
    freshness = _ci_metadata_freshness(ci["metadata_generated_at"], now=now)
    effective_ci_status = _evidence_gated_status(
        ci["status"], freshness["state"], ci, tuple(CI_JOB_ENV), build_sha=build_sha
    )
    effective_build_status = _evidence_gated_status(
        ci["build_status"], freshness["state"], ci, tuple(BUILD_JOB_ENV), ci["build_jobs"], build_sha
    )
    test_evidence_jobs = ci["test_jobs"] if ci["has_test_job_evidence"] else ci["jobs"]
    effective_tests_status = _evidence_gated_status(
        ci["tests_status"], freshness["state"], ci, TEST_JOB_NAMES, test_evidence_jobs, build_sha
    )
    failed_ci_jobs = []
    for job, status in ci["jobs"].items():
        if status == "failure":
            failed_ci_jobs.append(job)
            blocker = {"type": "ci_job", "job": job, "status": status}
            if ci["run_url"]:
                blocker["run_url"] = ci["run_url"]
            blocker_items.append(blocker)

    # Exact build/test step evidence can be red even when the containing GitHub
    # job result is absent or contradictory (for example, a partially copied
    # handoff artifact). Surface that failure as a real blocker instead of
    # returning a red aggregate with blocker count zero. When the containing
    # CI job is already red, the ci_job blocker remains the single canonical
    # blocker so one underlying failure is not double-counted.
    for job, status in ci["build_jobs"].items():
        if status == "failure" and ci["jobs"].get(job) != "failure":
            blocker_items.append({"type": "build_step", "job": job, "status": status})
    for job, status in ci["test_jobs"].items():
        if status == "failure" and ci["jobs"].get(job) != "failure":
            blocker_items.append({"type": "test_step", "job": job, "status": status})

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

    # Fresh green claims must be tied to one exact build + coherent GitHub run.
    # Surface identity loss separately from missing job/step evidence so the owner
    # can distinguish a deployment-handoff problem from an actual test/build gap.
    if freshness["state"] == "fresh" and _ci_success_evidence_present(ci) and not identity_complete:
        blocker_items.append({"type": "ci_identity", "state": "incomplete"})

    # Even with coherent identity, aggregate success still needs every exact
    # required job/step. A post-build screenshot failure may make CI red while
    # build/tests remain independently truthful.
    if freshness["state"] == "fresh" and identity_complete and not failed_ci_jobs and (
        (ci["status"] == "success" and effective_ci_status != "success")
        or (ci["build_status"] == "success" and effective_build_status != "success")
        or (ci["tests_status"] == "success" and effective_tests_status != "success")
    ):
        blocker_items.append({"type": "ci_evidence", "state": "incomplete"})

    if kill_switch_engaged:
        blocker_items.append({"type": "kill_switch", "state": "engaged"})

    approval_action_items = _owner_action_items(pending_approvals)
    planned_owner_source = _provenance(env, "JARVIS_OWNER_ACTIONS_SOURCE", _OWNER_ACTION_SOURCES)
    # Defense in depth: a direct process environment value must not become an
    # owner instruction unless its provenance is the reviewed version-controlled
    # plan. The metadata loader enforces the same contract, but this response
    # boundary can also be called directly in tests, local tools, or alternate
    # runtimes that bypass that loader. Fail closed instead of surfacing an
    # untrusted action with `unknown` provenance.
    planned_action_items = (
        _planned_owner_action_items(env)
        if planned_owner_source == "version_controlled_plan"
        else []
    )
    owner_action_items = approval_action_items + planned_action_items
    milestone_source = _provenance(env, "JARVIS_MILESTONE_SOURCE", _MILESTONE_SOURCES)
    if approval_action_items and planned_action_items:
        owner_actions_source = "mixed"
    elif approval_action_items:
        owner_actions_source = "runtime_approvals"
    elif planned_action_items:
        owner_actions_source = planned_owner_source
    else:
        owner_actions_source = "unknown"
    phase = _bounded_runtime_text(
        _text(env, "JARVIS_CURRENT_PHASE", "unknown"), default="unknown"
    )
    current_milestone = _bounded_runtime_text(
        _text(env, "JARVIS_CURRENT_MILESTONE", "unknown"), default="unknown"
    )
    next_milestone = _bounded_runtime_text(
        _text(env, "JARVIS_NEXT_MILESTONE", "unknown"), default="unknown"
    )
    return {
        "ok": True,
        "phase": phase,
        "current_milestone": current_milestone,
        "next_milestone": next_milestone,
        "build_sha": build_sha,
        # Display-facing statuses are freshness/evidence-gated. Raw reported values
        # remain available in the nested `ci` object for diagnostics inspection.
        "build_status": effective_build_status,
        "ci_status": effective_ci_status,
        "tests_status": effective_tests_status,
        "ci_run_id": ci["run_id"],
        "ci_run_number": ci["run_number"],
        "ci_run_url": ci["run_url"],
        "ci_branch": ci["branch"],
        "ci_repository": ci["repository"],
        "ci_metadata_generated_at": ci["metadata_generated_at"],
        "ci_metadata_state": freshness["state"],
        "ci_metadata_age_seconds": freshness["age_seconds"],
        "ci_jobs": ci["jobs"],
        "build_jobs": ci["build_jobs"],
        "test_jobs": ci["test_jobs"],
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
            "ci_run": "reported" if _ci_run_identity_present(ci) else "unknown",
            "ci_identity": "reported" if identity_complete else "unknown",
            "ci_freshness": freshness["state"],
            "milestones": _planning_evidence(phase, current_milestone, next_milestone),
            "milestone_source": milestone_source,
            "owner_actions": owner_actions_source,
        },
    }
