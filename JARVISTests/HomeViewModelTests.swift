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
}
