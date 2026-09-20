import XCTest
@testable import JARVIS

final class ApprovalPolicyEvaluatorTests: XCTestCase {
    private var evaluator: ApprovalPolicyEvaluator!

    override func setUpWithError() throws {
        let registry = try AgentRegistry.load()
        evaluator = ApprovalPolicyEvaluator(registry: registry)
    }

    func testHomeUnlockDoorRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "core_home", action: "unlock-door"))
    }
    func testHomeReadTemperatureNoApproval() {
        XCTAssertFalse(evaluator.requiresApproval(agentID: "core_home", action: "read-temperature"))
    }
    func testGuardianDisableCameraRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "core_guardian", action: "disable-camera"))
    }
    func testDealmakerFinancialCommitmentRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "core_dealmaker", action: "financial-commitment"))
    }
    func testServerDestructiveConfigRequiresApproval() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "sys_server", action: "destructive-config"))
    }
    func testUnknownAgentFailsSafe() {
        XCTAssertTrue(evaluator.requiresApproval(agentID: "unknown", action: "anything"))
    }
}

final class MeetingAuthorizationPolicyTests: XCTestCase {
    private let allowed = MeetingAuthorization(
        ownerAuthorized: true,
        participantConsent: true,
        visibleCaptureIndicator: true
    )

    func testLiveMeetingRequiresOwnerParticipantAndVisibleIndicator() {
        XCTAssertTrue(MeetingAuthorizationPolicy.canPrepare(mode: .liveAuthorized, authorization: allowed))
        XCTAssertFalse(MeetingAuthorizationPolicy.canPrepare(
            mode: .liveAuthorized,
            authorization: MeetingAuthorization(ownerAuthorized: false, participantConsent: true, visibleCaptureIndicator: true)
        ))
        XCTAssertFalse(MeetingAuthorizationPolicy.canPrepare(
            mode: .liveAuthorized,
            authorization: MeetingAuthorization(ownerAuthorized: true, participantConsent: false, visibleCaptureIndicator: true)
        ))
        XCTAssertFalse(MeetingAuthorizationPolicy.canPrepare(
            mode: .liveAuthorized,
            authorization: MeetingAuthorization(ownerAuthorized: true, participantConsent: true, visibleCaptureIndicator: false)
        ))
    }

    func testImportedTranscriptDoesNotPretendToBeLiveCapture() {
        var lifecycle = MeetingSessionLifecycle()
        lifecycle.prepare(mode: .importedTranscript)

        XCTAssertEqual(lifecycle.state, .ready)
        XCTAssertFalse(lifecycle.requiresVisibleCaptureIndicator)
        XCTAssertTrue(lifecycle.start())
        XCTAssertEqual(lifecycle.state, .active)
    }

    func testLiveLifecycleCannotStartWithoutAuthorization() {
        var lifecycle = MeetingSessionLifecycle()
        lifecycle.prepare(mode: .liveAuthorized, authorization: .none)

        XCTAssertEqual(lifecycle.state, .awaitingAuthorization)
        XCTAssertTrue(lifecycle.requiresVisibleCaptureIndicator)
        XCTAssertFalse(lifecycle.start())
        XCTAssertEqual(lifecycle.state, .awaitingAuthorization)
    }

    func testLiveLifecycleRechecksAuthorizationAtStart() {
        var lifecycle = MeetingSessionLifecycle()
        lifecycle.prepare(mode: .liveAuthorized, authorization: allowed)
        lifecycle.updateAuthorization(MeetingAuthorization(
            ownerAuthorized: true,
            participantConsent: false,
            visibleCaptureIndicator: true
        ))

        XCTAssertEqual(lifecycle.state, .awaitingAuthorization)
        XCTAssertFalse(lifecycle.start())
    }

    func testActiveLiveSessionStopsWhenConsentIsRevoked() {
        var lifecycle = MeetingSessionLifecycle()
        lifecycle.prepare(mode: .liveAuthorized, authorization: allowed)
        XCTAssertTrue(lifecycle.start())
        XCTAssertEqual(lifecycle.state, .active)

        lifecycle.updateAuthorization(MeetingAuthorization(
            ownerAuthorized: true,
            participantConsent: false,
            visibleCaptureIndicator: true
        ))
        XCTAssertEqual(lifecycle.state, .stopped)
    }

    func testWaitingSessionBecomesReadyWhenAuthorizationIsRestored() {
        var lifecycle = MeetingSessionLifecycle()
        lifecycle.prepare(mode: .liveAuthorized, authorization: .none)
        lifecycle.updateAuthorization(allowed)

        XCTAssertEqual(lifecycle.state, .ready)
        XCTAssertTrue(lifecycle.start())
        XCTAssertEqual(lifecycle.state, .active)
    }
}
