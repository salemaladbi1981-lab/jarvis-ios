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
        #if DEBUG
        self.sessionToken = JarvisConfig.injectedSessionToken ?? KeychainStore.load()
        #else
        self.sessionToken = KeychainStore.load()
        #endif
        self.isEnrolled = sessionToken != nil
        if let t = sessionToken {
            wire(t)
        }
    }

    /// يُدخل الرمز → يستلم token → يخزّنه في Keychain → يربط UploadManager.
    func enroll(code: String) async -> Bool {
        let trimmed = code.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { error = "أدخل الرمز"; return false }
        error = nil

        var req = URLRequest(url: baseURL.appendingPathComponent("/auth/enroll"))
        req.httpMethod = "POST"
        req.timeoutInterval = 30
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["code": trimmed])

        do {
            let (d, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse else {
                error = "استجابة خادم جارفس غير صالحة"
                return false
            }

            guard http.statusCode == 200 else {
                error = enrollmentMessage(forHTTPStatus: http.statusCode)
                return false
            }

            guard let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
                  let token = obj["session_token"] as? String,
                  !token.isEmpty else {
                error = "استجابة الربط ناقصة. حاول مرة أخرى."
                return false
            }

            guard KeychainStore.save(token) else {
                error = "تعذر حفظ جلسة جارفس بأمان على الجهاز"
                return false
            }

            sessionToken = token
            isEnrolled = true
            wire(token)
            error = nil
            return true
        } catch {
            self.error = enrollmentMessage(for: error)
            return false
        }
    }

    private func enrollmentMessage(forHTTPStatus code: Int) -> String {
        switch code {
        case 400, 401, 404, 410:
            return "الرمز غير صالح أو منتهي"
        case 408, 504:
            return "انتهت مهلة الاتصال بخادم جارفس. حاول مرة أخرى."
        case 429:
            return "محاولات الربط كثيرة حاليًا. حاول مرة أخرى بعد قليل."
        case 500...599:
            return "خادم جارفس غير متاح مؤقتًا. حاول مرة أخرى."
        default:
            return "تعذر ربط الجهاز (HTTP \(code))"
        }
    }

    private func enrollmentMessage(for error: Error) -> String {
        guard let urlError = error as? URLError else {
            return "فشل الاتصال بخادم جارفس"
        }
        switch urlError.code {
        case .notConnectedToInternet:
            return "لا يوجد اتصال بالإنترنت. تحقق من الشبكة ثم حاول مرة أخرى."
        case .timedOut:
            return "انتهت مهلة الاتصال بخادم جارفس. حاول مرة أخرى."
        case .networkConnectionLost:
            return "انقطع اتصال الشبكة أثناء ربط الجهاز. حاول مرة أخرى."
        case .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed:
            return "تعذر الوصول إلى خادم جارفس. تحقق من الشبكة ثم حاول مرة أخرى."
        default:
            return "فشل الاتصال بخادم جارفس"
        }
    }

    /// يتحقق من أن جلسة Keychain ما زالت معروفة للسيرفر.
    /// 401/403 فقط تعني أن الجلسة انتهت: نمسحها ونرجع لشاشة الاقتران.
    /// أخطاء الشبكة/5xx لا تمسح الجلسة حتى لا نفصل المستخدم بسبب عطل مؤقت.
    func validateCurrentSession() async {
        guard let token = sessionToken, !token.isEmpty else { return }
        var req = URLRequest(url: baseURL.appendingPathComponent("conversations"))
        req.httpMethod = "GET"
        req.timeoutInterval = 15
        req.setValue(token, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue("PERSONAL", forHTTPHeaderField: "X-Jarvis-Workspace")
        do {
            let (_, response) = try await URLSession.shared.data(for: req)
            guard let http = response as? HTTPURLResponse else { return }
            if http.statusCode == 401 || http.statusCode == 403 {
                KeychainStore.clear()
                sessionToken = nil
                isEnrolled = false
                api = nil
                uploadManager = nil
                #if os(iOS)
                BackgroundSessionBridge.shared = nil
                #endif
                error = "انتهت جلسة جارفس. أدخل رمز الاقتران الجديد مرة واحدة."
            }
        } catch {
            // Fail open for transient connectivity only; authenticated API calls still fail closed.
        }
    }

    /// يُنشئ نفس UploadManager المستخدم في التطبيق ويربطه بـ background bridge.
    private func wire(_ token: String) {
        let um = UploadManager(baseURL: baseURL, sessionToken: token)
        uploadManager = um
        api = JarvisAPI(baseURL: baseURL, sessionToken: token)
        #if os(iOS)
        BackgroundSessionBridge.shared = um
        #endif
    }
}
