import Foundation

/// deep-link canonical: jarvis://conversation|task|delivery/{id}.
enum DeepLinkTarget: Equatable {
    case conversation(String)
    case task(String)
    case delivery(String)

    static func parse(_ url: URL) -> DeepLinkTarget? {
        guard url.scheme?.lowercased() == "jarvis" else { return nil }
        let parts = url.pathComponents.filter { $0 != "/" }
        guard parts.count == 2, !parts[1].isEmpty else { return nil }
        switch parts[0].lowercased() {
        case "conversation": return .conversation(parts[1])
        case "task": return .task(parts[1])
        case "delivery": return .delivery(parts[1])
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
