#if os(iOS)
import AppIntents
import Foundation

/// جسر بين App Intent وحالة التطبيق. لا توجد خدمة wake-word دائمة في الخلفية؛
/// النظام يستدعي الـ Intent عبر Siri / Shortcuts ثم يفتح التطبيق رسميًا.
/// طلب بدء الصوت قصير العمر حتى لا يبدأ الميكروفون لاحقًا بسبب Intent قديم.
enum AppBridge {
    static let pendingStartVoiceKey = "jarvis.pendingStartVoice.requestedAt"
    static let pendingStartVoiceMaxAge: TimeInterval = 30

    static var pendingStartVoice: Bool {
        get {
            let requestedAt = UserDefaults.standard.double(forKey: pendingStartVoiceKey)
            guard requestedAt > 0 else { return false }

            let age = Date().timeIntervalSince1970 - requestedAt
            guard age >= 0, age <= pendingStartVoiceMaxAge else {
                UserDefaults.standard.removeObject(forKey: pendingStartVoiceKey)
                return false
            }
            return true
        }
        set {
            if newValue {
                UserDefaults.standard.set(Date().timeIntervalSince1970, forKey: pendingStartVoiceKey)
            } else {
                UserDefaults.standard.removeObject(forKey: pendingStartVoiceKey)
            }
        }
    }
}

/// مدخل رسمي عبر App Intents لفتح JARVIS وطلب بدء جلسة الصوت.
/// لأن تشغيل الميكروفون قد يكشف بيانات حساسة، يتطلب النظام مصادقة المستخدم
/// قبل تنفيذ الـ Intent عند استدعائه والجهاز مقفل.
struct JarvisVoiceIntent: AppIntent {
    static var title: LocalizedStringResource = "Start Jarvis"
    static var description = IntentDescription("Open Jarvis and start listening.")
    // Xcode 15 / iOS 17 compatibility. On newer SDKs Apple replaces this with
    // AppIntent.supportedModes; migrate when the project toolchain is raised.
    static var openAppWhenRun: Bool = true
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    func perform() async throws -> some IntentResult {
        // لا نبدأ الميكروفون داخل الـ Intent. نسجل طلبًا قصير العمر؛ التطبيق
        // يستهلكه بعد الفتح ثم يمر بمسار صلاحية الميكروفون المعتاد.
        AppBridge.pendingStartVoice = true
        return .result()
    }
}
#endif
