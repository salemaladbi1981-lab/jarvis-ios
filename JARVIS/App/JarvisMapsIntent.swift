#if os(iOS)
import AppIntents
import UIKit

/// يفتح Google Maps للتنقل إلى وجهة — قابل للاستدعاء من قفل الشاشة عبر Siri/Shortcuts.
struct JarvisNavigateIntent: AppIntent {
    static var title: LocalizedStringResource = "Navigate with Google Maps"
    static var description = IntentDescription("Open Google Maps turn-by-turn navigation to a destination.")
    static var openAppWhenRun: Bool = true

    @Parameter(title: "الوجهة")
    var destination: String

    func perform() async throws -> some IntentResult {
        let query = destination.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? destination
        let urlString = "https://www.google.com/maps/dir/?api=1&destination=\(query)&travelmode=driving&dir_action=navigate"
        if let url = URL(string: urlString) {
            await MainActor.run {
                UIApplication.shared.open(url)
            }
        }
        return .result()
    }
}
#endif
