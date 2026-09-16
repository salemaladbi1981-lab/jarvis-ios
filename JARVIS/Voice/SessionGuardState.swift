import Foundation

/// حالة حراسة أحداث جلسة Realtime — Foundation-only (قابل للاختبار على macOS).
/// يمنع أحداث الاتصال/الرد القديم من التأثير بعد الإيقاف أو إعادة البدء.
struct SessionGuardState {
    var currentResponseID: String?
    var isSessionReady = false
    var pendingStatus: String?

    /// session.created — جلسة الاتصال الحالية أصبحت نشطة.
    mutating func sessionCreated() {
        isSessionReady = true
    }

    /// response.created — يفتح رداً جديداً فقط إذا الجلسة نشطة.
    @discardableResult
    mutating func onResponseCreated(_ json: String) -> Bool {
        guard isSessionReady,
              let id = SessionEventParser.nested(json, "response", "id") else { return false }
        currentResponseID = id
        return true
    }

    /// response.output_audio.delta — يقبل فقط إذا جلسة نشطة + رد مطابق.
    mutating func onDelta(_ json: String) -> Bool {
        guard isSessionReady, let cur = currentResponseID else { return false }
        if let rid = SessionEventParser.field(json, "response_id"), rid != cur { return false }
        return true
    }

    /// response.done — يقبل فقط الرد المطابق (يصفّر currentResponseID → مرة واحدة).
    @discardableResult
    mutating func onDone(_ json: String) -> Bool {
        guard let cur = currentResponseID,
              let rid = SessionEventParser.nested(json, "response", "id"),
              rid == cur else { return false }
        pendingStatus = SessionEventParser.nested(json, "response", "status") ?? "completed"
        currentResponseID = nil
        return true
    }

    /// إيقاف/انقطاع كامل — يبطل الجلسة والرد الحالي.
    mutating func onStop() {
        currentResponseID = nil
        isSessionReady = false
        pendingStatus = nil
    }

    /// مقاطعة/إلغاء رد — يبطل الرد الحالي فقط (الجلسة تبقى نشطة للـ listening).
    mutating func onBarge() {
        currentResponseID = nil
        pendingStatus = nil
    }
}
