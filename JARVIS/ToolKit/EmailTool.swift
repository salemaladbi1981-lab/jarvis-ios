import Foundation

struct EmailMessage: Codable, Identifiable, Equatable {
    let id: String
    let from: String
    let subject: String
    let date: String
    let snippet: String
    let unread: Bool
}

enum EmailError: Error, Equatable {
    case authFailed
    case networkFailed
    case badResponse
}

/// عميل HTTP إلى backend `/email/*` — لا يحمل أي token (يُدار token سيرفراً).
struct EmailClient {
    let baseURL: String

    private func get(_ path: String, query: [String: String] = [:]) async throws -> Data {
        var comps = URLComponents(string: baseURL + path)
        if !query.isEmpty {
            comps?.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = comps?.url else { throw EmailError.badResponse }
        var req = URLRequest(url: url)
        req.timeoutInterval = 20
        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse else { throw EmailError.badResponse }
            if http.statusCode == 401 || http.statusCode == 403 { throw EmailError.authFailed }
            guard (200..<300).contains(http.statusCode) else { throw EmailError.badResponse }
            return data
        } catch let e as EmailError {
            throw e
        } catch {
            throw EmailError.networkFailed
        }
    }

    private func post(_ path: String, json: [String: Any]) async throws -> Data {
        guard let url = URL(string: baseURL + path) else { throw EmailError.badResponse }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 25
        req.httpBody = try? JSONSerialization.data(withJSONObject: json)
        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse else { throw EmailError.badResponse }
            if http.statusCode == 401 || http.statusCode == 403 { throw EmailError.authFailed }
            guard (200..<300).contains(http.statusCode) else { throw EmailError.badResponse }
            return data
        } catch let e as EmailError {
            throw e
        } catch {
            throw EmailError.networkFailed
        }
    }

    func summary(limit: Int = 10) async throws -> [EmailMessage] {
        let data = try await get("/email/summary", query: ["limit": String(limit)])
        struct R: Codable { let emails: [EmailMessage]? }
        return (try? JSONDecoder().decode(R.self, from: data))?.emails ?? []
    }

    func search(q: String, limit: Int = 20) async throws -> [EmailMessage] {
        let data = try await get("/email/search", query: ["q": q, "limit": String(limit)])
        struct R: Codable { let emails: [EmailMessage]? }
        return (try? JSONDecoder().decode(R.self, from: data))?.emails ?? []
    }

    func read(id: String) async throws -> EmailMessage {
        let data = try await get("/email/read", query: ["id": id])
        struct R: Codable { let message: EmailMessageBody? }
        struct EmailMessageBody: Codable {
            let id: String; let from: String; let subject: String; let date: String; let body: String
        }
        guard let m = (try? JSONDecoder().decode(R.self, from: data))?.message else {
            throw EmailError.badResponse
        }
        return EmailMessage(id: m.id, from: m.from, subject: m.subject, date: m.date,
                            snippet: m.body, unread: false)
    }

    func send(to: String, subject: String, body: String) async throws -> Bool {
        let data = try await post("/email/send", json: ["to": to, "subject": subject, "body": body])
        if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return (obj["ok"] as? Bool) ?? false
        }
        return false
    }
}

/// أداة البريد — تكتشف intent، تطلب تأكيداً للإرسال فقط، تنفّذ عبر الـ backend.
final class EmailTool: Tool {
    let client: EmailClient
    /// آخر رسالة تفاعل معها المالك (لسياق «رد عليه»).
    private(set) var lastMessage: EmailMessage?

    init(client: EmailClient) { self.client = client }

    func detectIntent(from transcript: String) -> ToolIntent {
        let t = transcript.lowercased()
        // ردّ (يتطلب نص الرد)
        if t.contains("رد") || t.contains("reply") {
            if let body = Self.extractReplyBody(t) { return .emailReply(body: body) }
        }
        // قراءة رسالة
        if t.contains("اقرأ") || t.contains("افتح") || t.contains("read") {
            if Self.isEmail(t) { return .emailRead }
        }
        // بحث
        if t.contains("ابحث") || t.contains("بحث") || t.contains("search") {
            if Self.isEmail(t) { return .emailSearch(query: t) }
        }
        // ملخّص / أهم الرسائل
        if Self.isEmail(t) { return .emailSummary }
        return .none
    }

    func confirmation(for intent: ToolIntent) -> ConfirmationRequirement {
        switch intent {
        case .emailReply(let body):
            return .confirm(description: "إرسال رد:\n\(body)")
        default:
            return .none
        }
    }

    func execute(_ intent: ToolIntent) async -> ToolResult {
        switch intent {
        case .emailSummary:
            do {
                let emails = try await client.summary(limit: 8)
                guard !emails.isEmpty else { return .success(message: "لا توجد إيميلات حديثة.") }
                lastMessage = emails.first
                let lines = emails.prefix(5).map { e in
                    let flag = e.unread ? "جديد" : "مقروء"
                    return "• [\(flag)] \(e.from) — \(e.subject)"
                }
                return .success(message: "أهم الإيميلات:\n" + lines.joined(separator: "\n"))
            } catch let e as EmailError {
                return Self.failure(for: e)
            } catch {
                return .failure(reason: "تعذّر جلب البريد")
            }
        case .emailRead:
            guard let last = lastMessage else {
                return .failure(reason: "لم تحدد رسالة بعد — اطلب الملخص أولاً")
            }
            do {
                let m = try await client.read(id: last.id)
                return .success(message: "من \(m.from)\nالموضوع: \(m.subject)\n\n\(String(m.snippet.prefix(600)))")
            } catch let e as EmailError {
                return Self.failure(for: e)
            } catch {
                return .failure(reason: "تعذّرت قراءة الرسالة")
            }
        case .emailSearch(let query):
            do {
                let emails = try await client.search(q: query)
                guard !emails.isEmpty else { return .success(message: "لا نتائج للبحث.") }
                let lines = emails.prefix(5).map { "• \($0.from) — \($0.subject)" }
                return .success(message: "نتائج البحث:\n" + lines.joined(separator: "\n"))
            } catch let e as EmailError {
                return Self.failure(for: e)
            } catch {
                return .failure(reason: "تعذّر البحث")
            }
        case .emailReply(let body):
            guard let last = lastMessage else {
                return .failure(reason: "لا توجد رسالة للرد عليها")
            }
            let to = last.from
            let subject = last.subject.hasPrefix("Re:") ? last.subject : "Re: " + last.subject
            do {
                let sent = try await client.send(to: to, subject: subject, body: body)
                return sent ? .success(message: "أُرسل الرد إلى \(to)") : .failure(reason: "فشل الإرسال")
            } catch let e as EmailError {
                return Self.failure(for: e)
            } catch {
                return .failure(reason: "تعذّر الإرسال")
            }
        case .none:
            return .failure(reason: "لا شيء")
        }
    }

    /// بعد عرض ملخّص، يتذكر أول رسالة كمؤشر للقراءة/الرد.
    func rememberFirst(from messages: [EmailMessage]) {
        lastMessage = messages.first
    }

    private static func failure(for e: EmailError) -> ToolResult {
        switch e {
        case .authFailed: return .failure(reason: "تعذّر التوثيق مع البريد — راجع صلاحيات Gmail")
        case .networkFailed: return .failure(reason: "تعذّر الوصول للشبكة")
        case .badResponse: return .failure(reason: "استجابة بريد غير صالحة")
        }
    }

    private static func isEmail(_ t: String) -> Bool {
        ["إيميل", "ايميل", "بريد", "رسائل", "رسالة", "email", "mail", "inbox"].contains { t.contains($0) }
    }

    private static func extractReplyBody(_ t: String) -> String? {
        let markers = ["بـ", "وقله", "قله", "قل له", "ب "]
        for m in markers {
            if let r = t.range(of: m) {
                let rest = String(t[r.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
                if !rest.isEmpty { return rest }
            }
        }
        return nil
    }
}
