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
        g.onStop()
        XCTAssertFalse(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertNil(g.currentResponseID)
    }

    func testStopThenNewSessionOldEventsRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        g.onStop()
        XCTAssertFalse(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "completed"]])))
        XCTAssertEqual(g.pendingCompletion, .success)
    }

    // MARK: - دورة الاتصال (connection generation)

    func testConnectionGenerationIsolatesOldCallbacks() {
        var g = SessionGuardState()
        let genA = g.beginConnection()
        let genB = g.beginConnection()   // اتصال B يحل محل A
        XCTAssertFalse(g.isValidConnection(genA))
        XCTAssertTrue(g.isValidConnection(genB))
    }

    func testInvalidateConnection() {
        var g = SessionGuardState()
        let gen = g.beginConnection()
        XCTAssertTrue(g.isValidConnection(gen))
        g.invalidateConnection()
        XCTAssertFalse(g.isValidConnection(gen))
    }

    func testSessionCreatedFromStaleConnectionDoesNotReadyNewSession() {
        var g = SessionGuardState()
        let genA = g.beginConnection()
        let genB = g.beginConnection()   // B يبدأ
        // session.created متأخر من A → غير صالح → لا يُعالج
        if g.isValidConnection(genA) { g.sessionCreated() }
        XCTAssertFalse(g.isSessionReady)   // لم تتأثر B
        // session.created من B → صالح
        if g.isValidConnection(genB) { g.sessionCreated() }
        XCTAssertTrue(g.isSessionReady)
    }

    // MARK: - إبطال الرد في كل speech_started

    func testSpeechStartedBeforeFirstDeltaThenCancelledDone() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onSpeechStarted())   // يبطل R1 قبل أول delta
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "cancelled"]])))
        XCTAssertEqual(g.pendingCompletion, .none)
    }

    func testSpeechStartedAfterStopRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        g.onStop()   // stopListening
        XCTAssertFalse(g.onSpeechStarted())   // متأخر بعد الإيقاف → مرفوض (لا flush/.listening)
    }

    // MARK: - done repeat

    func testDoneRepeatRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
    }

    // MARK: - إشعار انتهاء التشغيل (completion token)

    func testNormalCompletionConsumesSuccessOnce() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        XCTAssertEqual(g.consumeCompletion(), .success)
        XCTAssertEqual(g.consumeCompletion(), .none)   // مرة واحدة فقط
    }

    func testFailedCompletionPreserved() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "failed"]])))
        XCTAssertEqual(g.consumeCompletion(), .failed)
    }

    func testLateDrainAfterStopDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        g.onStop()   // stop → يبطل الاكتمال
        XCTAssertEqual(g.consumeCompletion(), .none)   // إشعار قديم لا ينشر نجاحاً
    }

    func testLateDrainAfterBargeDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        g.onBarge()   // barge → يبطل الاكتمال
        XCTAssertEqual(g.consumeCompletion(), .none)
    }

    func testLateDrainAfterNewCycleDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        // بدء دورة جديدة R2 → يبطل اكتمال R1
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertEqual(g.consumeCompletion(), .none)
        // R2 تكتمل → .success
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "completed"]])))
        XCTAssertEqual(g.consumeCompletion(), .success)
    }

    // MARK: - مقاطعة أثناء التشغيل والذيل

    func testInterruptDuringSpeakingInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "cancelled"]])))
    }

    func testInterruptDuringTailInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]])))
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
    }
}
