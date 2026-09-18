import Foundation
import CryptoKit

struct UploadState: Codable {
    let uploadID: String
    let filename: String
    let mimeType: String
    let checksum: String
    let totalParts: Int
    var uploadedParts: [Int]
    let sourcePath: String   // الملف الأصلي على القرص (لا يعتمد على الذاكرة)
}

/// رفع chunked/resumable عبر backgroundSession فعليًا.
/// السيرفر هو مصدر الحقيقة للأجزاء المرفوعة (GET status) — لا نعتمد على counter في الذاكرة.
final class UploadManager: NSObject, ObservableObject, URLSessionDelegate, URLSessionTaskDelegate {
    @Published var progress: Double = 0
    @Published var isUploading = false

    private let partSize = 4 * 1024 * 1024
    let baseURL: URL
    let sessionToken: String
    private var backgroundCompletionHandler: (() -> Void)?
    private var continuations: [String: CheckedContinuation<String, Error>] = [:]

    private lazy var backgroundSession: URLSession = {
        let cfg = URLSessionConfiguration.background(withIdentifier: "com.jarvis.upload")
        cfg.isDiscretionary = false
        cfg.sessionSendsLaunchEvents = true
        return URLSession(configuration: cfg, delegate: self, delegateQueue: nil)
    }()

    init(baseURL: URL, sessionToken: String) {
        self.baseURL = baseURL
        self.sessionToken = sessionToken
    }

    static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    // ---- استمرار ----
    private func stateKey(_ checksum: String) -> String { "upload.state.\(checksum)" }
    private func saveState(_ s: UploadState) {
        if let d = try? JSONEncoder().encode(s) { UserDefaults.standard.set(d, forKey: stateKey(s.checksum)) }
    }
    private func loadState(_ checksum: String) -> UploadState? {
        guard let d = UserDefaults.standard.data(forKey: stateKey(checksum)),
              let s = try? JSONDecoder().decode(UploadState.self, from: d) else { return nil }
        return s
    }
    private func allPersistedStates() -> [UploadState] {
        UserDefaults.standard.dictionaryRepresentation().compactMap { k, v in
            guard k.hasPrefix("upload.state."), let d = v as? Data,
                  let s = try? JSONDecoder().decode(UploadState.self, from: d) else { return nil }
            return s
        }
    }
    private func clearState(_ checksum: String) { UserDefaults.standard.removeObject(forKey: stateKey(checksum)) }

    /// source على القرص (يبقى بعد relaunch)
    private func sourceDir(_ checksum: String) -> URL {
        let d = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("uploads/\(checksum)", isDirectory: true)
        try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
        return d
    }

    // ---- بدء الرفع ----
    func upload(_ data: Data, filename: String, mimeType: String, conversationID: String, sessionID: String) {
        let checksum = Self.sha256(data)
        let totalParts = max(1, (data.count + partSize - 1) / partSize)

        // حفظ الملف الأصلي على القرص (للاستئناف بعد relaunch)
        let src = sourceDir(checksum).appendingPathComponent("original.bin")
        try? data.write(to: src)

        // init (foreground سريع)
        var req = URLRequest(url: baseURL.appendingPathComponent("/files/upload/init"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.httpBody = try? JSONSerialization.data(withJSONObject: [
            "filename": filename, "mime_type": mimeType, "size": data.count,
            "checksum": checksum, "conversation_id": conversationID, "session_id": sessionID,
        ])
        URLSession.shared.dataTask(with: req) { [weak self] d, _, _ in
            guard let self, let d,
                  let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
                  let uploadID = obj["upload_id"] as? String else { return }
            let state = self.loadState(checksum) ?? UploadState(
                uploadID: uploadID, filename: filename, mimeType: mimeType, checksum: checksum,
                totalParts: totalParts, uploadedParts: [], sourcePath: src.path)
            self.saveState(state)
            Task { @MainActor in self.isUploading = true }
            self.syncParts(state)
        }.resume()
    }

    /// السيرفر مصدر الحقيقة: نستعلم الأجزاء المرفوعة، نرفع الناقص، ونكمل فقط عند الاكتمال.
    private func syncParts(_ state: UploadState) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/files/upload/\(state.uploadID)/status"))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        URLSession.shared.dataTask(with: req) { [weak self] d, _, _ in
            guard let self, let d,
                  let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] else { return }
            let uploaded = Set((obj["uploaded_parts"] as? [Int]) ?? [])
            var s = state
            s.uploadedParts = uploaded.sorted()
            self.saveState(s)

            if uploaded.count >= state.totalParts {
                self.complete(s)   // كل الأجزاء موجودة فعليًا عند السيرفر
                return
            }
            // رفع الأجزاء الناقصة (عبر backgroundSession)
            guard let data = try? Data(contentsOf: URL(fileURLWithPath: state.sourcePath)) else { return }
            for i in 0..<state.totalParts where !uploaded.contains(i) {
                let lo = i * self.partSize
                let hi = min(lo + self.partSize, data.count)
                let part = data.subdata(in: lo..<hi)
                let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("part-\(i)-\(UUID().uuidString)")
                try? part.write(to: tmp)
                var pr = URLRequest(url: self.baseURL.appendingPathComponent("/files/upload/part?upload_id=\(state.uploadID)&part_number=\(i)"))
                pr.httpMethod = "POST"
                pr.setValue(self.sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
                self.backgroundSession.uploadTask(with: pr, fromFile: tmp).resume()
            }
        }.resume()
    }

    /// completion handling لكل part — نتحقق من HTTP success ثم نعيد المزامنة من السيرفر.
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        // HTTP success؟
        if let resp = task.response as? HTTPURLResponse, !(200..<300).contains(resp.statusCode) {
            return  // فشل — لا نعتبر الجزء uploaded
        }
        guard error == nil else { return }
        // بعد أي نجاح نعيد المزامنة من السيرفر (يقرر هل نكمل أم نرفع ناقصًا)
        let states = allPersistedStates()
        for s in states { syncParts(s) }
    }

    private func complete(_ state: UploadState) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/files/upload/complete"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["upload_id": state.uploadID])
        URLSession.shared.dataTask(with: req) { [weak self] data, resp, error in
            guard let self else { return }
            // النجاح فقط إذا: HTTP 2xx + ok == true + file_id موجود (تأكيد فعلي)
            var success = false
            var fileID: String?
            if error == nil,
               let r = resp as? HTTPURLResponse, (200..<300).contains(r.statusCode),
               let d = data,
               let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
               (obj["ok"] as? Bool) == true {
                fileID = obj["file_id"] as? String ?? (obj["file"] as? [String: Any])?["file_id"] as? String
                success = fileID != nil
            }
            if success, let fid = fileID {
                self.clearState(state.checksum)
                Task { @MainActor in self.isUploading = false; self.progress = 1.0 }
                if let cont = self.continuations.removeValue(forKey: state.checksum) {
                    cont.resume(returning: fid)
                }
            } else if error == nil {
                // استجابة رفض (ok=false أو لا file_id) → فشل مؤكد، state تبقى، resume error
                if let cont = self.continuations.removeValue(forKey: state.checksum) {
                    cont.resume(throwing: NSError(domain: "Upload", code: 3, userInfo: [NSLocalizedDescriptionKey: "complete failed"]))
                }
            }
            // network error (error != nil بلا response) → لا نستأنف، retry لاحقًا عبر restoreOnLaunch/syncParts
        }.resume()
    }

    /// state restoration بعد relaunch: أعد بناء الأجزاء الناقصة من السيرفر (وليس من الذاكرة).
    func restoreOnLaunch() {
        for s in allPersistedStates() { syncParts(s) }
    }

    /// async wrapper — يسجّل continuation ويُستأنف فقط عند نجاح /files/upload/complete.
    func uploadAsync(_ data: Data, filename: String, mimeType: String, conversationID: String, sessionID: String) async throws -> String {
        let checksum = Self.sha256(data)
        return try await withCheckedThrowingContinuation { cont in
            continuations[checksum] = cont
            upload(data, filename: filename, mimeType: mimeType, conversationID: conversationID, sessionID: sessionID)
        }
    }

    // ---- background completion handler (AppDelegate) ----
    func setBackgroundCompletionHandler(_ handler: @escaping () -> Void) {
        backgroundCompletionHandler = handler
    }
    func urlSessionDidFinishEvents(forBackgroundURLSession session: URLSession) {
        DispatchQueue.main.async { [weak self] in
            self?.backgroundCompletionHandler?()
            self?.backgroundCompletionHandler = nil
        }
    }
}
