import Foundation
import CryptoKit

/// حالة رفع تُخزَّن محليًا للاستئناف + state restoration بعد relaunch.
struct UploadState: Codable {
    let uploadID: String
    let filename: String
    let mimeType: String
    let checksum: String
    let totalParts: Int
    var uploadedParts: [Int]
}

/// Chunked + resumable upload. الأجزاء تُرفع عبر backgroundSession فعليًا
/// (uploadTask from file) وتُكمل بعد خروج التطبيق + state restoration.
final class UploadManager: NSObject, ObservableObject, URLSessionDelegate, URLSessionTaskDelegate {
    @Published var progress: Double = 0
    @Published var isUploading = false

    private let partSize = 4 * 1024 * 1024
    let baseURL: URL
    let sessionToken: String

    /// backgroundSession حقيقي — يُستخدم لرفع الأجزاء (وليس URLSession.shared).
    private lazy var backgroundSession: URLSession = {
        let cfg = URLSessionConfiguration.background(withIdentifier: "com.jarvis.upload")
        cfg.isDiscretionary = false
        cfg.sessionSendsLaunchEvents = true
        return URLSession(configuration: cfg, delegate: self, delegateQueue: nil)
    }()

    private var uploadCompletion: ((Result<String, Error>) -> Void)?
    private var pendingParts = 0
    private var activeState: UploadState?
    private var partData: Data?  // للاستئناف: البيانات الكاملة في الذاكرة

    init(baseURL: URL, sessionToken: String) {
        self.baseURL = baseURL
        self.sessionToken = sessionToken
    }

    static func sha256(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    // ---- استمرار الحالة ----
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
    private func clearState(_ checksum: String) { UserDefaults.standard.removeObject(forKey: stateKey(checksum)) }

    /// يرفع ملفًا. الأجزاء عبر backgroundSession. completion يُستدعى عند ready.
    func upload(_ data: Data, filename: String, mimeType: String, conversationID: String, sessionID: String,
                completion: @escaping (Result<String, Error>) -> Void) {
        let checksum = Self.sha256(data)
        let totalParts = max(1, (data.count + partSize - 1) / partSize)
        partData = data
        uploadCompletion = completion
        Task { @MainActor in isUploading = true; progress = 0 }

        // init (foreground سريع)
        var initReq = URLRequest(url: baseURL.appendingPathComponent("/files/upload/init"))
        initReq.httpMethod = "POST"
        initReq.setValue("application/json", forHTTPHeaderField: "Content-Type")
        initReq.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        let body: [String: Any] = ["filename": filename, "mime_type": mimeType,
                                   "size": data.count, "checksum": checksum,
                                   "conversation_id": conversationID, "session_id": sessionID]
        initReq.httpBody = try? JSONSerialization.data(withJSONObject: body)
        URLSession.shared.dataTask(with: initReq) { [weak self] d, _, err in
            guard let self else { return }
            if let d, let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
               let uploadID = obj["upload_id"] as? String {
                var state = self.loadState(checksum)
                if state == nil {
                    state = UploadState(uploadID: uploadID, filename: filename, mimeType: mimeType,
                                        checksum: checksum, totalParts: totalParts, uploadedParts: [])
                }
                self.activeState = state
                self.enqueueMissingParts(state!, data: data)
            } else {
                completion(.failure(err ?? NSError(domain: "Upload", code: 1)))
            }
        }.resume()
    }

    /// يُرسل الأجزاء الناقصة عبر backgroundSession (uploadTask from file).
    private func enqueueMissingParts(_ state: UploadState, data: Data) {
        let uploaded = Set(state.uploadedParts)
        var missing: [Int] = []
        for i in 0..<state.totalParts where !uploaded.contains(i) { missing.append(i) }
        pendingParts = missing.count
        for i in missing {
            let lo = i * partSize
            let hi = min(lo + partSize, data.count)
            let part = data.subdata(in: lo..<hi)
            let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("part-\(i)-\(UUID().uuidString)")
            try? part.write(to: tmp)
            var req = URLRequest(url: baseURL.appendingPathComponent("/files/upload/part?upload_id=\(state.uploadID)&part_number=\(i)"))
            req.httpMethod = "POST"
            req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
            backgroundSession.uploadTask(with: req, fromFile: tmp).resume()
        }
        if pendingParts == 0 { finishUpload(state) }
    }

    /// completion handling — يُستدعى لكل part (أيضًا بعد relaunch لـ restored tasks).
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard error == nil, let state = activeState ?? resumeActiveState() else { return }
        // احفظ هذا الجزء كـ uploaded
        if let idx = parsePartNumber(from: task.originalRequest?.url), !state.uploadedParts.contains(idx) {
            state.uploadedParts.append(idx); state.uploadedParts.sort()
            saveState(state)
            Task { @MainActor in
                self.progress = Double(state.uploadedParts.count) / Double(state.totalParts)
            }
        }
        pendingParts = max(0, pendingParts - 1)
        if pendingParts == 0 { finishUpload(state) }
    }

    private func finishUpload(_ state: UploadState) {
        var req = URLRequest(url: baseURL.appendingPathComponent("/files/upload/complete"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["upload_id": state.uploadID])
        URLSession.shared.dataTask(with: req) { [weak self] d, _, err in
            guard let self else { return }
            Task { @MainActor in self.isUploading = false }
            if let d, let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
               let file = obj["file"] as? [String: Any], let id = file["file_id"] as? String {
                self.clearState(state.checksum)
                self.uploadCompletion?(.success(id))
            } else {
                self.uploadCompletion?(.failure(err ?? NSError(domain: "Upload", code: 2)))
            }
            self.uploadCompletion = nil
        }.resume()
    }

    /// state restoration: بعد relaunch نسترجع نفس upload_id من الحالة المحفوظة.
    private func resumeActiveState() -> UploadState? {
        let all = UserDefaults.standard.dictionaryRepresentation()
        for (k, v) in all where k.hasPrefix("upload.state.") {
            if let d = v as? Data, let s = try? JSONDecoder().decode(UploadState.self, from: d) {
                return s
            }
        }
        return nil
    }

    private func parsePartNumber(from url: URL?) -> Int? {
        guard let comps = URLComponents(url: url ?? URL(string: "/")!, resolvingAgainstBaseURL: false),
              let n = comps.queryItems?.first(where: { $0.name == "part_number" })?.value else { return nil }
        return Int(n)
    }
}
