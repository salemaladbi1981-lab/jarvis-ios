import Foundation

/// نتيجة اكتمال الرد عند تصريف التشغيل المحلي.
/// `.none` لا تعني نجاحاً — بل «لا اكتمال معلّق».
enum PlaybackCompletion: Equatable {
    case none
    case success
    case failed
}

/// قرار إنهاء الرد عند وصول response.done.
enum DoneDisposition: Equatable {
    case ignore                            // رد غير مطابق (stale) — لا شيء
    case waitForDrain                      // رد بصوت — انتظر اكتمال التشغيل المحلي
    case publishImmediately(PlaybackCompletion)  // رد بلا صوت — انشر النتيجة فوراً
}

/// حالة حراسة أحداث جلسة Realtime — Foundation-only (قابل للاختبار على macOS).
/// يجمع: هوية الرد، جاهزية الجلسة، جيل الاتصال، ونتيجة الاكتمال المربوطة بهوية دورة التشغيل.
struct SessionGuardState {
    var currentResponseID: String?
    var isSessionReady = false
    var pendingCompletion: PlaybackCompletion = .none
    /// هوية دورة التشغيل (playbackGeneration) التي أنتجت النتيجة المعلقة.
    private(set) var pendingCompletionCycle = 0
    /// هل أنتج الرد الحالي صوتاً (delta)؟ — يحدد مسار الإنهاء (drain مقابل فوري).
    private(set) var currentResponseHasAudio = false

    /// جيل الاتصال — يعزل callbacks الاتصال القديم عن الجديد.
    private(set) var connectionGeneration = 0

    // MARK: - دورة الاتصال (WebSocket)

    @discardableResult
    mutating func beginConnection() -> Int {
        connectionGeneration += 1
        return connectionGeneration
    }

    mutating func invalidateConnection() {
        connectionGeneration += 1
    }

    func isValidConnection(_ generation: Int) -> Bool {
        generation == connectionGeneration
    }

    // MARK: - دورة الجلسة/الرد

    /// session.created — بدء الجلسة (لا يشترط isSessionReady؛ هو من يضبطه).
    mutating func sessionCreated() {
        isSessionReady = true
    }

    /// response.created — يفتح رداً جديداً فقط إذا الجلسة نشطة.
    @discardableResult
    mutating func onResponseCreated(_ json: String) -> Bool {
        guard isSessionReady,
              let id = SessionEventParser.nested(json, "response", "id") else { return false }
        currentResponseID = id
        currentResponseHasAudio = false   // رد جديد — لا صوت بعد
        resetCompletion()
        return true
    }

    /// response.output_audio.delta — يقبل فقط إذا جلسة نشطة + رد مطابق.
    mutating func onDelta(_ json: String) -> Bool {
        guard isSessionReady, let cur = currentResponseID else { return false }
        if let rid = SessionEventParser.field(json, "response_id"), rid != cur { return false }
        currentResponseHasAudio = true   // صوت وصل لهذا الرد
        resetCompletion()
        return true
    }

    /// response.done — يقرر مسار الإنهاء حسب وجود صوت للرد.
    /// - رد بلا صوت → `publishImmediately` (لا تنتظر drain، لا تترك نتيجة معلقة).
    /// - رد بصوت → `waitForDrain` (تربط النتيجة بهوية دورة التشغيل).
    mutating func resolveDone(_ json: String, cycle: Int) -> DoneDisposition {
        guard let cur = currentResponseID,
              let rid = SessionEventParser.nested(json, "response", "id"),
              rid == cur else { return .ignore }
        let status = SessionEventParser.nested(json, "response", "status") ?? "completed"
        let completion: PlaybackCompletion = (status == "failed") ? .failed : .success
        currentResponseID = nil
        if currentResponseHasAudio {
            pendingCompletion = completion
            pendingCompletionCycle = cycle
            return .waitForDrain
        } else {
            // بلا صوت — النتيجة تُنشر فوراً ولا تبقى معلقة (لا تتأثر بإشعار drain قديم).
            resetCompletion()
            return .publishImmediately(completion)
        }
    }

    /// قبول حدث speech_started — الجلسة نشطة فقط.
    /// لا يُبطل الرد هنا (التأكيد يؤجل الإبطال — يمنع micro-cut للضوضاء القصيرة).
    @discardableResult
    mutating func onSpeechStarted() -> Bool {
        guard isSessionReady else { return false }
        return true
    }

    /// استهلاك نتيجة الاكتمال فقط إذا تطابق هوية دورة التشغيل — وإلا تُرفض ولا تُلمس.
    mutating func consumeCompletion(cycle: Int) -> PlaybackCompletion {
        guard cycle == pendingCompletionCycle else { return .none }
        let c = pendingCompletion
        resetCompletion()
        return c
    }

    /// إيقاف/انقطاع كامل — يبطل الجلسة والرد الحالي ودورة الاتصال.
    mutating func onStop() {
        currentResponseID = nil
        isSessionReady = false
        currentResponseHasAudio = false
        resetCompletion()
        connectionGeneration += 1
    }

    /// مقاطعة/إلغاء رد — يبطل الرد الحالي فقط (الجلسة تبقى نشطة للـ listening).
    mutating func onBarge() {
        currentResponseID = nil
        currentResponseHasAudio = false
        resetCompletion()
    }

    private mutating func resetCompletion() {
        pendingCompletion = .none
        pendingCompletionCycle = 0
    }
}

/// Captures only a bounded candidate while playback is active.
/// Identity is decided by the authenticated verifier, never by loudness alone.
struct OwnerVoiceCandidate {
    private(set) var epoch = 0
    private(set) var buffer = Data()
    private(set) var inFlight = false
    private(set) var confirmations = 0
    private var quietBytes = 0
    private var voicedBytes = 0
    private var lastSubmittedBytes = 0

    mutating func reset() {
        epoch += 1
        buffer.removeAll(keepingCapacity: true)
        inFlight = false
        confirmations = 0
        quietBytes = 0
        voicedBytes = 0
        lastSubmittedBytes = 0
    }

    mutating func append(_ data: Data, level: Double) {
        let voiced = level >= 0.004
        if buffer.isEmpty && !voiced { return }
        buffer.append(data)
        if voiced { voicedBytes += data.count; quietBytes = 0 }
        else { quietBytes += data.count }
        // End a candidate on a 350 ms pause; cap retained audio at six seconds.
        if quietBytes >= 16800 || buffer.count > 288000 { reset() }
    }

    mutating func nextClip() -> (Data, Int)? {
        guard !inFlight, buffer.count >= 76800,
              buffer.count - lastSubmittedBytes >= 21600,
              voicedBytes * 2 >= buffer.count, quietBytes < 9600 else { return nil }
        inFlight = true
        lastSubmittedBytes = buffer.count
        return (Data(buffer.suffix(115200)), epoch)
    }

    mutating func complete(matched: Bool, epoch requestEpoch: Int) -> Data? {
        guard requestEpoch == epoch, inFlight else { return nil }
        inFlight = false
        confirmations = matched ? confirmations + 1 : 0
        guard confirmations >= 2 else { return nil }
        let speech = buffer
        reset()
        return speech
    }
}
