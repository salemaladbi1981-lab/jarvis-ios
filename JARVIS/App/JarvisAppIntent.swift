#if os(iOS)
import AppIntents
import Foundation

/// جسر بين App Intent وحالة التطبيق. لا توجد خدمة wake-word دائمة في الخلفية؛
/// النظام يستدعي الـ Intent عبر Siri / Shortcuts ثم يفتح التطبيق رسميًا.
enum AppBridge {
    static let pendingStartVoiceKey = "jarvis.pendingStartVoice"

    static var pendingStartVoice: Bool {
        get { UserDefaults.standard.bool(forKey: pendingStartVoiceKey) }
        set { UserDefaults.standard.set(newValue, forKey: pendingStartVoiceKey) }
    }
}

/// مدخل رسمي عبر App Intents لفتح JARVIS وطلب بدء جلسة الصوت.
/// لأن تشغيل الميكروفون قد يكشف بيانات حساسة، يتطلب النظام مصادقة المستخدم
/// قبل تنفيذ الـ Intent عند استدعائه والجهاز مقفل.
struct JarvisVoiceIntent: AppIntent {
    static var title: LocalizedStringResource = "Start Jarvis"
    static var description = IntentDescription("Open Jarvis and start listening.")
    static var openAppWhenRun: Bool = true
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    func perform() async throws -> some IntentResult {
        // لا نبدأ الميكروفون داخل الـ Intent. نسجل طلبًا أحادي الاتجاه؛ التطبيق
        // يستهلكه بعد الفتح ثم يمر بمسار صلاحية الميكروفون المعتاد.
        AppBridge.pendingStartVoice = true
        return .result()
    }
}
#endif
