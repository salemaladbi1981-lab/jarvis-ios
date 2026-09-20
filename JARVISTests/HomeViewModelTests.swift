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
}
