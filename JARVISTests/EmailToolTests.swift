import XCTest
// EmailTool + ToolFoundation compiled directly into this target (no @testable import).

final class EmailToolTests: XCTestCase {

    private let tool = EmailTool(client: EmailClient(baseURL: "http://localhost"))

    func testIntentSummary() {
        XCTAssertEqual(tool.detectIntent(from: "وش أهم إيميلاتي اليوم؟"), .emailSummary)
        XCTAssertEqual(tool.detectIntent(from: "لخص لي الإيميلات الجديدة"), .emailSummary)
    }

    func testIntentRead() {
        XCTAssertEqual(tool.detectIntent(from: "اقرأ الرسالة"), .emailRead)
        XCTAssertEqual(tool.detectIntent(from: "افتح البريد"), .emailRead)
    }

    func testIntentSearch() {
        XCTAssertEqual(tool.detectIntent(from: "ابحث في البريد عن فلان"), .emailSearch(query: "ابحث في البريد عن فلان"))
    }

    func testIntentReply() {
        XCTAssertEqual(tool.detectIntent(from: "رد عليه بـ تمام حجزت"), .emailReply(body: "تمام حجزت"))
    }

    func testIntentNone() {
        XCTAssertEqual(tool.detectIntent(from: "وش عندي اليوم؟"), .none)
        XCTAssertEqual(tool.detectIntent(from: "شغّل شي هادي"), .none)
    }

    func testReplyRequiresConfirmation() {
        switch tool.confirmation(for: .emailReply(body: "نص")) {
        case .confirm: break
        default: XCTFail("إرسال البريد يجب أن يتطلب تأكيداً")
        }
    }

    func testReadDoesNotRequireConfirmation() {
        XCTAssertEqual(tool.confirmation(for: .emailSummary), .none)
        XCTAssertEqual(tool.confirmation(for: .emailRead), .none)
        XCTAssertEqual(tool.confirmation(for: .emailSearch(query: "x")), .none)
    }
}
