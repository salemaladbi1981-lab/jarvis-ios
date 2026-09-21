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
    "Mac Operator has explicit permission + request-bound owner-approval policy",
    "struct MacOperatorAuthorizationPolicy" in SOURCE
    and "grantedPermissions.contains(permission)" in SOURCE
    and "struct MacOperatorApprovalGrant" in SOURCE
    and "ownerApproval.authorizes(request, now: now)" in SOURCE,
)

check(
    "official macOS permission classes are represented",
    "case userSelectedFiles" in SOURCE
    and "case accessibility" in SOURCE
    and "case automation" in SOURCE,
)

check(
    "target shape validation runs before permission and owner-approval prompts",
    "struct MacOperatorTargetPolicy" in SOURCE
    and "case invalidTarget" in SOURCE
    and SOURCE.find("targetPolicy.isValid(request)")
    < SOURCE.find("grantedPermissions.contains(permission)")
    < SOURCE.find("request.action.requiresOwnerApproval"),
)

check(
    "file and app targets are constrained before authorization",
    "target.utf8.count <= maxTargetUTF8Bytes" in SOURCE
    and "target.rangeOfCharacter(from: .controlCharacters) == nil" in SOURCE
    and 'target.hasPrefix("/")' in SOURCE
    and 'target != "/"' in SOURCE
    and 'components.contains(where: { $0 == ".." })' in SOURCE
    and "isBundleIdentifier(target)" in SOURCE,
)

check(
    "permission gate executes before owner approval gate",
    SOURCE.find("grantedPermissions.contains(permission)")
    < SOURCE.find("request.action.requiresOwnerApproval"),
)

check(
    "owner approval is exact-request-bound and expiring",
    "self.request == request && now < expiresAt" in SOURCE,
)

check(
    "approval grant carries a unique replay identity",
    "let id: UUID" in SOURCE
    and "init(id: UUID = UUID(), request: MacOperatorRequest, expiresAt: Date)" in SOURCE,
)

check(
    "approval-required execution is actor-serialized and one-shot",
    "actor MacOperatorExecutionGate" in SOURCE
    and "consumedApprovalIDs: Set<UUID>" in SOURCE
    and "guard !consumedApprovalIDs.contains(ownerApproval.id)" in SOURCE
    and "consumedApprovalIDs.insert(ownerApproval.id)" in SOURCE,
)

check(
    "executor seam requires an authorization token rather than a raw request",
    "struct MacOperatorExecutionAuthorization" in SOURCE
    and "fileprivate init(request: MacOperatorRequest, approvalGrantID: UUID?)" in SOURCE
    and "func execute(_ authorization: MacOperatorExecutionAuthorization)" in SOURCE,
)

check(
    "single service seam gates before invoking executor",
    "actor MacOperatorService" in SOURCE
    and "let gateResult = await gate.authorize(" in SOURCE
    and "return .execution(await executor.execute(authorization))" in SOURCE
    and SOURCE.find("let gateResult = await gate.authorize(")
    < SOURCE.find("return .execution(await executor.execute(authorization))"),
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
