#if os(iOS)
import UIKit
#endif

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

// AppDelegate (JARVIS/App/AppDelegate.swift) يستدعي handleEventsForBackgroundURLSession.
// BackgroundSessionBridge.shared يُربط في EnrollmentManager.wire(token).
