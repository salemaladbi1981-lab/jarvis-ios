import XCTest
@testable import JarvisProviders

final class ProviderIntegrityTests: XCTestCase {
    func testUnavailableProvidersReturnNoInventedState() async {
        let devices = await UnavailableSmartHomeProvider().readDevices()
        let security = await UnavailableSecurityProvider().status()
        let media = await UnavailableMediaProvider().nowPlaying()
        XCTAssertTrue(devices.isEmpty)
        XCTAssertNil(security)
        XCTAssertNil(media)
    }

    func testUnavailableActionsCannotReportSuccess() async {
        do { _ = try await UnavailableSmartHomeProvider().control(device: "door", action: "unlock"); XCTFail("Must fail closed") }
        catch { XCTAssertTrue(error is ProviderUnavailable) }
        do { _ = try await UnavailableSecurityProvider().execute(action: "disable"); XCTFail("Must fail closed") }
        catch { XCTAssertTrue(error is ProviderUnavailable) }
        do { _ = try await UnavailableMediaProvider().send(command: "play"); XCTFail("Must fail closed") }
        catch { XCTAssertTrue(error is ProviderUnavailable) }
    }
}
