import Foundation
import CryptoKit

/// حالة رفع تُخزَّن محليًا للاستئناف بعد انقطاع الشبكة أو إعادة فتح التطبيق.
struct UploadState: Codable {
    let uploadID: String
    let filename: String
    let mimeType: String
    let checksum: String
    let totalParts: Int
    var uploadedParts: [Int]
}

/// Chunked + resumable upload إلى /files/upload/* — بدون Base64 عبر Realtime، مع الحفاظ على الأصل.
final class UploadManager: NSObject, ObservableObject, URLSessionDelegate {
    @Published var progress: Double = 0
    @Published var isUploading = false
    @Published var error: String?

    private let partSize = 4 * 1024 * 1024
    let baseURL: URL
    let userID: String
    let sessionToken: String

    /// Background URLSession — يُكمل الرفع بعد خروج التطبيق.
    private lazy var backgroundSession: URLSession = {
        let cfg = URLSessionConfiguration.background(withIdentifier: "com.jarvis.upload")
        cfg.isDiscretionary = false
        cfg.sessionSendsLaunchEvents = true
        return URLSession(configuration: cfg, delegate: self, delegateQueue: nil)
    }()

    init(baseURL: URL, userID: String, sessionToken: String) {
        self.baseURL = baseURL
        self.userID = userID
        self.sessionToken = sessionToken
    }

    static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    // ---- استمرار الحالة محليًا ----
    private func stateKey(_ checksum: String) -> String { "upload.state.\(checksum)" }
    private func loadState(_ checksum: String) -> UploadState? {
        guard let d = UserDefaults.standard.data(forKey: stateKey(checksum)),
              let s = try? JSONDecoder().decode(UploadState.self, from: d) else { return nil }
        return s
    }
    private func saveState(_ s: UploadState) {
        if let d = try? JSONEncoder().encode(s) {
            UserDefaults.standard.set(d, forKey: stateKey(s.checksum))
        }
    }
    private func clearState(_ checksum: String) {
        UserDefaults.standard.removeObject(forKey: stateKey(checksum))
    }

    /// يرفع ملفًا ويُرجع file_id. يستأنف نفس upload_id إن وُجدت حالة سابقة بنفس البصمة.
    func upload(_ data: Data, filename: String, mimeType: String, conversationID: String, sessionID: String) async throws -> String {
        await MainActor.run { isUploading = true; progress = 0; error = nil }
        defer { Task { @MainActor in isUploading = false } }

        let checksum = Self.sha256(data)
        let totalParts = max(1, (data.count + partSize - 1) / partSize)

        // استئناف: نبحث عن حالة سابقة بنفس البصمة
        var state: UploadState
        if let saved = loadState(checksum), saved.totalParts == totalParts {
            state = saved  // استئناف نفس upload_id
        } else {
            let initBody: [String: Any] = [
                "user_id": userID, "filename": filename, "mime_type": mimeType,
                "size": data.count, "checksum": checksum,
                "conversation_id": conversationID, "session_id": sessionID,
            ]
            let initResp: [String: Any] = try await post("/files/upload/init", body: initBody)
            guard let uploadID = initResp["upload_id"] as? String else {
                throw NSError(domain: "Upload", code: 1, userInfo: [NSLocalizedDescriptionKey: "init failed"])
            }
            state = UploadState(uploadID: uploadID, filename: filename, mimeType: mimeType,
                                checksum: checksum, totalParts: totalParts, uploadedParts: [])
        }

        let uploaded = Set(state.uploadedParts)
        for i in 0..<totalParts {
            guard !uploaded.contains(i) else { continue }
            let lo = i * partSize
            let hi = min(lo + partSize, data.count)
            let part = data.subdata(in: lo..<hi)
            let _: [String: Any] = try await postRaw("/files/upload/part?upload_id=\(state.uploadID)&part_number=\(i)", bytes: part)
            state.uploadedParts.append(i)
            state.uploadedParts.sort()
            saveState(state)  // احفظ بعد كل جزء — استئناف آمن
            await MainActor.run { progress = Double(i + 1) / Double(totalParts) }
        }

        let completeResp: [String: Any] = try await post("/files/upload/complete", body: ["upload_id": state.uploadID])
        guard let fileID = (completeResp["file"] as? [String: Any])?["file_id"] as? String else {
            throw NSError(domain: "Upload", code: 2, userInfo: [NSLocalizedDescriptionKey: "complete failed"])
        }
        clearState(checksum)
        return fileID
    }

    // ---- HTTP helpers (مع session token موثّق) ----
    private func authHeaders() -> [String: String] {
        ["X-Jarvis-Session": sessionToken, "Content-Type": "application/json"]
    }
    private func post(_ path: String, body: [String: Any]) async throws -> [String: Any] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.allHTTPHeaderFields = authHeaders()
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }
    private func postRaw(_ path: String, bytes: Data) async throws -> [String: Any] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.httpBody = bytes
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }
}
