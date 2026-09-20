#if os(iOS)
import AppIntents
import Foundation
import UIKit

/// يفتح Google Maps للتنقل إلى وجهة عبر آليات iOS الرسمية فقط.
/// عند الاستدعاء من Siri/Shortcuts والجهاز مقفل، يطلب النظام مصادقة المالك
/// قبل فتح التطبيق أو تمرير الوجهة إلى تطبيق الخرائط.
struct JarvisNavigateIntent: AppIntent {
    static var title: LocalizedStringResource = "Navigate with Google Maps"
    static var description = IntentDescription("Open Google Maps turn-by-turn navigation to a destination.")
    static var openAppWhenRun: Bool = true
    static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication

    @Parameter(title: "الوجهة")
    var destination: String

    func perform() async throws -> some IntentResult {
        let normalized = destination.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty, normalized.utf8.count <= 512 else {
            return .result()
        }

        // URLComponents keeps the destination as data, not executable URL syntax,
        // and leaves origin/location ownership to the Maps app after the handoff.
        var components = URLComponents(string: "https://www.google.com/maps/dir/")
        components?.queryItems = [
            URLQueryItem(name: "api", value: "1"),
            URLQueryItem(name: "destination", value: normalized),
            URLQueryItem(name: "travelmode", value: "driving"),
            URLQueryItem(name: "dir_action", value: "navigate")
        ]
        guard let url = components?.url else {
            return .result()
        }

        await MainActor.run {
            UIApplication.shared.open(url)
        }
        return .result()
    }
}
#endif
