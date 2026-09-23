"""Regression: Project Health CI artifacts must prove explicit deployment identity."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "phase3" / "backend"
sys.path.insert(0, str(BACKEND))

import project_health_metadata

PASS = FAIL = 0
BUILD = "d68a1c5c88ba5f6bbbabd3e82b6c74e32aa38a25"
BRANCH = "chatgpt-overnight-2"


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def write_handoff(path, *, build=True, branch=True):
    lines = ["JARVIS_PROJECT_HEALTH_METADATA_SCHEMA=1"]
    if build:
        lines.append(f"JARVIS_BUILD_SHA={BUILD}")
    if branch:
        lines.append(f"JARVIS_CI_BRANCH={BRANCH}")
    lines.extend([
        "JARVIS_CI_STATUS=success",
        "JARVIS_TESTS_STATUS=success",
        "JARVIS_CI_RUN_ID=35745992096",
        "JARVIS_CI_RUN_URL=https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35745992096",
        "JARVIS_CI_METADATA_GENERATED_AT=2026-09-22T15:24:11Z",
        "JARVIS_CI_BACKEND_STATUS=success",
        "JARVIS_CI_IOS_STATUS=success",
        "JARVIS_CI_MAC_STATUS=success",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


with tempfile.TemporaryDirectory() as td:
    td = Path(td)

    complete = td / "complete.env"
    write_handoff(complete)
    complete_env = {"JARVIS_BUILD_SHA": BUILD, "JARVIS_CI_BRANCH": BRANCH}
    loaded = project_health_metadata.load_health_metadata(complete, complete_env)
    check("matching explicit build and branch identity loads the artifact", loaded)
    check("matching artifact can supply green CI evidence",
          complete_env.get("JARVIS_CI_STATUS") == "success"
          and complete_env.get("JARVIS_CI_RUN_ID") == "35745992096")

    missing_build = td / "missing-build.env"
    write_handoff(missing_build, build=False)
    build_env = {"JARVIS_BUILD_SHA": BUILD}
    loaded = project_health_metadata.load_health_metadata(missing_build, build_env)
    check("explicit deployment SHA rejects an artifact that omits build SHA", not loaded)
    check("rejected build-less artifact cannot inject green CI evidence",
          build_env == {"JARVIS_BUILD_SHA": BUILD})

    missing_branch = td / "missing-branch.env"
    write_handoff(missing_branch, branch=False)
    branch_env = {"JARVIS_CI_BRANCH": BRANCH}
    loaded = project_health_metadata.load_health_metadata(missing_branch, branch_env)
    check("explicit deployment branch rejects an artifact that omits branch", not loaded)
    check("rejected branch-less artifact cannot inject green CI evidence",
          branch_env == {"JARVIS_CI_BRANCH": BRANCH})

    malformed_build = td / "malformed-build.env"
    malformed_build.write_text(
        "JARVIS_PROJECT_HEALTH_METADATA_SCHEMA=1\n"
        "JARVIS_BUILD_SHA=not-a-sha\n"
        f"JARVIS_CI_BRANCH={BRANCH}\n"
        "JARVIS_CI_STATUS=success\n",
        encoding="utf-8",
    )
    malformed_env = {"JARVIS_BUILD_SHA": BUILD}
    loaded = project_health_metadata.load_health_metadata(malformed_build, malformed_env)
    check("filtered malformed build identity cannot degrade into a missing-identity bypass", not loaded)
    check("malformed identity rejection leaves explicit environment unchanged",
          malformed_env == {"JARVIS_BUILD_SHA": BUILD})

    legacy = td / "legacy-no-explicit-identity.env"
    write_handoff(legacy, build=False, branch=False)
    legacy_env = {}
    loaded = project_health_metadata.load_health_metadata(legacy, legacy_env)
    check("schema-compatible artifact loads when deployment declares no explicit identity", loaded)
    check("identity-optional artifact still requires normal field validation",
          legacy_env.get("JARVIS_CI_STATUS") == "success"
          and legacy_env.get("JARVIS_CI_RUN_URL", "").endswith("/35745992096"))

print(f"\nproject health metadata identity presence: {PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
