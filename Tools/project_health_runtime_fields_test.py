"""Project Health runtime field safety regression checks."""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BACKEND = os.path.join(ROOT, 'phase3', 'backend')
sys.path.insert(0, BACKEND)

import project_health

PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond:
        PASS += 1
    else:
        FAIL += 1


def snapshot(env):
    return project_health.build_project_health(
        tasks=[],
        job_state_for=lambda _task_id: None,
        pending_approvals=[],
        capability_count=1,
        kill_switch_engaged=False,
        provider="test",
        workspace_id="ws-runtime-fields",
        environ=env,
    )


valid = snapshot({
    "JARVIS_CURRENT_PHASE": " 2 ",
    "JARVIS_CURRENT_MILESTONE": "Siri lock-screen foundation",
    "JARVIS_NEXT_MILESTONE": "Mac Operator foundation",
    "JARVIS_BUILD_SHA": "a" * 40,
})
check("valid phase is preserved and trimmed", valid["phase"] == "2")
check("valid current milestone is preserved", valid["current_milestone"] == "Siri lock-screen foundation")
check("valid next milestone is preserved", valid["next_milestone"] == "Mac Operator foundation")
check("valid build SHA is preserved", valid["build_sha"] == "a" * 40)
check("valid planning evidence remains reported", valid["evidence"]["milestones"] == "reported")
check("valid build evidence remains reported", valid["evidence"]["build"] == "reported")

malformed = snapshot({
    "JARVIS_CURRENT_PHASE": "2\nJARVIS_CI_STATUS=success",
    "JARVIS_CURRENT_MILESTONE": "x" * 241,
    "JARVIS_NEXT_MILESTONE": "Meeting\rJARVIS_TESTS_STATUS=success",
    "JARVIS_BUILD_SHA": "b" * 65,
})
check("multiline phase fails closed", malformed["phase"] == "unknown")
check("oversized current milestone fails closed", malformed["current_milestone"] == "unknown")
check("carriage-return next milestone fails closed", malformed["next_milestone"] == "unknown")
check("oversized build identity fails closed", malformed["build_sha"] == "")
check("malformed planning evidence is unknown", malformed["evidence"]["milestones"] == "unknown")
check("malformed build evidence is unknown", malformed["evidence"]["build"] == "unknown")
serialized = json.dumps(malformed, allow_nan=False)
check("rejected runtime injection text is not reflected", "JARVIS_CI_STATUS=success" not in serialized and "JARVIS_TESTS_STATUS=success" not in serialized)

boundary = snapshot({
    "JARVIS_CURRENT_PHASE": "p" * 240,
    "JARVIS_CURRENT_MILESTONE": "m" * 240,
    "JARVIS_NEXT_MILESTONE": "n" * 240,
    "JARVIS_BUILD_SHA": "c" * 64,
})
check("documented runtime field boundary remains accepted", boundary["current_milestone"] == "m" * 240)
check("build identity boundary remains accepted", boundary["build_sha"] == "c" * 64)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
