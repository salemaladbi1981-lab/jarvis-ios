import Foundation

/// عميل API موحّد — كل الطلبات تحمل session token موثّقًا (لا user_id من العميل).
struct JarvisAPI {
    let baseURL: URL
    let sessionToken: String
    var workspace: String = "PERSONAL"

    private static let requestTimeout: TimeInterval = 45

    private func makeRequest(_ path: String, method: String = "GET", body: [String: Any]? = nil) throws -> URLRequest {
        guard !sessionToken.isEmpty else {
            throw NSError(domain: "JarvisAPI", code: 401,
                          userInfo: [NSLocalizedDescriptionKey: "Missing JARVIS session token"])
        }

        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        req.timeoutInterval = Self.requestTimeout
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")

        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        return req
    }

    @discardableResult
    private func validate(_ response: URLResponse) throws -> HTTPURLResponse {
        guard let http = response as? HTTPURLResponse else {
            throw NSError(domain: "JarvisAPI", code: -1,
                          userInfo: [NSLocalizedDescriptionKey: "Invalid HTTP response"])
        }
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "JarvisAPI", code: http.statusCode,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \(http.statusCode)"])
        }
        return http
    }

    func get(_ path: String) async throws -> [[String: Any]] {
        let req = try makeRequest(path)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(response)
        return (try JSONSerialization.jsonObject(with: data) as? [[String: Any]]) ?? []
    }

    func post(_ path: String, body: [String: Any]) async throws -> [String: Any] {
        let req = try makeRequest(path, method: "POST", body: body)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(response)
        return (try JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
    }

    func download(_ path: String) async throws -> (URL, String) {
        let req = try makeRequest(path)
        let (tmp, response) = try await URLSession.shared.download(for: req)
        let http = try validate(response)
        let name = http.suggestedFilename ?? "file"
        return (tmp, name)
    }

    /// قائمة مُفهرسة (GET /tasks, /conversations, /deliveries) → [T].
    func getArray<T: Decodable>(_ path: String) async throws -> [T] {
        let req = try makeRequest(path)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(response)
        return try JarvisJSON.decoder().decode([T].self, from: data)
    }

    /// عنصر واحد (GET /conversations/{id}) → T.
    func getObject<T: Decodable>(_ path: String) async throws -> T {
        let req = try makeRequest(path)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(response)
        return try JarvisJSON.decoder().decode(T.self, from: data)
    }

    /// بيانات خام (للصور/المرفقات) — GET /files/{id}/download.
    func fetchData(_ path: String) async throws -> Data {
        let req = try makeRequest(path)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(response)
        return data
    }

    /// POST يُرجع كائنًا (POST /conversations) → U.
    func postObject<U: Decodable>(_ path: String, body: [String: Any]) async throws -> U {
        let req = try makeRequest(path, method: "POST", body: body)
        let (data, response) = try await URLSession.shared.data(for: req)
        try validate(response)
        return try JarvisJSON.decoder().decode(U.self, from: data)
    }
}
