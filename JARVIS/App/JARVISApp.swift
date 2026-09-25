import SwiftUI

#if os(iOS)
@main
struct JARVISApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    /// -demo / -sessionToken: يعرض الواجهة الرئيسية بلا enrollment (لـscreenshots الـCI).
    private var isDemo: Bool {
        ProcessInfo.processInfo.arguments.contains("-demo")
        || ProcessInfo.processInfo.arguments.contains("-sessionToken")
    }

    var body: some Scene {
        WindowGroup {
            if enrollment.isEnrolled || isDemo {
                AdaptiveRootView()
                    .id(enrollment.sessionToken)
                    .environment(\.layoutDirection, .rightToLeft)
                    .preferredColorScheme(.dark)
                    .environmentObject(enrollment)
            } else {
                PairingView()
                    .environmentObject(enrollment)
            }
        }
    }
}
#endif
