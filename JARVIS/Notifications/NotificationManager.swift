import Foundation
import UserNotifications

#if os(iOS)

/// إدارة الإشعارات المحلية (local notifications) — صلاحية + جدولة + فتح على العنصر الصحيح.
/// الإشعار يحمل deep-link في userInfo (jarvis://conversation|task|delivery/{id})،
/// وعند الضغط يُفتح العنصر المحدد عبر RootView (وليس الشاشة الرئيسية فقط).
@MainActor
final class NotificationManager: NSObject, ObservableObject {
    static let shared = NotificationManager()

    @Published var authorizationStatus: UNAuthorizationStatus = .notDetermined
    /// deep link معلّق من ضغطة إشعار (بارد أو دافئ) — يلتقطه RootView عند الجاهزية.
    @Published var pendingCount: Int = 0
    @Published var pendingDeepLink: DeepLinkTarget?

    override private init() { super.init() }

    /// يُستدعى مرة واحدة عند الإطلاق — يربط الـ delegate (حتى تعمل ضغطة الإشعار عند التطبيق المقتول).
    func configure() {
        let center = UNUserNotificationCenter.current()
        center.delegate = self
        Task { await self.refreshStatus() }
    }

    /// صلاحية الإشعارات — يُستدعى عند أول استخدام (لا يزعج قبل الحاجة).
    @discardableResult
    func requestAuthorization() async -> Bool {
        let center = UNUserNotificationCenter.current()
        guard let granted = try? await center.requestAuthorization(options: [.alert, .sound, .badge]) else {
            await refreshStatus()
            return false
        }
        await refreshStatus()
        return granted
    }

    func refreshStatus() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        authorizationStatus = settings.authorizationStatus
        let pending = await UNUserNotificationCenter.current().pendingNotificationRequests()
        pendingCount = pending.count
    }

    /// جدولة إشعار محلي يحمل deep-link للعنصر الصحيح.
    func schedule(_ target: DeepLinkTarget, title: String, body: String, delaySeconds: TimeInterval = 1) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        content.userInfo = ["jarvis_deep_link": target.url]

        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: max(1, delaySeconds), repeats: false)
        let request = UNNotificationRequest(identifier: "jarvis-\\(UUID().uuidString)", content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request)
        Task { await self.refreshStatus() }
    }

    /// إزالة الإشعارات المعلّقة (عند فتح العنصر مباشرة أو عند الإلغاء).
    func cancelPending() {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
    }

    /// عند تسليم مهمة إلى الخلفية — إشعار «قيد التنفيذ» يفتح المهمة.
    func notifyTaskHandoff(_ taskId: String) {
        Task { await self.ensureAuthorized() }
        schedule(.task(taskId), title: "مهمة قيد التنفيذ", body: "جارفس يعمل على مهمتك — ستُخطرك عند الجاهزية.")
    }

    /// عند جاهزية تسليم — إشعار يفتح التسليم مباشرة.
    func notifyDeliveryReady(_ deliveryId: String, filename: String) {
        Task { await self.ensureAuthorized() }
        schedule(.delivery(deliveryId), title: "التسليم جاهز", body: filename)
    }

    private func ensureAuthorized() async {
        if authorizationStatus == .notDetermined {
            _ = await requestAuthorization()
        }
    }
}

extension NotificationManager: UNUserNotificationCenterDelegate {
    /// تقديم الإشعار في المقدمة (foreground) — بدون إسقاطه بصمت.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound])
    }

    /// ضغطة الإشعار (مقدمة/خلفية/تطبيق مقتول) → deep-link للعنصر الصحيح.
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        let info = response.notification.request.content.userInfo
        if let str = info["jarvis_deep_link"] as? String, let url = URL(string: str) {
            let target = DeepLinkTarget.parse(url)
            DispatchQueue.main.async {
                self.pendingDeepLink = target
            }
        }
        completionHandler()
    }
}

#endif
