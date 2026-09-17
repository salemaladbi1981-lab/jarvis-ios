#if os(iOS)
import AppIntents
import Foundation

/// جسر بين الـ App Intent وحالة التطبيق — يطلب بدء الصوت عند الفتح من قفل الشاشة.
enum AppBridge {
    static let pendingStartVoiceKey = "jarvis.pendingStartVoice"

    static var pendingStartVoice: Bool {
        get { UserDefaults.standard.bool(forKey: pendingStartVoiceKey) }
        set { UserDefaults.standard.set(newValue, forKey: pendingStartVoiceKey) }
    }
}

/// يفتح JARVIS ويبدأ الاستماع — قابل للاستدعاء من شاشة القفل عبر Siri/Shortcuts.
struct JarvisVoiceIntent: AppIntent {
    static var title: LocalizedStringResource = "Start Jarvis"
    static var description = IntentDescription("Open Jarvis and start listening.")
    static var openAppWhenRun: Bool = true

    func perform() async throws -> some IntentResult {
        // علامة معلّقة يلتقطها التطبيق عند فتحه ويبدأ منها الصوت.
        AppBridge.pendingStartVoice = true
        return .result()
    }
}
#endif
