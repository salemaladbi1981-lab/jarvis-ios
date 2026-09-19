import Foundation

/// deep-link canonical: jarvis://conversation|task|delivery/{id}.
enum DeepLinkTarget: Equatable {
    case conversation(String)
    case task(String)
    case delivery(String)

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

/// حالة التنقّل عبر deep link — يقرأها الـRootView للانتقال للعنصر الصحيح.
@MainActor
final class DeepLinkRouter: ObservableObject {
    @Published var target: DeepLinkTarget?

    func handle(_ url: URL) {
        target = DeepLinkTarget.parse(url)
    }
}
