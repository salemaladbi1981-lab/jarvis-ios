import XCTest
@testable import JARVIS

final class HomeViewModelTests: XCTestCase {
    @MainActor
    func testViewModelInitializesWithMockProviders() {
        let vm = HomeViewModel()
        XCTAssertEqual(vm.state, .idle)
        XCTAssertEqual(vm.activeGroup, "core")
    }
}
