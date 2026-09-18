import Foundation
import CryptoKit

/// Chunked + resumable upload إلى /files/upload/* — بدون Base64 عبر Realtime، مع الحفاظ على الأصل.
final class UploadManager: ObservableObject {
    @Published var progress: Double = 0
    @Published var isUploading = false
    @Published var error: String?

    private let partSize = 4 * 1024 * 1024
    let baseURL: URL
    let userID: String

    init(baseURL: URL, userID: String) {
        self.baseURL = baseURL
        self.userID = userID
    }

    static func sha256(_ data: Data) -> String {
        let d = SHA256.hash(data: data)
        return d.map { String(format: "%02x", $0) }.joined()
    }

    /// يرفع ملفًا ويُرجع file_id. يُستأنف تلقائيًا (يرفع الأجزاء الناقصة فقط) عند إعادة المحاولة.
    func upload(_ data: Data, filename: String, mimeType: String, conversationID: String, sessionID: String) async throws -> String {
        await MainActor.run { isUploading = true; progress = 0; error = nil }
        defer { Task { @MainActor in isUploading = false } }

        let checksum = Self.sha256(data)
        let initBody: [String: Any] = [
            "user_id": userID, "filename": filename, "mime_type": mimeType,
            "size": data.count, "checksum": checksum,
            "conversation_id": conversationID, "session_id": sessionID,
        ]
        let initResp: [String: Any] = try await post("/files/upload/init", body: initBody)
        guard let uploadID = initResp["upload_id"] as? String,
              let totalParts = initResp["total_parts"] as? Int else {
            throw NSError(domain: "Upload", code: 1, userInfo: [NSLocalizedDescriptionKey: "init failed"])
        }

        // استعلام الحالة (للاستئناف: نرفع الأجزاء الناقصة فقط)
        var uploaded = Set<Int>()
        if let st: [String: Any] = try? await get("/files/upload/\(uploadID)/status"),
           let done = st["uploaded_parts"] as? [Int] {
            uploaded = Set(done)
        }

        for i in 0..<totalParts {
            guard !uploaded.contains(i) else { continue }
            let lo = i * partSize
            let hi = min(lo + partSize, data.count)
            let part = data.subdata(in: lo..<hi)
            let _: [String: Any] = try await postRaw("/files/upload/part?upload_id=\(uploadID)&part_number=\(i)", bytes: part)
            await MainActor.run { progress = Double(i + 1) / Double(totalParts) }
        }

        let completeResp: [String: Any] = try await post("/files/upload/complete", body: ["upload_id": uploadID])
        guard let fileID = (completeResp["file"] as? [String: Any])?["file_id"] as? String else {
            throw NSError(domain: "Upload", code: 2, userInfo: [NSLocalizedDescriptionKey: "complete failed"])
        }
        return fileID
    }

    private func post(_ path: String, body: [String: Any]) async throws -> [String: Any] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }
    private func get(_ path: String) async throws -> [String: Any] {
        let (d, _) = try await URLSession.shared.data(from: baseURL.appendingPathComponent(path))
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }
    private func postRaw(_ path: String, bytes: Data) async throws -> [String: Any] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.httpBody = bytes
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }
}
