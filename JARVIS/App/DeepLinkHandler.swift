import Foundation
import Combine

/// حالة التنقّل عبر deep link — يقرأها الـRootView للانتقال للعنصر الصحيح.
@MainActor
final class DeepLinkRouter: ObservableObject {
    @Published var target: DeepLinkTarget?

    func handle(_ url: URL) {
        target = DeepLinkTarget.parse(url)
    }
}
