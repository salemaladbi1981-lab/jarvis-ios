import Foundation

/// The same authenticated, workspace-scoped transport is used for JSON and chat.
struct JarvisAPI {
    let baseURL: URL
    let sessionToken: String
    var workspace: String = "PERSONAL"
    var session: URLSession = .shared

    func request(_ path: String, method: String = "GET", body: [String: Any]? = nil) throws -> URLRequest {
        guard !sessionToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw JarvisAPIError.authentication
        }
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        req.timeoutInterval = 90
        req.setValue(sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        return req
    }

    static func validate(_ response: URLResponse) throws {
        guard let response = response as? HTTPURLResponse else { throw JarvisAPIError.invalidResponse }
        switch response.statusCode {
        case 200..<300: return
        case 401: throw JarvisAPIError.authentication
        case 403: throw JarvisAPIError.forbidden
        case 404: throw JarvisAPIError.notFound
        case 409: throw JarvisAPIError.conflict
        case 429: throw JarvisAPIError.rateLimited
        case 500...599: throw JarvisAPIError.server
        default: throw JarvisAPIError.invalidResponse
        }
    }

    private func data(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> Data {
        let req = try request(path, method: method, body: body)
        let (data, response) = try await session.data(for: req)
        try Self.validate(response)
        return data
    }

    func get(_ path: String) async throws -> [[String: Any]] {
        let data = try await data(path)
        guard let value = try JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
            throw JarvisAPIError.invalidResponse
        }
        return value
    }

    func post(_ path: String, body: [String: Any]) async throws -> [String: Any] {
        let data = try await data(path, method: "POST", body: body)
        guard let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw JarvisAPIError.invalidResponse
        }
        return value
    }

    func download(_ path: String) async throws -> (URL, String) {
        let (url, response) = try await session.download(for: request(path))
        do { try Self.validate(response) }
        catch { try? FileManager.default.removeItem(at: url); throw error }
        return (url, response.suggestedFilename ?? "file")
    }

    func getArray<T: Decodable>(_ path: String) async throws -> [T] {
        try await getObject(path)
    }

    func getObject<T: Decodable>(_ path: String) async throws -> T {
        try JarvisJSON.decoder().decode(T.self, from: await data(path))
    }

    func fetchData(_ path: String) async throws -> Data { try await data(path) }

    func postObject<T: Decodable>(_ path: String, body: [String: Any]) async throws -> T {
        try JarvisJSON.decoder().decode(T.self, from: await data(path, method: "POST", body: body))
    }
}

enum JarvisAPIError: Error, LocalizedError, Equatable {
    case authentication, forbidden, notFound, conflict, rateLimited, server, invalidResponse, interrupted

    var errorDescription: String? {
        switch self {
        case .authentication: return "انتهت جلسة الاتصال. أعد ربط جارفس من إعدادات الاتصال."
        case .forbidden: return "لا تملك هذه الجلسة صلاحية الوصول إلى مساحة العمل."
        case .notFound: return "لم يعد هذا العنصر متاحًا. حدّث القائمة وأعد المحاولة."
        case .conflict: return "الطلب قيد التنفيذ بالفعل. انتظر ثم حدّث المحادثة."
        case .rateLimited: return "طلبات كثيرة حاليًا. انتظر قليلًا ثم أعد المحاولة."
        case .server: return "الخادم غير متاح مؤقتًا. أعد المحاولة بعد قليل."
        case .invalidResponse: return "تعذّر قراءة استجابة الخادم. حدّث المحادثة أو أعد المحاولة."
        case .interrupted: return "انقطع الرد قبل اكتماله. أعد الاتصال لاستعادة نتيجة الطلب."
        }
    }

    static func message(for error: Error) -> String {
        if let error = error as? JarvisAPIError { return error.localizedDescription }
        if let error = error as? URLError {
            switch error.code {
            case .timedOut: return "انتهت مهلة الاتصال. أعد المحاولة لاستعادة نتيجة الطلب."
            case .notConnectedToInternet, .networkConnectionLost, .cannotFindHost, .cannotConnectToHost:
                return "لا يوجد اتصال بالخادم. تحقق من الشبكة ثم أعد المحاولة."
            case .cancelled: return "توقف الاتصال. يمكنك استعادة المحادثة عند العودة."
            default: return "تعذّر الاتصال الآمن بالخادم. تحقق من الشبكة وأعد المحاولة."
            }
        }
        return JarvisAPIError.invalidResponse.localizedDescription
    }
}
