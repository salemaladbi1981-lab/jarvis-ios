import SwiftUI

#if os(iOS)
@main
struct JARVISApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    /// -demo: يعرض الواجهة الرئيسية بلا enrollment (لـscreenshots الـCI — الواجهات الحقيقية + API حقيقي).
    private var isDemo: Bool { ProcessInfo.processInfo.arguments.contains("-demo") }

    var body: some Scene {
        WindowGroup {
            if enrollment.isEnrolled || isDemo {
                AdaptiveRootView()
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
