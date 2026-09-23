"""Safe, opt-in runtime loader for Project Health CI metadata.

The CI workflow emits ``project-health.env``. A deployment may mount/copy that
artifact and point ``JARVIS_PROJECT_HEALTH_METADATA_PATH`` at it. Only Project
Health keys are accepted; explicit process environment values always win.
"""
from datetime import datetime
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

HEALTH_KEYS = {
    "JARVIS_BUILD_SHA",
    "JARVIS_BUILD_STATUS",
    "JARVIS_CI_STATUS",
    "JARVIS_TESTS_STATUS",
    "JARVIS_CURRENT_PHASE",
    "JARVIS_CURRENT_MILESTONE",
    "JARVIS_NEXT_MILESTONE",
    "JARVIS_OWNER_ACTIONS_JSON",
    "JARVIS_MILESTONE_SOURCE",
    "JARVIS_OWNER_ACTIONS_SOURCE",
    "JARVIS_CI_RUN_ID",
    "JARVIS_CI_RUN_NUMBER",
    "JARVIS_CI_RUN_URL",
    "JARVIS_CI_BRANCH",
    "JARVIS_CI_METADATA_GENERATED_AT",
    "JARVIS_CI_BACKEND_STATUS",
    "JARVIS_CI_IOS_STATUS",
    "JARVIS_CI_MAC_STATUS",
    "JARVIS_IOS_BUILD_STATUS",
    "JARVIS_MAC_BUILD_STATUS",
    "JARVIS_BACKEND_TEST_STATUS",
    "JARVIS_MAC_TEST_STATUS",
}
STATUS_KEYS = {
    "JARVIS_BUILD_STATUS",
    "JARVIS_CI_STATUS",
    "JARVIS_TESTS_STATUS",
    "JARVIS_CI_BACKEND_STATUS",
    "JARVIS_CI_IOS_STATUS",
    "JARVIS_CI_MAC_STATUS",
    "JARVIS_IOS_BUILD_STATUS",
    "JARVIS_MAC_BUILD_STATUS",
    "JARVIS_BACKEND_TEST_STATUS",
    "JARVIS_MAC_TEST_STATUS",
}
VALID_STATUSES = {"success", "failure", "unknown"}
PROVENANCE_VALUES = {
    "JARVIS_MILESTONE_SOURCE": {"github_repository_variables", "version_controlled_plan", "mixed", "unknown"},
    "JARVIS_OWNER_ACTIONS_SOURCE": {"version_controlled_plan", "unknown"},
}
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_DIGITS_RE = re.compile(r"^[0-9]+$")
_GITHUB_RUN_PATH_RE = re.compile(r"^/[^/]+/[^/]+/actions/runs/([0-9]+)/?$")
_GENERATED_AT_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)
_OWNER_ACTION_FIELDS = {"type", "action", "agent", "task_id"}
_MAX_OWNER_ACTIONS = 20
_MAX_OWNER_ACTION_FIELD_LENGTH = 240
_MAX_OWNER_ACTIONS_JSON_LENGTH = 8192


def _valid_owner_actions_json(value):
    if not value:
        return True
    if len(value) > _MAX_OWNER_ACTIONS_JSON_LENGTH:
        return False
    try:
        data = json.loads(value)
    except (ValueError, TypeError):
        return False
    if not isinstance(data, list) or len(data) > _MAX_OWNER_ACTIONS:
        return False
    for item in data:
        if not isinstance(item, dict) or not item or not item.keys() <= _OWNER_ACTION_FIELDS:
            return False
        if not isinstance(item.get("action"), str) or not item["action"].strip():
            return False
        for field_value in item.values():
            if not isinstance(field_value, str):
                return False
            if not field_value.strip() or len(field_value) > _MAX_OWNER_ACTION_FIELD_LENGTH:
                return False
            if "\n" in field_value or "\r" in field_value:
                return False
    return True


def _github_run_id_from_url(value):
    """Return the GitHub Actions run id only for the expected canonical HTTPS shape."""
    if not value:
        return None
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return None
    match = _GITHUB_RUN_PATH_RE.fullmatch(parsed.path)
    return match.group(1) if match else None


def _valid_generated_at(value):
    """Accept only the UTC timestamp shape emitted by the CI metadata producer."""
    if not value:
        return True
    if not _GENERATED_AT_RE.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except (TypeError, ValueError):
        return False
    return True


def _valid_value(key, value):
    if key in STATUS_KEYS:
        return value.lower() in VALID_STATUSES
    if key == "JARVIS_BUILD_SHA":
        return not value or bool(_SHA_RE.fullmatch(value))
    if key in {"JARVIS_CI_RUN_ID", "JARVIS_CI_RUN_NUMBER"}:
        return not value or bool(_DIGITS_RE.fullmatch(value))
    if key == "JARVIS_CI_RUN_URL":
        return not value or _github_run_id_from_url(value) is not None
    if key == "JARVIS_CI_METADATA_GENERATED_AT":
        return _valid_generated_at(value)
    if key == "JARVIS_CI_BRANCH":
        return "\n" not in value and "\r" not in value and len(value) <= 200
    if key == "JARVIS_OWNER_ACTIONS_JSON":
        return _valid_owner_actions_json(value)
    if key in PROVENANCE_VALUES:
        return value in PROVENANCE_VALUES[key]
    return True


def _drop_inconsistent_run_identity(staged, env):
    """Do not surface a clickable CI URL unless it agrees with the effective run id.

    Process environment values remain authoritative. If a staged artifact conflicts
    with an explicit deployment value, only the conflicting staged field is removed.
    """
    staged_url = staged.get("JARVIS_CI_RUN_URL")
    staged_id = staged.get("JARVIS_CI_RUN_ID")
    explicit_url = (env.get("JARVIS_CI_RUN_URL") or "").strip()
    explicit_id = (env.get("JARVIS_CI_RUN_ID") or "").strip()

    if staged_url:
        expected_id = explicit_id or staged_id or ""
        if expected_id and _github_run_id_from_url(staged_url) != expected_id:
            staged.pop("JARVIS_CI_RUN_URL", None)

    if staged_id and explicit_url:
        explicit_url_id = _github_run_id_from_url(explicit_url)
        if explicit_url_id and staged_id != explicit_url_id:
            staged.pop("JARVIS_CI_RUN_ID", None)


def _matches_explicit_build_identity(staged, env):
    """Reject CI artifacts that cannot prove the deployed build and branch identity.

    Explicit deployment identity is authoritative. If deployment supplies a build
    SHA or branch, the staged artifact must carry the same field and value. Missing
    identity is therefore rejected just like a conflict; otherwise a fresh green
    artifact with its identity omitted could be mixed with the current deployment
    identity and falsely appear to prove the wrong build.
    """
    for key in ("JARVIS_BUILD_SHA", "JARVIS_CI_BRANCH"):
        staged_value = (staged.get(key) or "").strip()
        explicit_value = (env.get(key) or "").strip()
        if explicit_value and (not staged_value or staged_value != explicit_value):
            return False
    return True


def load_health_metadata(path, environ=None):
    """Load allow-listed health metadata without overriding explicit env.

    Missing/unreadable files fail closed and never break backend startup.
    Unknown keys are ignored so a metadata file cannot inject secrets or other
    runtime configuration.
    """
    env = os.environ if environ is None else environ
    path = str(path or "").strip()
    if not path:
        return False

    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return False

    staged = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key not in HEALTH_KEYS or not _valid_value(key, value):
            continue
        staged[key] = value

    _drop_inconsistent_run_identity(staged, env)

    if not staged or not _matches_explicit_build_identity(staged, env):
        return False

    for key, value in staged.items():
        env.setdefault(key, value)
    return True


def load_configured_health_metadata(environ=None):
    """Load only when a deployment explicitly provides a metadata path."""
    env = os.environ if environ is None else environ
    path = (env.get("JARVIS_PROJECT_HEALTH_METADATA_PATH") or "").strip()
    if not path:
        return False
    return load_health_metadata(path, env)
