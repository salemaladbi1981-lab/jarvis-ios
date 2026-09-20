"""Regression guard for the authorization-only Meeting foundation.

This test intentionally checks that the shared model remains policy/state plumbing
and does not quietly grow recording, screen-capture, shell, or automation APIs.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODELS = (ROOT / "JARVIS/Workspace/WorkspaceModels.swift").read_text(encoding="utf-8")
TESTS = (ROOT / "JARVISTests/ApprovalPolicyEvaluatorTests.swift").read_text(encoding="utf-8")
PASS = FAIL = 0


def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


meeting = MODELS.split("// MARK: - Meeting foundation", 1)[-1]

check("meeting foundation exists", "struct MeetingSessionLifecycle" in meeting)
check("live mode is explicit", "case liveAuthorized" in meeting)
check("imported transcript is distinct", "case importedTranscript" in meeting)
check("owner authorization is required", "authorization.ownerAuthorized" in meeting)
check("participant consent is required", "authorization.participantConsent" in meeting)
check("visible capture indicator is required", "authorization.visibleCaptureIndicator" in meeting)
check("active session stops on revoked authorization", "case .active where !allowed" in meeting and "state = .stopped" in meeting)
check("authorization is rechecked before active", "guard MeetingAuthorizationPolicy.canPrepare" in meeting)

for forbidden in ("AVAudioSession", "AVAudioEngine", "AVCapture", "ScreenCaptureKit", "SCStream", "Process(", "NSAppleScript", "AXUIElement"):
    check(f"no unauthorized capture/control API: {forbidden}", forbidden not in meeting)

check("Swift regression tests cover live authorization", "testLiveMeetingRequiresOwnerParticipantAndVisibleIndicator" in TESTS)
check("Swift regression tests cover revocation", "testActiveLiveSessionStopsWhenConsentIsRevoked" in TESTS)
check("Swift regression tests cover imported transcript", "testImportedTranscriptDoesNotPretendToBeLiveCapture" in TESTS)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
