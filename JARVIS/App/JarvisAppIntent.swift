#if os(iOS)
import AppIntents
import Foundation

/// جسر بين App Intent وحالة التطبيق. لا توجد خدمة wake-word دائمة في الخلفية؛
/// النظام يستدعي الـ Intent عبر Siri / Shortcuts ثم يفتح التطبيق رسميًا.
/// طلب بدء الصوت قصير العمر ويُستهلك مرة واحدة حتى لا يبدأ الميكروفون لاحقًا
/// بسبب Intent قديم أو بسبب تكرار lifecycle handoff بعد فتح التطبيق.
enum AppBridge {
    static let pendingStartVoiceKey = "jarvis.pendingStartVoice.requestedAt"
    static let pendingStartVoiceMaxAge: TimeInterval = 30

    /// يستهلك طلب Siri/Shortcut الذّي لم تنتهِ صلاحيته بشكل one-shot.
    /// القراءة الناجحة تحذف العلامة قبل إعادة true، لذلك لا يمكن لنفس الطلب
    /// تشغيل جلسة صوت ثانية إذا أعادت SwiftUI استدعاء handoff أثناء الفتح.
    static func consumePendingStartVoice(now: TimeInterval = Date().timeIntervalSince1970) -> Bool {
        let requestedAt = UserDefaults.standard.double(forKey: pendingStartVoiceKey)
        guard requestedAt > 0 else { return false }

        let age = now - requestedAt
        guard age >= 0, age <= pendingStartVoiceMaxAge else {
            UserDefaults.standard.removeObject(forKey: pendingStartVoiceKey)
            return false
        }

        UserDefaults.standard.removeObject(forKey: pendingStartVoiceKey)
        return true
    }

    static var pendingStartVoice: Bool {
        get { consumePendingStartVoice() }
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
    // iOS 17–25 compatibility. On iOS 26+ use Apple's explicit foreground mode.
    static var openAppWhenRun: Bool = true
    #if compiler(>=6.2)
    @available(iOS 26.0, *)
    static var supportedModes: IntentModes { .foreground(.immediate) }
    #endif
    #if compiler(>=6.4)
    @available(iOS 27.0, *)
    static var allowedExecutionTargets: IntentExecutionTargets { .main }
    #endif
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    func perform() async throws -> some IntentResult {
        // لا نبدأ الميكروفون داخل الـ Intent. نسجل طلبًا قصير العمر؛ التطبيق
        // يستهلكه بعد الفتح ثم يمر بمسار صلاحية الميكروفون المعتاد.
        AppBridge.pendingStartVoice = true
        return .result()
    }
}

/// فتح التطبيق فقط من Siri / Shortcuts بدون تسليح الميكروفون.
/// هذا يفصل أمر "افتح جارفس" عن أمر "كلّم جارفس" حتى لا يبدأ الصوت
/// لمجرد أن المستخدم أراد الوصول للتطبيق من شاشة القفل.
struct JarvisOpenIntent: AppIntent {
    static var title: LocalizedStringResource = "Open Jarvis"
    static var description = IntentDescription("Open Jarvis without starting the microphone.")
    static var openAppWhenRun: Bool = true
    #if compiler(>=6.2)
    @available(iOS 26.0, *)
    static var supportedModes: IntentModes { .foreground(.immediate) }
    #endif
    #if compiler(>=6.4)
    @available(iOS 27.0, *)
    static var allowedExecutionTargets: IntentExecutionTargets { .main }
    #endif
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    func perform() async throws -> some IntentResult {
        // امسح أي طلب صوت قديم قصير العمر؛ أمر الفتح وحده لا يطلب الميكروفون.
        AppBridge.pendingStartVoice = false
        return .result()
    }
}
#endif
