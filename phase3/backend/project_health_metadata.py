"""Safe, opt-in runtime loader for Project Health CI metadata.

The CI workflow emits ``project-health.env``. A deployment may mount/copy that
artifact and point ``JARVIS_PROJECT_HEALTH_METADATA_PATH`` at it. Only Project
Health keys are accepted; explicit process environment values always win.
"""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

HEALTH_KEYS = {
    "JARVIS_BUILD_SHA",
    "JARVIS_CI_STATUS",
    "JARVIS_TESTS_STATUS",
    "JARVIS_CURRENT_PHASE",
    "JARVIS_CURRENT_MILESTONE",
    "JARVIS_NEXT_MILESTONE",
    "JARVIS_OWNER_ACTIONS_JSON",
    "JARVIS_CI_RUN_ID",
    "JARVIS_CI_RUN_NUMBER",
    "JARVIS_CI_RUN_URL",
    "JARVIS_CI_BRANCH",
    "JARVIS_CI_METADATA_GENERATED_AT",
    "JARVIS_CI_BACKEND_STATUS",
    "JARVIS_CI_IOS_STATUS",
    "JARVIS_CI_MAC_STATUS",
}
STATUS_KEYS = {
    "JARVIS_CI_STATUS",
    "JARVIS_TESTS_STATUS",
    "JARVIS_CI_BACKEND_STATUS",
    "JARVIS_CI_IOS_STATUS",
    "JARVIS_CI_MAC_STATUS",
}
VALID_STATUSES = {"success", "failure", "unknown"}
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
_DIGITS_RE = re.compile(r"^[0-9]+$")
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


def _valid_value(key, value):
    if key in STATUS_KEYS:
        return value.lower() in VALID_STATUSES
    if key == "JARVIS_BUILD_SHA":
        return not value or bool(_SHA_RE.fullmatch(value))
    if key in {"JARVIS_CI_RUN_ID", "JARVIS_CI_RUN_NUMBER"}:
        return not value or bool(_DIGITS_RE.fullmatch(value))
    if key == "JARVIS_CI_RUN_URL":
        if not value:
            return True
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    if key == "JARVIS_CI_METADATA_GENERATED_AT":
        return not value or ("T" in value and value.endswith("Z"))
    if key == "JARVIS_CI_BRANCH":
        return "\n" not in value and "\r" not in value and len(value) <= 200
    if key == "JARVIS_OWNER_ACTIONS_JSON":
        return _valid_owner_actions_json(value)
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

    if not staged:
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
