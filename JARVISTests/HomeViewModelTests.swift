import XCTest
@testable import JARVIS

final class HomeViewModelTests: XCTestCase {
    @MainActor
    func testViewModelInitializesInIdleState() {
        let vm = HomeViewModel()
        XCTAssertEqual(vm.state, .idle)
        XCTAssertEqual(vm.activeGroup, "core")
    }

    @MainActor
    func testDefaultProvidersDoNotFabricateProductionData() async {
        XCTAssertFalse(ProcessInfo.processInfo.arguments.contains("-demo"))

        let vm = HomeViewModel()
        await vm.load()

        XCTAssertTrue(vm.homeDevices.isEmpty, "production launch must not expose synthetic smart-home devices")
        XCTAssertEqual(vm.securityStatus?.systemsNormal, false, "production launch must not fabricate an all-normal security state")
        XCTAssertEqual(vm.mediaTrack?.title, "", "production launch must not expose a synthetic now-playing track")
    }

    func testMeetingMetadataDoesNotRequestCaptureAuthorization() {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: .metadataOnly,
            ownerAuthorized: false,
            participantConsentConfirmed: false
        )
        XCTAssertTrue(decision.allowed)
        XCTAssertNil(decision.blockReason)
        XCTAssertFalse(decision.requiresVisibleCaptureIndicator)
    }

    func testImportedTranscriptDoesNotBecomeLiveCapture() {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: .importedTranscript,
            ownerAuthorized: false,
            participantConsentConfirmed: false
        )
        XCTAssertTrue(decision.allowed)
        XCTAssertFalse(decision.requiresVisibleCaptureIndicator)
    }

    func testLiveMeetingCaptureRequiresOwnerAuthorizationFirst() {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: .authorizedLiveCapture,
            ownerAuthorized: false,
            participantConsentConfirmed: true
        )
        XCTAssertFalse(decision.allowed)
        XCTAssertEqual(decision.blockReason, .ownerAuthorizationRequired)
        XCTAssertTrue(decision.requiresVisibleCaptureIndicator)
    }

    func testLiveMeetingCaptureRequiresParticipantConsent() {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: .authorizedLiveCapture,
            ownerAuthorized: true,
            participantConsentConfirmed: false
        )
        XCTAssertFalse(decision.allowed)
        XCTAssertEqual(decision.blockReason, .participantConsentRequired)
        XCTAssertTrue(decision.requiresVisibleCaptureIndicator)
    }

    func testLiveMeetingCaptureAllowedOnlyWithBothGates() {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: .authorizedLiveCapture,
            ownerAuthorized: true,
            participantConsentConfirmed: true
        )
        XCTAssertTrue(decision.allowed)
        XCTAssertNil(decision.blockReason)
        XCTAssertTrue(decision.requiresVisibleCaptureIndicator)
    }

    func testSilentObserverDoesNotEncodeStealthCapture() {
        let session = MeetingSessionDescriptor(
            title: "Planning",
            inputMode: .authorizedLiveCapture,
            presence: .silentObserver
        )
        XCTAssertEqual(session.presence, .silentObserver)
        XCTAssertEqual(session.state, .idle)

        let blocked = MeetingCapturePolicy.evaluate(
            inputMode: session.inputMode,
            ownerAuthorized: true,
            participantConsentConfirmed: false
        )
        XCTAssertFalse(blocked.allowed, "silent observer mode must never bypass participant consent")
        XCTAssertTrue(blocked.requiresVisibleCaptureIndicator, "silent assistant behavior must not imply invisible capture")
    }

    func testMeetingPreparationKeepsUnauthorizedLiveCaptureWaiting() {
        let state = MeetingSessionLifecycle.preparedState(
            inputMode: .authorizedLiveCapture,
            ownerAuthorized: true,
            participantConsentConfirmed: false
        )
        XCTAssertEqual(state, .awaitingAuthorization)
    }

    func testMeetingPreparationBecomesReadyOnlyAfterBothLiveCaptureGates() {
        let state = MeetingSessionLifecycle.preparedState(
            inputMode: .authorizedLiveCapture,
            ownerAuthorized: true,
            participantConsentConfirmed: true
        )
        XCTAssertEqual(state, .ready)
    }

    func testMeetingMetadataPreparationIsReadyWithoutCapturePermissions() {
        let state = MeetingSessionLifecycle.preparedState(
            inputMode: .metadataOnly,
            ownerAuthorized: false,
            participantConsentConfirmed: false
        )
        XCTAssertEqual(state, .ready)
    }

    func testMeetingLifecycleCannotJumpFromIdleOrAuthorizationWaitToActive() {
        XCTAssertFalse(MeetingSessionLifecycle.canTransition(from: .idle, to: .active))
        XCTAssertFalse(MeetingSessionLifecycle.canTransition(from: .awaitingAuthorization, to: .active))
    }

    func testMeetingLifecycleAllowsReadyActiveStoppedFlowAndIdempotence() {
        XCTAssertTrue(MeetingSessionLifecycle.canTransition(from: .ready, to: .active))
        XCTAssertTrue(MeetingSessionLifecycle.canTransition(from: .active, to: .stopped))
        XCTAssertTrue(MeetingSessionLifecycle.canTransition(from: .stopped, to: .idle))
        XCTAssertTrue(MeetingSessionLifecycle.canTransition(from: .active, to: .active))
    }

    func testMeetingCoordinatorKeepsBlockedLiveSessionAwaitingAuthorization() throws {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Weekly review",
                inputMode: .authorizedLiveCapture
            )
        )

        let decision = try coordinator.prepare(
            ownerAuthorized: true,
            participantConsentConfirmed: false
        )

        XCTAssertFalse(decision.allowed)
        XCTAssertEqual(decision.blockReason, .participantConsentRequired)
        XCTAssertEqual(coordinator.descriptor.state, .awaitingAuthorization)
    }

    func testMeetingCoordinatorRechecksLiveConsentAtActivation() {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Injected ready state",
                inputMode: .authorizedLiveCapture,
                state: .ready
            )
        )

        XCTAssertThrowsError(
            try coordinator.activate(
                ownerAuthorized: true,
                participantConsentConfirmed: false
            )
        ) { error in
            XCTAssertEqual(
                error as? MeetingSessionTransitionError,
                .captureBlocked(.participantConsentRequired)
            )
        }
        XCTAssertEqual(coordinator.descriptor.state, .ready)
    }

    func testMeetingCoordinatorAllowsAuthorizedReadyActiveStopResetFlow() throws {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Authorized meeting",
                inputMode: .authorizedLiveCapture
            )
        )

        let decision = try coordinator.prepare(
            ownerAuthorized: true,
            participantConsentConfirmed: true
        )
        XCTAssertTrue(decision.allowed)
        XCTAssertEqual(coordinator.descriptor.state, .ready)

        try coordinator.activate(
            ownerAuthorized: true,
            participantConsentConfirmed: true
        )
        XCTAssertEqual(coordinator.descriptor.state, .active)

        try coordinator.stop()
        XCTAssertEqual(coordinator.descriptor.state, .stopped)

        try coordinator.reset()
        XCTAssertEqual(coordinator.descriptor.state, .idle)
    }

    func testMeetingCoordinatorRejectsDirectIdleActivationEvenForMetadata() {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Metadata only",
                inputMode: .metadataOnly
            )
        )

        XCTAssertThrowsError(
            try coordinator.activate(
                ownerAuthorized: false,
                participantConsentConfirmed: false
            )
        ) { error in
            XCTAssertEqual(
                error as? MeetingSessionTransitionError,
                .invalidTransition(from: .idle, to: .active)
            )
        }
        XCTAssertEqual(coordinator.descriptor.state, .idle)
    }

    func testMeetingCoordinatorStopsActiveLiveSessionWhenConsentIsRevoked() throws {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Live review",
                inputMode: .authorizedLiveCapture
            )
        )
        _ = try coordinator.prepare(ownerAuthorized: true, participantConsentConfirmed: true)
        try coordinator.activate(ownerAuthorized: true, participantConsentConfirmed: true)
        XCTAssertEqual(coordinator.descriptor.state, .active)

        let decision = try coordinator.reconcileAuthorization(
            ownerAuthorized: true,
            participantConsentConfirmed: false
        )

        XCTAssertFalse(decision.allowed)
        XCTAssertEqual(decision.blockReason, .participantConsentRequired)
        XCTAssertEqual(coordinator.descriptor.state, .stopped)
    }

    func testMeetingCoordinatorDowngradesReadyLiveSessionWhenOwnerAuthorizationIsRevoked() throws {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Ready review",
                inputMode: .authorizedLiveCapture
            )
        )
        _ = try coordinator.prepare(ownerAuthorized: true, participantConsentConfirmed: true)
        XCTAssertEqual(coordinator.descriptor.state, .ready)

        let decision = try coordinator.reconcileAuthorization(
            ownerAuthorized: false,
            participantConsentConfirmed: true
        )

        XCTAssertFalse(decision.allowed)
        XCTAssertEqual(decision.blockReason, .ownerAuthorizationRequired)
        XCTAssertEqual(coordinator.descriptor.state, .awaitingAuthorization)
    }

    func testMeetingCoordinatorRestoresWaitingLiveSessionToReadyWhenConsentReturns() throws {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Waiting review",
                inputMode: .authorizedLiveCapture
            )
        )
        _ = try coordinator.prepare(ownerAuthorized: true, participantConsentConfirmed: false)
        XCTAssertEqual(coordinator.descriptor.state, .awaitingAuthorization)

        let decision = try coordinator.reconcileAuthorization(
            ownerAuthorized: true,
            participantConsentConfirmed: true
        )

        XCTAssertTrue(decision.allowed)
        XCTAssertEqual(coordinator.descriptor.state, .ready)
    }

    func testMeetingCoordinatorLeavesNonCaptureSessionStateUntouchedDuringAuthorizationReconcile() throws {
        var coordinator = MeetingSessionCoordinator(
            descriptor: MeetingSessionDescriptor(
                title: "Imported notes",
                inputMode: .importedTranscript,
                state: .ready
            )
        )

        let decision = try coordinator.reconcileAuthorization(
            ownerAuthorized: false,
            participantConsentConfirmed: false
        )

        XCTAssertTrue(decision.allowed)
        XCTAssertEqual(coordinator.descriptor.state, .ready)
    }
}