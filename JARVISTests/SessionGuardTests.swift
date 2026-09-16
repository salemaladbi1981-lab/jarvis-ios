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
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "completed"]]), cycle: 2))
        XCTAssertEqual(g.pendingCompletion, .success)
    }

    // MARK: - دورة الاتصال (connection generation)

    func testConnectionGenerationIsolatesOldCallbacks() {
        var g = SessionGuardState()
        let genA = g.beginConnection()
        let genB = g.beginConnection()
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
        let genB = g.beginConnection()
        if g.isValidConnection(genA) { g.sessionCreated() }
        XCTAssertFalse(g.isSessionReady)
        if g.isValidConnection(genB) { g.sessionCreated() }
        XCTAssertTrue(g.isSessionReady)
    }

    // MARK: - stopListening يبطل دورة الاتصال

    func testStopListeningInvalidatesConnectionThenLateSessionCreatedRejected() {
        var g = SessionGuardState()
        let genA = g.beginConnection()   // اتصال A
        g.sessionCreated()
        g.onStop()   // stopListening → يبطل الجلسة + الاتصال
        // جيل A لم يعد صالحاً → session.created(A) المتأخر لا يُعالج
        XCTAssertFalse(g.isValidConnection(genA))
        if g.isValidConnection(genA) { g.sessionCreated() }
        XCTAssertFalse(g.isSessionReady)   // لا جاهزية
        // أحداث متأخرة أخرى من A مرفوضة
        XCTAssertFalse(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertFalse(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        XCTAssertFalse(g.onSpeechStarted())
    }

    func testNewSessionAfterStopStartsCorrectly() {
        var g = SessionGuardState()
        let genA = g.beginConnection()
        g.sessionCreated()
        g.onStop()   // يبطل A
        // بدء جديد صريح
        let genB = g.beginConnection()
        XCTAssertTrue(g.isValidConnection(genB))
        if g.isValidConnection(genB) { g.sessionCreated() }
        XCTAssertTrue(g.isSessionReady)
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
    }

    // MARK: - إبطال الرد في كل speech_started

    func testSpeechStartedBeforeFirstDeltaThenCancelledDone() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onSpeechStarted())
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "cancelled"]]), cycle: 1))
        XCTAssertEqual(g.pendingCompletion, .none)
    }

    func testSpeechStartedAfterStopRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        g.onStop()
        XCTAssertFalse(g.onSpeechStarted())
    }

    // MARK: - done repeat

    func testDoneRepeatRejected() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
    }

    // MARK: - إشعار انتهاء التشغيل (completion token)

    func testNormalCompletionConsumesSuccessOnce() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .success)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
    }

    func testFailedCompletionPreserved() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "failed"]]), cycle: 1))
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .failed)
    }

    func testLateDrainAfterStopDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        g.onStop()
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
    }

    func testLateDrainAfterBargeDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        g.onBarge()
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
    }

    func testLateDrainAfterNewCycleDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "completed"]]), cycle: 2))
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .success)
    }

    // MARK: - هوية دورة التشغيل (drain identity) — حتمية

    func testDrainIdentityIsolationSuccess() {
        var g = SessionGuardState()
        g.sessionCreated()
        // R1
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        // R2
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "completed"]]), cycle: 2))
        // drain(R1) متأخر → لا ينشر ولا يمس R2
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
        XCTAssertEqual(g.pendingCompletion, .success)   // R2 سليمة
        // drain(R2) → يستهلك R2 مرة واحدة
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .success)
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .none)
    }

    func testDrainIdentityIsolationFailed() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "failed"]]), cycle: 1))
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R2", "status": "failed"]]), cycle: 2))
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
        XCTAssertEqual(g.pendingCompletion, .failed)   // R2 سليمة
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .failed)
    }

    // MARK: - مقاطعة أثناء التشغيل والذيل

    func testInterruptDuringSpeakingInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
        XCTAssertFalse(g.onDone(j(["response": ["id": "R1", "status": "cancelled"]]), cycle: 1))
    }

    func testInterruptDuringTailInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1))
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
    }
}
