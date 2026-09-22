import Foundation

/// Enrollment flow: one-time pairing code → POST /auth/enroll → session_token → Keychain.
/// يمتلك UploadManager/JarvisAPI المشتركين ويربطهما بـ BackgroundSessionBridge.
@MainActor
final class EnrollmentManager: ObservableObject {
    @Published var sessionToken: String?
    @Published var isEnrolled = false
    @Published var error: String?

    let baseURL: URL
    var uploadManager: UploadManager?
    var api: JarvisAPI?

    init(baseURL: URL) {
        self.baseURL = baseURL
        self.sessionToken = KeychainStore.load()
        self.isEnrolled = sessionToken != nil
        #if os(iOS)
        // A Siri/App Shortcut voice request must never survive an unauthenticated
        // app launch. If there is no enrolled session, discard any short-lived
        // handoff before the pairing UI can transition into the authenticated app.
        if sessionToken == nil {
            AppBridge.pendingStartVoice = false
        }
        #endif
        if let t = sessionToken {
            wire(t)
        }
    }

    /// يُدخل الرمز → يستلم token → يخزّنه في Keychain → يربط UploadManager.
    func enroll(code: String) async -> Bool {
        let trimmed = code.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { error = "أدخل الرمز"; return false }

        var req = URLRequest(url: baseURL.appendingPathComponent("/auth/enroll"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["code": trimmed])

        do {
            let (d, resp) = try await URLSession.shared.data(for: req)
            guard (resp as? HTTPURLResponse)?.statusCode == 200,
                  let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
                  let token = obj["session_token"] as? String else {
                error = "الرمز غير صالح أو منتهي"
                return false
            }
            KeychainStore.save(token)
            #if os(iOS)
            // Pairing is an authentication boundary. Never carry a voice request
            // that was armed before enrollment into the newly authenticated UI.
            AppBridge.pendingStartVoice = false
            #endif
            sessionToken = token
            isEnrolled = true
            wire(token)
            return true
        } catch {
            self.error = "فشل الاتصال"
            return false
        }
    }

    /// يُنشئ نفس UploadManager المستخدم في التطبيق ويربطه بـ background bridge.
    private func wire(_ token: String) {
        let um = UploadManager(baseURL: baseURL, sessionToken: token)
        uploadManager = um
        api = JarvisAPI(baseURL: baseURL, sessionToken: token)
        #if os(iOS)
        BackgroundSessionBridge.shared = um   // <== الربط الفعلي هنا
        #endif
    }
}
