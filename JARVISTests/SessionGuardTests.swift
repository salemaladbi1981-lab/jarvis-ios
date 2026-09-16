import XCTest

final class SessionGuardTests: XCTestCase {
    private func j(_ obj: [String: Any]) -> String {
        let d = try! JSONSerialization.data(withJSONObject: obj)
        return String(data: d, encoding: .utf8)!
    }

    // MARK: - parsing

    func testParserNestedResponseID() {
        let json = #"{"type":"response.done","response":{"id":"resp_abc","status":"completed"}}"#
        XCTAssertEqual(SessionEventParser.nested(json, "response", "id"), "resp_abc")
        XCTAssertEqual(SessionEventParser.nested(json, "response", "status"), "completed")
    }

    func testParserFieldResponseID() {
        let json = #"{"type":"response.output_audio.delta","response_id":"resp_abc","delta":"AAA="}"#
        XCTAssertEqual(SessionEventParser.field(json, "response_id"), "resp_abc")
        XCTAssertEqual(SessionEventParser.field(json, "type"), "response.output_audio.delta")
    }

    // MARK: - منع إعادة فتح الرد بعد stop

    func testStopThenLateResponseCreatedRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        g.onStop()   // stopListening
        // response.created متأخر بعد stop → مرفوض (لا جلسة نشطة)
        XCTAssertFalse(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertNil(g.currentResponseID)
    }

    func testStopThenNewSessionOldEventsRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        g.onStop()
        // أحداث الاتصال القديم مرفوضة
        XCTAssertFalse(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        // بدء جديد صريح يفتح دورة جديدة
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "completed"]])))
        XCTAssertEqual(g.pendingStatus, "completed")
    }

    // MARK: - إبطال الرد في كل speech_started

    func testSpeechStartedBeforeFirstDeltaThenCancelledDone() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        g.onBarge()   // speech_started قبل أول delta
        // response.done(R1, cancelled) → لا رد نشط → مرفوض (لا flushTail)
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "cancelled"]])))
        XCTAssertNil(g.pendingStatus)
    }

    // MARK: - done repeat

    func testDoneRepeatRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        // تكرار → currentResponseID nil → مرفوض
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
    }

    // MARK: - failed result محفوظ حتى انتهاء التشغيل

    func testFailedStatusPreserved() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "failed"]])))
        XCTAssertEqual(g.pendingStatus, "failed")   // لا يتحول success
    }

    // MARK: - مقاطعة أثناء التشغيل والذيل

    func testInterruptDuringSpeakingInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        g.onBarge()   // interrupt أثناء التشغيل
        XCTAssertNil(g.currentResponseID)
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "cancelled"]])))
    }

    func testInterruptDuringTailInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        // ذيل ما زال يُشغَّل → speech_started (مقاطعة أثناء الذيل)
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
    }
}
