"""Regression tests for safe CI -> runtime Project Health metadata handoff."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "phase3" / "backend"
PASS = FAIL = 0
HEALTH_KEYS = (
    "JARVIS_BUILD_SHA",
    "JARVIS_CI_STATUS",
    "JARVIS_TESTS_STATUS",
    "JARVIS_CURRENT_PHASE",
    "JARVIS_CURRENT_MILESTONE",
    "JARVIS_NEXT_MILESTONE",
)


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


def probe(env):
    code = (
        "import os,sys; "
        f"sys.path.insert(0, {str(BACKEND)!r}); "
        "import config; "
        "keys=" + repr(HEALTH_KEYS) + "; "
        "print('|'.join(os.environ.get(k,'') for k in keys)); "
        "print(os.environ.get('OPENAI_API_KEY',''))"
    )
    return subprocess.check_output([sys.executable, "-c", code], env=env, text=True).splitlines()


config_source = (BACKEND / "config.py").read_text(encoding="utf-8")
loader_source = (BACKEND / "project_health_metadata.py").read_text(encoding="utf-8")
check(
    "backend config consumes only an explicitly configured health metadata path",
    "load_configured_health_metadata()" in config_source
    and "JARVIS_PROJECT_HEALTH_METADATA_PATH" in loader_source,
)
check(
    "runtime loader allow-lists Project Health keys",
    "HEALTH_KEYS" in loader_source and "env.setdefault(key, value)" in loader_source,
)

with tempfile.TemporaryDirectory() as td:
    handoff = Path(td) / "project-health.env"
    handoff.write_text(
        "JARVIS_BUILD_SHA=ab57842584e1606142fb72a9fcfee745617c3d28\n"
        "JARVIS_CI_STATUS=success\n"
        "JARVIS_TESTS_STATUS=success\n"
        "JARVIS_CURRENT_PHASE=4\n"
        "JARVIS_CURRENT_MILESTONE=Siri / App Intents foundation\n"
        "JARVIS_NEXT_MILESTONE=Mac Operator foundation\n"
        "OPENAI_API_KEY=must-not-be-injected\n",
        encoding="utf-8",
    )

    clean = os.environ.copy()
    for key in HEALTH_KEYS + ("OPENAI_API_KEY",):
        clean.pop(key, None)
    clean["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = str(handoff)
    values, secret = probe(clean)
    check(
        "generated handoff can populate build CI tests and milestone metadata",
        values == (
            "ab57842584e1606142fb72a9fcfee745617c3d28|success|success|4|"
            "Siri / App Intents foundation|Mac Operator foundation"
        ),
    )
    check("metadata handoff cannot inject non-health secrets", secret != "must-not-be-injected")

    explicit = clean.copy()
    explicit["JARVIS_CI_STATUS"] = "failure"
    explicit["JARVIS_CURRENT_MILESTONE"] = "Deployment-owned milestone"
    explicit_values, _ = probe(explicit)
    check(
        "explicit deployment environment remains authoritative",
        "|failure|" in explicit_values
        and "|Deployment-owned milestone|" in explicit_values,
    )

    bad = Path(td) / "bad.env"
    bad.write_text(
        "JARVIS_BUILD_SHA=not-a-sha\n"
        "JARVIS_CI_STATUS=definitely-green\n"
        "JARVIS_TESTS_STATUS=success\n",
        encoding="utf-8",
    )
    invalid = os.environ.copy()
    for key in HEALTH_KEYS:
        invalid.pop(key, None)
    invalid["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = str(bad)
    invalid_values, _ = probe(invalid)
    parts = invalid_values.split("|")
    check("invalid SHA is rejected instead of reported", parts[0] == "")
    check("invalid CI status is rejected instead of reported", parts[1] == "")
    check("valid fields from a partially malformed handoff remain usable", parts[2] == "success")

missing = os.environ.copy()
for key in HEALTH_KEYS:
    missing.pop(key, None)
missing["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = "/path/that/does/not/exist"
missing_values, _ = probe(missing)
missing_parts = missing_values.split("|")
check(
    "missing handoff fails closed without startup failure",
    missing_parts[:3] == ["", "", ""] and missing_parts[3:] == ["unknown", "unknown", "unknown"],
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
