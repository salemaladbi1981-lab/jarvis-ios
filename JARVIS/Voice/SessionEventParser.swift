import Foundation

/// استخراج حقول JSON من أحداث Realtime — Foundation-only (قابل للاختبار على macOS).
enum SessionEventParser {
    static func field(_ json: String, _ key: String) -> String? {
        guard let data = json.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        return obj[key] as? String
    }

    /// استخراج حقل nested (مثل response.id من response.created / response.done).
    static func nested(_ json: String, _ key: String, _ subKey: String) -> String? {
        guard let data = json.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let nested = obj[key] as? [String: Any] else { return nil }
        return nested[subKey] as? String
    }

    static func transcript(_ json: String) -> String? {
        guard let data = json.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        // GA: transcript field مباشر
        if let t = obj["transcript"] as? String, !t.isEmpty { return t }
        // fallback: item.content
        if let item = obj["item"] as? [String: Any],
           let content = item["content"] as? [[String: Any]] {
            for c in content where (c["type"] as? String) == "input_text" || (c["type"] as? String) == "text" {
                if let t = c["text"] as? String { return t }
            }
        }
        return nil
    }
}
