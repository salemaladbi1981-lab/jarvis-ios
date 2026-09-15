import SwiftUI

@main
struct JARVISApp: App {
    var body: some Scene {
        WindowGroup {
            AdaptiveRootView()
                .environment(\.layoutDirection, .rightToLeft)
                .preferredColorScheme(.dark)
        }
    }
}
