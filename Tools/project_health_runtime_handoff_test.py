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
    "JARVIS_CI_RUN_ID",
    "JARVIS_CI_RUN_NUMBER",
    "JARVIS_CI_RUN_URL",
    "JARVIS_CI_BRANCH",
    "JARVIS_CI_REPOSITORY",
    "JARVIS_CI_METADATA_GENERATED_AT",
    "JARVIS_CI_BACKEND_STATUS",
    "JARVIS_CI_IOS_STATUS",
    "JARVIS_CI_MAC_STATUS",
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
check(
    "runtime loader validates canonical GitHub CI identity fields",
    "JARVIS_CI_RUN_ID" in loader_source
    and "JARVIS_CI_RUN_URL" in loader_source
    and "_github_run_id_from_url" in loader_source
    and "_GITHUB_RUN_PATH_RE" in loader_source
    and "JARVIS_CI_REPOSITORY" in loader_source
    and "parsed.netloc != \"github.com\"" in loader_source,
)
check(
    "runtime loader cross-checks run URL against effective run id",
    "_drop_inconsistent_run_identity(staged, env)" in loader_source,
)
check(
    "runtime loader fail-closes on deployed build or branch identity conflicts",
    "_matches_explicit_build_identity(staged, env)" in loader_source
    and 'for key in ("JARVIS_BUILD_SHA", "JARVIS_CI_BRANCH", "JARVIS_CI_REPOSITORY")' in loader_source,
)

with tempfile.TemporaryDirectory() as td:
    handoff = Path(td) / "project-health.env"
    handoff.write_text(
        "JARVIS_BUILD_SHA=ab57842584e1606142fb72a9fcfee745617c3d28\n"
        "JARVIS_CI_STATUS=success\n"
        "JARVIS_TESTS_STATUS=success\n"
        "JARVIS_CURRENT_PHASE=4\n"
        "JARVIS_CURRENT_MILESTONE=Project Health Monitor\n"
        "JARVIS_NEXT_MILESTONE=Siri / App Intents foundation\n"
        "JARVIS_CI_RUN_ID=35603375966\n"
        "JARVIS_CI_RUN_NUMBER=277\n"
        "JARVIS_CI_RUN_URL=https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35603375966\n"
        "JARVIS_CI_BRANCH=chatgpt-overnight-2\n"
        "JARVIS_CI_REPOSITORY=salemaladbi1981-lab/jarvis-ios\n"
        "JARVIS_CI_METADATA_GENERATED_AT=2026-09-21T13:10:00Z\n"
        "JARVIS_CI_BACKEND_STATUS=success\n"
        "JARVIS_CI_IOS_STATUS=success\n"
        "JARVIS_CI_MAC_STATUS=success\n"
        "OPENAI_API_KEY=must-not-be-injected\n",
        encoding="utf-8",
    )

    clean = os.environ.copy()
    for key in HEALTH_KEYS + ("OPENAI_API_KEY",):
        clean.pop(key, None)
    clean["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = str(handoff)
    values, secret = probe(clean)
    parts = values.split("|")
    check(
        "generated handoff can populate build CI tests milestones and run identity",
        parts[:6] == [
            "ab57842584e1606142fb72a9fcfee745617c3d28", "success", "success", "4",
            "Project Health Monitor", "Siri / App Intents foundation",
        ]
        and parts[6:10] == [
            "35603375966", "277",
            "https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35603375966",
            "chatgpt-overnight-2",
        ]
        and parts[10] == "salemaladbi1981-lab/jarvis-ios"
        and parts[11:] == ["2026-09-21T13:10:00Z", "success", "success", "success"],
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

    wrong_build = clean.copy()
    wrong_build["JARVIS_BUILD_SHA"] = "ffffffffffffffffffffffffffffffffffffffff"
    wrong_build_values, _ = probe(wrong_build)
    wrong_build_parts = wrong_build_values.split("|")
    check(
        "artifact is rejected as a unit when deployed build SHA disagrees",
        wrong_build_parts[0] == "ffffffffffffffffffffffffffffffffffffffff"
        and wrong_build_parts[1] == ""
        and wrong_build_parts[2] == ""
        and wrong_build_parts[6] == ""
        and wrong_build_parts[8] == ""
        and wrong_build_parts[9] == "",
    )

    wrong_branch = clean.copy()
    wrong_branch["JARVIS_CI_BRANCH"] = "main"
    wrong_branch_values, _ = probe(wrong_branch)
    wrong_branch_parts = wrong_branch_values.split("|")
    check(
        "artifact is rejected as a unit when deployed branch disagrees",
        wrong_branch_parts[0] == ""
        and wrong_branch_parts[1] == ""
        and wrong_branch_parts[2] == ""
        and wrong_branch_parts[6] == ""
        and wrong_branch_parts[8] == ""
        and wrong_branch_parts[9] == "main",
    )

    bad = Path(td) / "bad.env"
    bad.write_text(
        "JARVIS_BUILD_SHA=not-a-sha\n"
        "JARVIS_CI_STATUS=definitely-green\n"
        "JARVIS_TESTS_STATUS=success\n"
        "JARVIS_CI_RUN_ID=not-numeric\n"
        "JARVIS_CI_RUN_URL=http://not-https.example/run\n"
        "JARVIS_CI_BACKEND_STATUS=maybe\n",
        encoding="utf-8",
    )
    invalid = os.environ.copy()
    for key in HEALTH_KEYS:
        invalid.pop(key, None)
    invalid["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = str(bad)
    invalid_values, _ = probe(invalid)
    invalid_parts = invalid_values.split("|")
    check("invalid SHA is rejected instead of reported", invalid_parts[0] == "")
    check("invalid CI status is rejected instead of reported", invalid_parts[1] == "")
    check("valid fields from a partially malformed handoff remain usable", invalid_parts[2] == "success")
    check("invalid CI run identity is rejected", invalid_parts[6] == "" and invalid_parts[8] == "")
    check("invalid per-job status is rejected", invalid_parts[12] == "")

    foreign = Path(td) / "foreign-run-url.env"
    foreign.write_text(
        "JARVIS_CI_RUN_ID=35603375966\n"
        "JARVIS_CI_RUN_URL=https://example.com/salemaladbi1981-lab/jarvis-ios/actions/runs/35603375966\n",
        encoding="utf-8",
    )
    foreign_env = os.environ.copy()
    for key in HEALTH_KEYS:
        foreign_env.pop(key, None)
    foreign_env["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = str(foreign)
    foreign_values, _ = probe(foreign_env)
    foreign_parts = foreign_values.split("|")
    check(
        "foreign HTTPS hosts cannot become clickable CI run URLs",
        foreign_parts[6] == "35603375966" and foreign_parts[8] == "",
    )

    mismatch = Path(td) / "mismatched-run.env"
    mismatch.write_text(
        "JARVIS_CI_RUN_ID=35603375966\n"
        "JARVIS_CI_RUN_URL=https://github.com/salemaladbi1981-lab/jarvis-ios/actions/runs/99999999999\n",
        encoding="utf-8",
    )
    mismatch_env = os.environ.copy()
    for key in HEALTH_KEYS:
        mismatch_env.pop(key, None)
    mismatch_env["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = str(mismatch)
    mismatch_values, _ = probe(mismatch_env)
    mismatch_parts = mismatch_values.split("|")
    check(
        "mismatched GitHub run URL is removed instead of being surfaced",
        mismatch_parts[6] == "35603375966" and mismatch_parts[8] == "",
    )

missing = os.environ.copy()
for key in HEALTH_KEYS:
    missing.pop(key, None)
missing["JARVIS_PROJECT_HEALTH_METADATA_PATH"] = "/path/that/does/not/exist"
missing_values, _ = probe(missing)
missing_parts = missing_values.split("|")
check(
    "missing handoff fails closed without startup failure",
    missing_parts[:3] == ["", "", ""] and missing_parts[3:6] == ["unknown", "unknown", "unknown"],
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
