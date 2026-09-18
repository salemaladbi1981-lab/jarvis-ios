import UIKit

/// ربط background URLSession events في AppDelegate/SceneDelegate.
/// يُستدعى عند إعادة تشغيل التطبيق لإكمال رفع خلفي.
enum BackgroundSessionBridge {
    static var shared: UploadManager?

    @MainActor
    static func handleEventsForBackgroundURLSession(identifier: String, completionHandler: @escaping () -> Void) {
        // نفس identifier المستخدم في UploadManager
        shared?.setBackgroundCompletionHandler(completionHandler)
        shared?.restoreOnLaunch()
    }
}

// مثال الاستدعاء داخل AppDelegate:
//   func application(_ application: UIApplication,
//                    handleEventsForBackgroundURLSession identifier: String,
//                    completionHandler: @escaping () -> Void) {
//       BackgroundSessionBridge.handleEventsForBackgroundURLSession(identifier: identifier,
//                                                                  completionHandler: completionHandler)
//   }
