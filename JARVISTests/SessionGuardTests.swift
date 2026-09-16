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
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .ignore)
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R2", "status": "completed"]]), cycle: 2), .waitForDrain)
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

    func testStopListeningInvalidatesConnectionThenLateSessionCreatedRejected() {
        var g = SessionGuardState()
        let genA = g.beginConnection()
        g.sessionCreated()
        g.onStop()
        XCTAssertFalse(g.isValidConnection(genA))
        if g.isValidConnection(genA) { g.sessionCreated() }
        XCTAssertFalse(g.isSessionReady)
        XCTAssertFalse(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertFalse(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .ignore)
        XCTAssertFalse(g.onSpeechStarted())
    }

    func testNewSessionAfterStopStartsCorrectly() {
        var g = SessionGuardState()
        let genA = g.beginConnection()
        g.sessionCreated()
        g.onStop()
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
        // التأكيد: onSpeechStarted لا يُبطل؛ onBarge (بعد نافذة التأكيد) هو من يبطل الرد.
        g.onBarge()
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "cancelled"]]), cycle: 1), .ignore)
        XCTAssertEqual(g.pendingCompletion, .none)
    }

    func testSpeechStartedDoesNotInvalidateResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onSpeechStarted())
        // الرد يبقى حياً — delta يستمر مقبولاً (منع micro-cut للضوضاء القصيرة)
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
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
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .ignore)
    }

    // MARK: - إشعار انتهاء التشغيل (completion token)

    func testNormalCompletionConsumesSuccessOnce() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .success)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
    }

    func testFailedCompletionPreserved() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "failed"]]), cycle: 1), .waitForDrain)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .failed)
    }

    func testLateDrainAfterStopDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        g.onStop()
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
    }

    func testLateDrainAfterBargeDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        g.onBarge()
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
    }

    func testLateDrainAfterNewCycleDoesNotNotify() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R2", "status": "completed"]]), cycle: 2), .waitForDrain)
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .success)
    }

    // MARK: - هوية دورة التشغيل (drain identity)

    func testDrainIdentityIsolationSuccess() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R2", "status": "completed"]]), cycle: 2), .waitForDrain)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
        XCTAssertEqual(g.pendingCompletion, .success)
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .success)
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .none)
    }

    func testDrainIdentityIsolationFailed() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "failed"]]), cycle: 1), .waitForDrain)
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R2", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R2", "status": "failed"]]), cycle: 2), .waitForDrain)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .none)
        XCTAssertEqual(g.pendingCompletion, .failed)
        XCTAssertEqual(g.consumeCompletion(cycle: 2), .failed)
    }

    // MARK: - رد بلا صوت (no audio) — إنهاء فوري

    func testNoAudioResponseDonePublishesImmediatelyOnce() {
        var g = SessionGuardState()
        g.sessionCreated()
        // R1 ينتهي تشغيله بالكامل (drain حدث) — محاكاة محرك أنهى R1
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        XCTAssertEqual(g.consumeCompletion(cycle: 1), .success)   // R1 drain استهلك نتيجته
        // R2: response.created ثم done(failed) بلا delta
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R2"]])))
        let d = g.resolveDone(j(["response": ["id": "R2", "status": "failed"]]), cycle: 1)
        XCTAssertEqual(d, .publishImmediately(.failed))   // نشر فوري، لا انتظار drain
        XCTAssertEqual(g.pendingCompletion, .none)        // لا نتيجة معلقة
        XCTAssertEqual(g.pendingCompletionCycle, 0)       // هوية دورة صفر (لا drain معلق)
    }

    func testNoAudioResponseDoneIgnoredOnRepeat() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "failed"]]), cycle: 1), .publishImmediately(.failed))
        // تكرار done بلا صوت → مرفوض (currentResponseID صُفّر)
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "failed"]]), cycle: 1), .ignore)
    }

    // MARK: - مقاطعة أثناء التشغيل والذيل

    func testInterruptDuringSpeakingInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "cancelled"]]), cycle: 1), .ignore)
    }

    func testInterruptDuringTailInvalidatesResponse() {
        var g = SessionGuardState()
        g.sessionCreated()
        XCTAssertTrue(g.onResponseCreated(j(["response": ["id": "R1"]])))
        XCTAssertTrue(g.onDelta(j(["response_id": "R1", "delta": "AAA="])))
        XCTAssertEqual(g.resolveDone(j(["response": ["id": "R1", "status": "completed"]]), cycle: 1), .waitForDrain)
        g.onBarge()
        XCTAssertNil(g.currentResponseID)
    }
}
