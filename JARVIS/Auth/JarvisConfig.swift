import Foundation

/// إعدادات عامة (عنوان السيرفر — ليس سرًا).
/// تدعم overrides للـCI/integration: -baseURL <url> و -sessionToken <token>.
enum JarvisConfig {
    static var baseURL: URL {
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-baseURL"), i + 1 < args.count,
           let u = URL(string: args[i + 1]) {
            return u
        }
        return URL(string: "https://jarvis-api.qeyas.app")!
    }

    /// session token محقون من launch arg (للـCI فقط) — لا يُستخدم في الإنتاج.
    static var injectedSessionToken: String? {
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-sessionToken"), i + 1 < args.count {
            return args[i + 1]
        }
        return nil
    }
}
