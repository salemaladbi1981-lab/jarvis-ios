import Foundation

/// عميل API موحّد — كل الطلبات تحمل session token موثّقًا (لا user_id من العميل).
struct JarvisAPI {
    let baseURL: URL
    let sessionToken: String
    var workspace: String = "PERSONAL"

    func get(_ path: String) async throws -> [[String: Any]] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        let (d, _) = try await URLSession.shared.data(for: req)
        return (try JSONSerialization.jsonObject(with: d) as? [[String: Any]]) ?? []
    }

    func post(_ path: String, body: [String: Any]) async throws -> [String: Any] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (d, resp) = try await URLSession.shared.data(for: req)
        if let r = resp as? HTTPURLResponse, !(200..<300).contains(r.statusCode) {
            throw NSError(domain: "JarvisAPI", code: r.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(r.statusCode)"])
        }
        return (try JSONSerialization.jsonObject(with: d) as? [String: Any]) ?? [:]
    }

    func download(_ path: String) async throws -> (URL, String) {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        let (tmp, resp) = try await URLSession.shared.download(for: req)
        let name = (resp as? HTTPURLResponse)?.suggestedFilename ?? "file"
        return (tmp, name)
    }

    /// قائمة مُفهرسة (GET /tasks, /conversations, /deliveries) → [T].
    func getArray<T: Decodable>(_ path: String) async throws -> [T] {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        let (d, resp) = try await URLSession.shared.data(for: req)
        if let r = resp as? HTTPURLResponse, !(200..<300).contains(r.statusCode) {
            throw NSError(domain: "JarvisAPI", code: r.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(r.statusCode)"])
        }
        return try JarvisJSON.decoder().decode([T].self, from: d)
    }

    /// عنصر واحد (GET /conversations/{id}) → T.
    func getObject<T: Decodable>(_ path: String) async throws -> T {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        let (d, resp) = try await URLSession.shared.data(for: req)
        if let r = resp as? HTTPURLResponse, !(200..<300).contains(r.statusCode) {
            throw NSError(domain: "JarvisAPI", code: r.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(r.statusCode)"])
        }
        return try JarvisJSON.decoder().decode(T.self, from: d)
    }

    /// بيانات خام (للصور/المرفقات) — GET /files/{id}/download.
    func fetchData(_ path: String) async throws -> Data {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        let (d, resp) = try await URLSession.shared.data(for: req)
        if let r = resp as? HTTPURLResponse, !(200..<300).contains(r.statusCode) {
            throw NSError(domain: "JarvisAPI", code: r.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(r.statusCode)"])
        }
        return d
    }

    /// POST يُرجع كائنًا (POST /conversations) → U.
    func postObject<U: Decodable>(_ path: String, body: [String: Any]) async throws -> U {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (d, resp) = try await URLSession.shared.data(for: req)
        if let r = resp as? HTTPURLResponse, !(200..<300).contains(r.statusCode) {
            throw NSError(domain: "JarvisAPI", code: r.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(r.statusCode)"])
        }
        return try JarvisJSON.decoder().decode(U.self, from: d)
    }
}
