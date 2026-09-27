import SwiftUI

#if os(macOS)
@main
struct MacApp: App {
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    /// -demo / -sessionToken: يفتح الواجهة بلا enrollment (للتطوير فقط).
    private var isDemo: Bool {
        ProcessInfo.processInfo.arguments.contains("-demo")
        || ProcessInfo.processInfo.arguments.contains("-sessionToken")
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if enrollment.isEnrolled || isDemo {
                    AdaptiveRootView()
                } else {
                    PairingView()
                }
            }
            .environmentObject(enrollment)
            .environment(\.layoutDirection, .rightToLeft)
            .preferredColorScheme(.dark)
            .frame(minWidth: 1000, minHeight: 640)
        }
    }
}
#endif
