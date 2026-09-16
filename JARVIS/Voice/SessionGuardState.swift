import Foundation

/// نتيجة اكتمال الرد عند تصريف التشغيل المحلي.
/// `.none` لا تعني نجاحاً — بل «لا اكتمال معلّق».
enum PlaybackCompletion: Equatable {
    case none
    case success
    case failed
}

/// حالة حراسة أحداث جلسة Realtime — Foundation-only (قابل للاختبار على macOS).
/// يجمع: هوية الرد، جاهزية الجلسة، جيل الاتصال، ونتيجة الاكتمال المربوطة بهوية دورة التشغيل.
struct SessionGuardState {
    var currentResponseID: String?
    var isSessionReady = false
    var pendingCompletion: PlaybackCompletion = .none
    /// هوية دورة التشغيل (playbackGeneration) التي أنتجت النتيجة المعلقة.
    private(set) var pendingCompletionCycle = 0

    /// جيل الاتصال — يعزل callbacks الاتصال القديم عن الجديد.
    private(set) var connectionGeneration = 0

    // MARK: - دورة الاتصال (WebSocket)

    /// بدء اتصال جديد — يزيد الجيل ويُرجع هويته للربط بالـ callbacks.
    @discardableResult
    mutating func beginConnection() -> Int {
        connectionGeneration += 1
        return connectionGeneration
    }

    /// إبطال الاتصال الحالي (قطع/استبدال) — أي callback قديم يصبح غير صالح.
    mutating func invalidateConnection() {
        connectionGeneration += 1
    }

    /// هل هذا الجيل هو الاتصال الحالي المسموح له بالمعالجة؟
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
        resetCompletion()   // بدء دورة رد جديدة يبطل اكتمال الرد السابق
        return true
    }

    /// response.output_audio.delta — يقبل فقط إذا جلسة نشطة + رد مطابق.
    mutating func onDelta(_ json: String) -> Bool {
        guard isSessionReady, let cur = currentResponseID else { return false }
        if let rid = SessionEventParser.field(json, "response_id"), rid != cur { return false }
        resetCompletion()   // أي صوت لرد جديد يبطل الاكتمال المعلّق القديم
        return true
    }

    /// response.done — يقبل فقط الرد المطابق، ويربط النتيجة بهوية دورة تشغيله.
    @discardableResult
    mutating func onDone(_ json: String, cycle: Int) -> Bool {
        guard let cur = currentResponseID,
              let rid = SessionEventParser.nested(json, "response", "id"),
              rid == cur else { return false }
        let status = SessionEventParser.nested(json, "response", "status") ?? "completed"
        pendingCompletion = (status == "failed") ? .failed : .success
        pendingCompletionCycle = cycle
        currentResponseID = nil
        return true
    }

    /// قبول حدث speech_started — الجلسة نشطة فقط، ويُبطل الرد الجاري.
    @discardableResult
    mutating func onSpeechStarted() -> Bool {
        guard isSessionReady else { return false }
        onBarge()
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
        resetCompletion()
        connectionGeneration += 1   // إبطال دورة الاتصال — callbacks قديمة تُرفض
    }

    /// مقاطعة/إلغاء رد — يبطل الرد الحالي فقط (الجلسة تبقى نشطة للـ listening).
    mutating func onBarge() {
        currentResponseID = nil
        resetCompletion()
    }

    private mutating func resetCompletion() {
        pendingCompletion = .none
        pendingCompletionCycle = 0
    }
}
