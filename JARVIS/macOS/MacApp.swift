import SwiftUI

#if os(macOS)
@main
struct MacApp: App {
    var body: some Scene {
        WindowGroup {
            AdaptiveRootView()
                .environment(\.layoutDirection, .rightToLeft)
                .preferredColorScheme(.dark)
                .frame(minWidth: 1000, minHeight: 640)
        }
    }
}
#endif
