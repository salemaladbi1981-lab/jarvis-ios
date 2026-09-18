import Foundation

/// Enrollment flow: one-time pairing code → POST /auth/enroll → session_token → Keychain.
@MainActor
final class EnrollmentManager: ObservableObject {
    @Published var sessionToken: String?
    @Published var isEnrolled = false
    @Published var error: String?

    let baseURL: URL

    init(baseURL: URL) {
        self.baseURL = baseURL
        self.sessionToken = KeychainStore.load()
        self.isEnrolled = sessionToken != nil
    }

    /// يُدخل الرمز → يستلم token → يخزّنه في Keychain.
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
            sessionToken = token
            isEnrolled = true
            return true
        } catch {
            error = "فشل الاتصال"
            return false
        }
    }
}
