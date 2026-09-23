#!/usr/bin/env python3
"""Read-only verifier for a deployed Project Health endpoint.

This tool is intentionally separate from deployment/cutover. It performs one
HTTPS GET, optionally using an existing bearer token supplied via an
environment variable, and validates that the live runtime is serving fresh CI,
build, test, milestone, and blocker evidence for the exact expected build and
GitHub Actions run. It never writes production state and never prints
authentication material.
"""
import argparse
import json
import os
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_MAX_RESPONSE_BYTES = 1_048_576
_REQUIRED_REPORTED_EVIDENCE = ("build", "ci", "tests", "ci_run", "milestones")
EXPECTED_REPOSITORY = "salemaladbi1981-lab/jarvis-ios"


def _nonempty(value):
    return bool(str(value or "").strip()) and str(value).strip().lower() != "unknown"


def _canonical_run_url(repository, run_id):
    repository = str(repository or "").strip()
    run_id = str(run_id or "").strip()
    if not repository or not run_id:
        return ""
    return f"https://github.com/{repository}/actions/runs/{run_id}"


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


def assess_snapshot(
    snapshot,
    expected_sha,
    expected_branch,
    expected_repository=EXPECTED_REPOSITORY,
    expected_run_id="",
    expected_run_number="",
):
    """Return a sanitized, fail-closed verdict for one live health snapshot."""
    if not isinstance(snapshot, dict):
        return {"ok": False, "failed_checks": ["response_object"]}

    expected_sha = str(expected_sha or "").strip()
    expected_branch = str(expected_branch or "").strip()
    expected_repository = str(expected_repository or "").strip()
    expected_run_id = str(expected_run_id or "").strip()
    expected_run_number = str(expected_run_number or "").strip()
    expected_run_url = _canonical_run_url(expected_repository, expected_run_id)
    evidence = snapshot.get("evidence") if isinstance(snapshot.get("evidence"), dict) else {}
    blocker_items = snapshot.get("blocker_items") if isinstance(snapshot.get("blocker_items"), list) else []
    owner_items = snapshot.get("owner_action_items") if isinstance(snapshot.get("owner_action_items"), list) else []

    blocker_count = snapshot.get("blockers")
    owner_action_count = snapshot.get("owner_actions")
    blockers = blocker_count if type(blocker_count) is int else -1
    owner_actions = owner_action_count if type(owner_action_count) is int else -1
    blocker_coherent = (
        blockers >= 0
        and isinstance(snapshot.get("blocker_items"), list)
        and blockers == len(blocker_items)
    )
    owner_action_coherent = (
        owner_actions >= 0
        and isinstance(snapshot.get("owner_action_items"), list)
        and owner_actions == len(owner_items)
    )
    owner_action_source = evidence.get("owner_actions")

    checks = {
        "expected_identity": bool(
            expected_sha
            and expected_branch
            and expected_repository
            and expected_run_id.isdigit()
            and expected_run_number.isdigit()
        ),
        "build_identity": snapshot.get("build_sha") == expected_sha,
        "branch_identity": snapshot.get("ci_branch") == expected_branch,
        "repository_identity": snapshot.get("ci_repository") == expected_repository,
        "run_id_identity": str(snapshot.get("ci_run_id") or "") == expected_run_id,
        "run_number_identity": str(snapshot.get("ci_run_number") or "") == expected_run_number,
        "run_url_identity": str(snapshot.get("ci_run_url") or "") == expected_run_url,
        "ci": snapshot.get("ci_status") == "success",
        "build": snapshot.get("build_status") == "success",
        "tests": snapshot.get("tests_status") == "success",
        "freshness": snapshot.get("ci_metadata_state") == "fresh",
        "blocker_coherence": blocker_coherent,
        "blockers": blocker_coherent and blockers == 0,
        "milestones": all(_nonempty(snapshot.get(key)) for key in ("phase", "current_milestone", "next_milestone")),
        "reported_evidence": all(evidence.get(key) == "reported" for key in _REQUIRED_REPORTED_EVIDENCE),
        "freshness_evidence": evidence.get("ci_freshness") == "fresh",
        "milestone_provenance": evidence.get("milestone_source") in {
            "github_repository_variables", "version_controlled_plan", "mixed"
        },
        "owner_action_coherence": owner_action_coherent,
        "owner_action_provenance": owner_action_source in {
            "version_controlled_plan", "runtime_approvals", "mixed", "unknown"
        } and (owner_actions == 0 or owner_action_source != "unknown"),
    }
    failed = [name for name, passed in checks.items() if not passed]

    return {
        "ok": not failed,
        "failed_checks": failed,
        "build_sha": str(snapshot.get("build_sha") or ""),
        "ci_branch": str(snapshot.get("ci_branch") or ""),
        "ci_repository": str(snapshot.get("ci_repository") or ""),
        "ci_run_id": str(snapshot.get("ci_run_id") or ""),
        "ci_run_number": str(snapshot.get("ci_run_number") or ""),
        "ci_run_url": str(snapshot.get("ci_run_url") or ""),
        "ci_status": str(snapshot.get("ci_status") or "unknown"),
        "build_status": str(snapshot.get("build_status") or "unknown"),
        "tests_status": str(snapshot.get("tests_status") or "unknown"),
        "ci_metadata_state": str(snapshot.get("ci_metadata_state") or "unknown"),
        "blockers": blockers,
        "owner_actions": owner_actions,
        "phase": str(snapshot.get("phase") or "unknown"),
        "current_milestone": str(snapshot.get("current_milestone") or "unknown"),
        "next_milestone": str(snapshot.get("next_milestone") or "unknown"),
        "milestone_source": str(evidence.get("milestone_source") or "unknown"),
        "owner_actions_source": str(evidence.get("owner_actions") or "unknown"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-repository", default=EXPECTED_REPOSITORY)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-run-number", required=True)
    parser.add_argument("--token-env", default="JARVIS_SESSION_TOKEN")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    try:
        token = os.environ.get(args.token_env, "") if args.token_env else ""
        snapshot = fetch_snapshot(args.url, bearer_token=token, timeout=args.timeout)
        result = assess_snapshot(
            snapshot,
            args.expected_sha,
            args.expected_branch,
            args.expected_repository,
            args.expected_run_id,
            args.expected_run_number,
        )
    except Exception as exc:  # CLI boundary: return only a sanitized error class/message.
        result = {"ok": False, "failed_checks": ["live_fetch"], "error": str(exc)}

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
