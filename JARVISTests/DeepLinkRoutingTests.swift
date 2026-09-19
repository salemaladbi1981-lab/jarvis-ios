import XCTest

/// اختبار توجيه الإشعار/deep-link: parse + url round-trip + حالات الرفض.
final class DeepLinkRoutingTests: XCTestCase {

    func testParseConversation() {
        XCTAssertEqual(DeepLinkTarget.parse(URL(string: "jarvis://conversation/conv-123")!),
                       .conversation("conv-123"))
    }

    func testParseTask() {
        XCTAssertEqual(DeepLinkTarget.parse(URL(string: "jarvis://task/task-456")!),
                       .task("task-456"))
    }

    func testParseDelivery() {
        XCTAssertEqual(DeepLinkTarget.parse(URL(string: "jarvis://delivery/dlv-789")!),
                       .delivery("dlv-789"))
    }

    func testParseRejectsWrongScheme() {
        XCTAssertNil(DeepLinkTarget.parse(URL(string: "https://conversation/x")!))
    }

    func testParseRejectsUnknownHost() {
        XCTAssertNil(DeepLinkTarget.parse(URL(string: "jarvis://nope/x")!))
    }

    func testParseRejectsEmptyId() {
        XCTAssertNil(DeepLinkTarget.parse(URL(string: "jarvis://task/")!))
    }

    /// round-trip: target → url → parse → نفس الـ target (هوية الإشعار لا تتغير).
    func testUrlRoundTrip() {
        let cases: [DeepLinkTarget] = [
            .conversation("conv-abc"), .task("task-def"), .delivery("dlv-ghi")
        ]
        for target in cases {
            let parsed = DeepLinkTarget.parse(URL(string: target.url)!)
            XCTAssertEqual(parsed, target, "round-trip failed for \(target.url)")
        }
    }

    /// محاكاة userInfo إشعار: السلسلة المخزّنة تُفتح نفس العنصر.
    func testNotificationUserInfoRoundTrip() {
        // نفس ما يخزّنه NotificationManager في userInfo["jarvis_deep_link"]
        let stored = DeepLinkTarget.delivery("dlv-42").url
        let parsed = DeepLinkTarget.parse(URL(string: stored)!)
        XCTAssertEqual(parsed, .delivery("dlv-42"))
    }
}
