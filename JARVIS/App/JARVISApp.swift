import SwiftUI

#if os(iOS)
@main
struct JARVISApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    var body: some Scene {
        WindowGroup {
            if enrollment.isEnrolled {
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
