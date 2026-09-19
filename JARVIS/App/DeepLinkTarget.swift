import Foundation

/// deep-link canonical: jarvis://conversation|task|delivery/{id}.
/// Foundation خالصة (قابلة للاختبار في target الاختبار macOS مباشرة).
enum DeepLinkTarget: Equatable {
    case conversation(String)
    case task(String)
    case delivery(String)

    /// الشكل القانوني للـ deep link — يُخزَّن في userInfo إشعار ويُستخدم للفتح المباشر.
    var url: String {
        switch self {
        case .conversation(let id): return "jarvis://conversation/\(id)"
        case .task(let id): return "jarvis://task/\(id)"
        case .delivery(let id): return "jarvis://delivery/\(id)"
        }
    }

    static func parse(_ url: URL) -> DeepLinkTarget? {
        guard url.scheme?.lowercased() == "jarvis" else { return nil }
        // jarvis://conversation/{id} → host = type, path = id
        let host = url.host?.lowercased()
        let id = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard !id.isEmpty else { return nil }
        switch host {
        case "conversation": return .conversation(id)
        case "task": return .task(id)
        case "delivery": return .delivery(id)
        default: return nil
        }
    }
}
