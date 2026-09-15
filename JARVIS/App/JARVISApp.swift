import SwiftUI

@main
struct JARVISApp: App {
    var body: some Scene {
        WindowGroup {
            HomeView()
                .environment(\.layoutDirection, .rightToLeft)
                .preferredColorScheme(.dark)
        }
    }
}
