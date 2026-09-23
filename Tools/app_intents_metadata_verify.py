#!/usr/bin/env python3
"""Verify compiled AppIntents metadata emitted by Xcode for JARVIS.

The extractor schema differs across Xcode releases. This verifier checks the
stable security/runtime contract while accepting known legacy schema shape.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

MAX_METADATA_BYTES = 2 * 1024 * 1024
EXPECTED_ACTIONS = {"JarvisVoiceIntent", "JarvisOpenIntent", "JarvisNavigateIntent"}
EXPECTED_SHORTCUTS = {"JarvisVoiceIntent", "JarvisOpenIntent"}
REQUIRED_PHRASES = {
    "JarvisVoiceIntent": {"Start ${applicationName}", "شغل ${applicationName}"},
    "JarvisOpenIntent": {"Open ${applicationName}", "افتح ${applicationName}"},
}


def validate_payload(payload):
    errors = []
    if not isinstance(payload, dict):
        return ["metadata_root"]

    actions = payload.get("actions")
    if not isinstance(actions, dict):
        return ["actions"]

    for name in sorted(EXPECTED_ACTIONS):
        action = actions.get(name)
        if not isinstance(action, dict):
            errors.append(f"action:{name}")
            continue
        # Xcode 15.x emits authenticationPolicy but not isAuthPolExplicit;
        # newer extractors emit both. Policy 1 is requiresAuthentication.
        if action.get("authenticationPolicy") != 1:
            errors.append(f"auth_policy:{name}")
        if "isAuthPolExplicit" in action and action.get("isAuthPolExplicit") is not True:
            errors.append(f"auth_explicit:{name}")
        if action.get("isDiscoverable") is not True:
            errors.append(f"discoverable:{name}")
        if action.get("openAppWhenRun") is not True:
            errors.append(f"foreground_compat:{name}")

    shortcuts = payload.get("autoShortcuts")
    if not isinstance(shortcuts, list):
        errors.append("autoShortcuts")
        return errors

    by_action = {}
    for item in shortcuts:
        if isinstance(item, dict) and isinstance(item.get("actionIdentifier"), str):
            by_action[item["actionIdentifier"]] = item

    if set(by_action) != EXPECTED_SHORTCUTS:
        errors.append("shortcut_action_set")
    if "JarvisNavigateIntent" in by_action:
        errors.append("parameterized_navigation_shortcut")

    for action, required in REQUIRED_PHRASES.items():
        item = by_action.get(action) or {}
        phrases = {
            phrase.get("key")
            for phrase in item.get("phraseTemplates", [])
            if isinstance(phrase, dict) and isinstance(phrase.get("key"), str)
        }
        if not required <= phrases:
            errors.append(f"phrases:{action}")

    return errors


def load_app_metadata(app_path):
    path = Path(app_path) / "Metadata.appintents" / "extract.actionsdata"
    if not path.is_file():
        raise ValueError("compiled AppIntents metadata is missing")
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("compiled AppIntents metadata exceeds safe size limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("compiled AppIntents metadata is not valid UTF-8 JSON") from exc
    return payload


def payload_generator(payload):
    generator = payload.get("generator") if isinstance(payload, dict) else None
    if not isinstance(generator, dict):
        return "unknown extractor"
    name = generator.get("name")
    version = generator.get("version")
    if isinstance(name, str) and isinstance(version, str):
        return f"{name} {version}"
    return "unknown extractor"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: app_intents_metadata_verify.py /path/to/JARVIS.app", file=sys.stderr)
        return 2
    try:
        payload = load_app_metadata(argv[0])
        errors = validate_payload(payload)
    except ValueError as exc:
        print(f"App Intents metadata verification FAILED: {exc}")
        return 1
    if errors:
        print(f"App Intents metadata verification FAILED ({payload_generator(payload)}): " + ", ".join(errors))
        return 1
    print(f"App Intents metadata verification PASS: 3 authenticated intents, 2 parameterless shortcuts ({payload_generator(payload)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
