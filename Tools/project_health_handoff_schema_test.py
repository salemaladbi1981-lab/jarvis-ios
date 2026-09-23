#!/usr/bin/env python3
"""Regression: Project Health CI -> runtime handoff is explicitly versioned."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
TOOLS = ROOT / "Tools"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TOOLS))

import project_health_ci_metadata
import project_health_metadata

PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    PASS += int(bool(condition))
    FAIL += int(not condition)


def generated_handoff(path):
    env = {
        "GITHUB_SHA": "a" * 40,
        "GITHUB_RUN_ID": "123456789",
        "GITHUB_RUN_NUMBER": "428",
        "GITHUB_REF_NAME": "chatgpt-overnight-2",
        "GITHUB_REPOSITORY": "salemaladbi1981-lab/jarvis-ios",
        "GITHUB_SERVER_URL": "https://github.com",
        "JARVIS_BACKEND_TEST_RESULT": "success",
        "JARVIS_IOS_RESULT": "success",
        "JARVIS_MAC_RESULT": "success",
        "JARVIS_IOS_BUILD_RESULT": "success",
        "JARVIS_MAC_BUILD_RESULT": "success",
        "JARVIS_MAC_TEST_RESULT": "success",
    }
    metadata = project_health_ci_metadata.build_metadata(env=env, generated_at="2026-09-23T14:15:00Z")
    project_health_ci_metadata._write_env(path, metadata)
    return path.read_text(encoding="utf-8")


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    valid = td / "project-health.env"
    text = generated_handoff(valid)
    check("producer emits handoff schema version", text.startswith("JARVIS_PROJECT_HEALTH_METADATA_SCHEMA=1\n"))
    loaded = {}
    check("runtime accepts current handoff schema", project_health_metadata.load_health_metadata(valid, loaded))
    check("runtime exposes loaded schema for diagnostics", loaded.get("JARVIS_PROJECT_HEALTH_METADATA_SCHEMA") == "1")

    missing = td / "missing-schema.env"
    missing.write_text("\n".join(text.splitlines()[1:]) + "\n", encoding="utf-8")
    missing_env = {}
    check("runtime rejects missing handoff schema as a unit", not project_health_metadata.load_health_metadata(missing, missing_env) and not missing_env)

    future = td / "future-schema.env"
    future.write_text(text.replace("JARVIS_PROJECT_HEALTH_METADATA_SCHEMA=1", "JARVIS_PROJECT_HEALTH_METADATA_SCHEMA=2", 1), encoding="utf-8")
    future_env = {}
    check("runtime rejects future handoff schema as a unit", not project_health_metadata.load_health_metadata(future, future_env) and not future_env)

    schema_only = td / "schema-only.env"
    schema_only.write_text("JARVIS_PROJECT_HEALTH_METADATA_SCHEMA=1\n", encoding="utf-8")
    schema_only_env = {}
    check("schema-only artifact cannot masquerade as a valid handoff", not project_health_metadata.load_health_metadata(schema_only, schema_only_env) and not schema_only_env)

    explicit = {"JARVIS_PROJECT_HEALTH_METADATA_SCHEMA": "1"}
    check("explicit process env cannot bless an incompatible artifact", not project_health_metadata.load_health_metadata(future, explicit) and explicit == {"JARVIS_PROJECT_HEALTH_METADATA_SCHEMA": "1"})

print(f"\nproject health handoff schema: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
