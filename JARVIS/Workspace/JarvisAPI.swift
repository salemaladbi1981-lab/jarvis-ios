import Foundation

/// عميل API موحّد — كل الطلبات تحمل session token موثّقًا (لا user_id من العميل).
struct JarvisAPI {
    let baseURL: URL
    let sessionToken: String

    func get(_ path: String) async throws -> [[String: Any]] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [[String: Any]]) ?? []
    }

    func post(_ path: String, body: [String: Any]) async throws -> [String: Any] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }

    func download(_ path: String) async throws -> (URL, String) {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        let (tmp, resp) = try await URLSession.shared.download(for: req)
        let name = (resp as? HTTPURLResponse)?.suggestedFilename ?? "file"
        return (tmp, name)
    }
}
