#!/usr/bin/env python3
"""Read-only verifier for a deployed Project Health endpoint.

This tool is intentionally separate from deployment/cutover. It performs one
HTTPS GET, optionally using an existing bearer token supplied via an
environment variable, and validates that the live runtime is serving fresh CI,
build, test, milestone, and blocker evidence for the exact expected build.
It never writes production state and never prints authentication material.
"""
import argparse
import json
import os
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_MAX_RESPONSE_BYTES = 1_048_576
_REQUIRED_REPORTED_EVIDENCE = ("build", "ci", "tests", "ci_run", "milestones")


def _nonempty(value):
    return bool(str(value or "").strip()) and str(value).strip().lower() != "unknown"


def validate_url(url):
    """Accept only a canonical HTTPS endpoint URL with no embedded credentials."""
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Project Health live verification requires an https URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Project Health URL must not contain credentials, query, or fragment")
    return parsed.geturl()


def fetch_snapshot(url, bearer_token="", timeout=10.0):
    """Fetch one bounded JSON object without exposing the bearer token."""
    url = validate_url(url)
    headers = {"Accept": "application/json"}
    token = str(bearer_token or "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=float(timeout)) as response:
        raw = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise ValueError("Project Health response exceeds safe size limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Project Health response is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Project Health response must be a JSON object")
    return payload


def assess_snapshot(snapshot, expected_sha, expected_branch):
    """Return a sanitized, fail-closed verdict for one live health snapshot."""
    if not isinstance(snapshot, dict):
        return {"ok": False, "failed_checks": ["response_object"]}

    expected_sha = str(expected_sha or "").strip()
    expected_branch = str(expected_branch or "").strip()
    evidence = snapshot.get("evidence") if isinstance(snapshot.get("evidence"), dict) else {}
    blocker_items = snapshot.get("blocker_items") if isinstance(snapshot.get("blocker_items"), list) else []
    owner_items = snapshot.get("owner_action_items") if isinstance(snapshot.get("owner_action_items"), list) else []

    try:
        blockers = int(snapshot.get("blockers") or 0)
    except (TypeError, ValueError):
        blockers = -1
    try:
        owner_actions = int(snapshot.get("owner_actions") or 0)
    except (TypeError, ValueError):
        owner_actions = -1

    checks = {
        "expected_identity": bool(expected_sha and expected_branch),
        "build_identity": snapshot.get("build_sha") == expected_sha,
        "branch_identity": snapshot.get("ci_branch") == expected_branch,
        "ci": snapshot.get("ci_status") == "success",
        "build": snapshot.get("build_status") == "success",
        "tests": snapshot.get("tests_status") == "success",
        "freshness": snapshot.get("ci_metadata_state") == "fresh",
        "blockers": blockers == 0 and not blocker_items,
        "milestones": all(_nonempty(snapshot.get(key)) for key in ("phase", "current_milestone", "next_milestone")),
        "reported_evidence": all(evidence.get(key) == "reported" for key in _REQUIRED_REPORTED_EVIDENCE),
        "freshness_evidence": evidence.get("ci_freshness") == "fresh",
        "owner_action_coherence": owner_actions >= 0 and owner_actions == len(owner_items),
    }
    failed = [name for name, passed in checks.items() if not passed]

    return {
        "ok": not failed,
        "failed_checks": failed,
        "build_sha": str(snapshot.get("build_sha") or ""),
        "ci_branch": str(snapshot.get("ci_branch") or ""),
        "ci_run_id": str(snapshot.get("ci_run_id") or ""),
        "ci_run_number": str(snapshot.get("ci_run_number") or ""),
        "ci_status": str(snapshot.get("ci_status") or "unknown"),
        "build_status": str(snapshot.get("build_status") or "unknown"),
        "tests_status": str(snapshot.get("tests_status") or "unknown"),
        "ci_metadata_state": str(snapshot.get("ci_metadata_state") or "unknown"),
        "blockers": blockers,
        "owner_actions": owner_actions,
        "phase": str(snapshot.get("phase") or "unknown"),
        "current_milestone": str(snapshot.get("current_milestone") or "unknown"),
        "next_milestone": str(snapshot.get("next_milestone") or "unknown"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--token-env", default="JARVIS_SESSION_TOKEN")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    try:
        token = os.environ.get(args.token_env, "") if args.token_env else ""
        snapshot = fetch_snapshot(args.url, bearer_token=token, timeout=args.timeout)
        result = assess_snapshot(snapshot, args.expected_sha, args.expected_branch)
    except Exception as exc:  # CLI boundary: return only a sanitized error class/message.
        result = {"ok": False, "failed_checks": ["live_fetch"], "error": str(exc)}

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
