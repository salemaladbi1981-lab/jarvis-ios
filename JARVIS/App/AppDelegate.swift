import UIKit

#if os(iOS)
/// AppDelegate — يستقبل handleEventsForBackgroundURLSession ويربطه بالـ bridge.
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        // يربط delegate الإشعارات مبكراً — حتى تعمل ضغطة الإشعار عند التطبيق المقتول.
        NotificationManager.shared.configure()
        return true
    }

    /// If Siri / Shortcuts opened the app but the scene backgrounds before SwiftUI consumes
    /// the one-shot voice handoff, cancel that pending request. Returning to the app later must
    /// never start the microphone from an abandoned lock-screen invocation.
    func applicationDidEnterBackground(_ application: UIApplication) {
        AppBridge.pendingStartVoice = false
    }

    func application(_ application: UIApplication,
                     handleEventsForBackgroundURLSession identifier: String,
                     completionHandler: @escaping () -> Void) {
        BackgroundSessionBridge.handleEventsForBackgroundURLSession(identifier: identifier,
                                                                    completionHandler: completionHandler)
    }
}
#endif
