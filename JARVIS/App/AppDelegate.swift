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

    func application(_ application: UIApplication,
                     handleEventsForBackgroundURLSession identifier: String,
                     completionHandler: @escaping () -> Void) {
        BackgroundSessionBridge.handleEventsForBackgroundURLSession(identifier: identifier,
                                                                    completionHandler: completionHandler)
    }
}
#endif
