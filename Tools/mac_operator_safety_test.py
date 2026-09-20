"""Static safety regression for the Mac Operator foundation.

The foundation may model permissions/approvals, but must not gain a concrete
privileged execution path until an explicitly authorized platform adapter is
implemented and reviewed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "JARVIS" / "App" / "DeepLinkTarget.swift").read_text(encoding="utf-8")

PASS = 0
FAIL = 0


def check(name: str, condition: bool) -> None:
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


check(
    "Mac Operator has explicit permission + owner-approval policy",
    "struct MacOperatorAuthorizationPolicy" in SOURCE
    and "grantedPermissions.contains(permission)" in SOURCE
    and "ownerApproved" in SOURCE,
)

check(
    "official macOS permission classes are represented",
    "case userSelectedFiles" in SOURCE
    and "case accessibility" in SOURCE
    and "case automation" in SOURCE,
)

check(
    "permission gate executes before owner approval gate",
    SOURCE.find("grantedPermissions.contains(permission)")
    < SOURCE.find("request.action.requiresOwnerApproval"),
)

check(
    "default executor is fail-closed",
    "struct DisabledMacOperatorExecutor" in SOURCE
    and '.blocked("mac_operator_executor_not_configured")' in SOURCE,
)

for forbidden in (
    "Process(",
    "NSAppleScript",
    "osascript",
    "AXUIElement",
    "NSWorkspace.shared",
    "AuthorizationExecuteWithPrivileges",
):
    check(f"foundation does not execute via {forbidden}", forbidden not in SOURCE)

check(
    "foundation exposes only typed actions, not arbitrary command text",
    "case runCommand" not in SOURCE
    and "case shellCommand" not in SOURCE
    and "command: String" not in SOURCE,
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
