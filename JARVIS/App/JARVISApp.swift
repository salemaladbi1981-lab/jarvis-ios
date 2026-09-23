import SwiftUI

#if os(iOS)
import AppIntents

@main
struct JARVISApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var enrollment = EnrollmentManager(baseURL: JarvisConfig.baseURL)

    init() {
        // Apple recommends refreshing App Shortcut metadata on first launch so
        // Siri / Shortcuts / Spotlight can index the provider through the
        // official App Intents registration path. This does not start audio,
        // bypass lock-screen authentication, or create an always-on listener.
        JarvisShortcuts.updateAppShortcutParameters()
    }

    /// -demo / -sessionToken: يعرض الواجهة الرئيسية بلا enrollment (لـscreenshots الـCI).
    private var isDemo: Bool {
        ProcessInfo.processInfo.arguments.contains("-demo")
        || ProcessInfo.processInfo.arguments.contains("-sessionToken")
    }

    var body: some Scene {
        WindowGroup {
            if enrollment.isEnrolled || isDemo {
                AdaptiveRootView()
                    .environment(\.layoutDirection, .rightToLeft)
                    .preferredColorScheme(.dark)
                    .environmentObject(enrollment)
                    .task { await enrollment.validateSession() }
            } else {
                PairingView()
                    .environmentObject(enrollment)
            }
        }
    }
}
#endif
