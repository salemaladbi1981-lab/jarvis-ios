import XCTest
@testable import JarvisProviders

final class MeetingArtifactTests: XCTestCase {
    private let scope = MeetingScope(userID: "owner", workspaceID: "PERSONAL")
    private func record() -> MeetingRecord {
        MeetingRecord(scope: scope, session: .init(id: "meeting-1", title: "Review", inputMode: .importedTranscript),
            transcript: [.init(id: "segment-1", speaker: nil, startSeconds: 0, endSeconds: 3, text: "Send the report.")],
            summary: [.init(id: "summary-1", text: "Report requested", sourceSegmentIDs: ["segment-1"])],
            decisions: [], actionItems: [], artifacts: [])
    }
    func testArtifactsRoundTripAndKeepWorkspaceAndEvidence() throws {
        let original = record()
        let decoded = try JSONDecoder().decode(MeetingRecord.self, from: JSONEncoder().encode(original))
        XCTAssertEqual(decoded, original)
        XCTAssertNoThrow(try decoded.validate(for: scope))
    }
    func testCrossWorkspaceReadIsRejected() {
        XCTAssertThrowsError(try record().validate(for: .init(userID: "owner", workspaceID: "BUSINESS"))) {
            XCTAssertEqual($0 as? MeetingRecordError, .wrongScope)
        }
    }
    func testMissingEvidenceCannotBecomeSummaryOrAction() {
        var value = record()
        value.summary[0].sourceSegmentIDs = ["invented-segment"]
        XCTAssertThrowsError(try value.validate(for: scope)) { XCTAssertEqual($0 as? MeetingRecordError, .missingEvidence) }
        value.summary = []
        value.actionItems = [.init(id: "action-1", finding: .init(id: "finding-1", text: "Email", sourceSegmentIDs: []), assignee: nil, dueAt: nil, completed: false)]
        XCTAssertThrowsError(try value.validate(for: scope))
    }
    func testInvalidTimestampsAndDuplicateSegmentsFailValidation() {
        var value = record()
        value.transcript[0].endSeconds = -1
        XCTAssertThrowsError(try value.validate(for: scope)) { XCTAssertEqual($0 as? MeetingRecordError, .invalidTranscript) }
        value = record()
        value.transcript.append(value.transcript[0])
        XCTAssertThrowsError(try value.validate(for: scope)) { XCTAssertEqual($0 as? MeetingRecordError, .duplicateIdentity) }
    }
}
