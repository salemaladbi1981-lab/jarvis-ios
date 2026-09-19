import Foundation
import Combine

/// حالة الرد الحي (working/searching/using_tool/complete/failed/background_task).
enum ChatStatus: String {
    case idle, working, searching, usingTool, complete, failed, backgroundTask
}

struct DeltaEvent: Codable { let delta: String? }
struct ToolCallEvent: Codable { let toolName: String?; let callId: String?; let status: String? }
struct CitationEvent: Codable { let citationId: String?; let title: String?; let url: String?; let source: String?; let snippet: String? }
struct CompleteEvent: Codable { let messageId: String?; let status: String?; let taskId: String? }
struct ErrorEvent: Codable { let errorType: String?; let message: String? }

struct ConversationDetail: Codable {
    let conversation: Conversation?
    let messages: [ChatMessage]?
}

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var streamingText: String = ""
    @Published var status: ChatStatus = .idle
    @Published var statusLabel: String = ""
    @Published var liveCitations: [Citation] = []
    @Published var pendingTaskId: String?
    @Published var errorMessage: String?
    @Published var conversationId: String = ""

    private let api: JarvisAPI

    init(api: JarvisAPI) { self.api = api }

    func load(_ id: String) async {
        conversationId = id
        errorMessage = nil
        do {
            let detail: ConversationDetail = try await api.getObject("conversations/\(id)")
            messages = detail.messages ?? []
        } catch {
            errorMessage = "تعذر تحميل المحادثة"
        }
    }

    func send(_ text: String) async {
        let cid = conversationId
        guard !cid.isEmpty else { return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        let userMsg = ChatMessage(messageId: "local-\(UUID().uuidString.prefix(8))",
                                  conversationId: cid, role: "user", content: trimmed,
                                  citations: nil, toolCalls: nil, attachmentRefs: nil,
                                  taskRefs: nil, deliveryRefs: nil,
                                  executionState: nil, createdAt: Date().timeIntervalSince1970)
        messages.append(userMsg)

        streamingText = ""
        liveCitations = []
        pendingTaskId = nil
        errorMessage = nil
        status = .working
        statusLabel = "جارٍ المعالجة"

        var req = URLRequest(url: api.baseURL.appendingPathComponent("conversations/\(cid)/chat"))
        req.httpMethod = "POST"
        req.setValue(api.sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["text": trimmed])

        do {
            let (bytes, _) = try await URLSession.shared.bytes(for: req)
            var currentEvent = ""
            for try await line in bytes.lines {
                if line.hasPrefix("event: ") {
                    currentEvent = String(line.dropFirst(7))
                } else if line.hasPrefix("data: ") {
                    let payload = String(line.dropFirst(6))
                    handle(currentEvent, payload)
                }
            }
        } catch {
            status = .failed
            errorMessage = "انقطع الاتصال"
        }
    }

    private func handle(_ event: String, _ payload: String) {
        guard let data = payload.data(using: .utf8) else { return }
        switch event {
        case "message_start":
            status = .working
            statusLabel = "جارٍ المعالجة"
        case "content_delta":
            if let d = try? JSONDecoder().decode(DeltaEvent.self, from: data) {
                streamingText += d.delta ?? ""
            }
        case "tool_call":
            if let t = try? JSONDecoder().decode(ToolCallEvent.self, from: data) {
                let name = t.toolName ?? ""
                if name.lowercased().contains("search") || name.lowercased().contains("web") {
                    status = .searching; statusLabel = "يبحث"
                } else {
                    status = .usingTool; statusLabel = "يستخدم أداة"
                }
            }
        case "citation":
            if let c = try? JSONDecoder().decode(CitationEvent.self, from: data) {
                liveCitations.append(Citation(citationId: c.citationId ?? "",
                                              messageId: nil, title: c.title, url: c.url,
                                              source: c.source, snippet: c.snippet, order: nil))
            }
        case "message_complete":
            if let c = try? JSONDecoder().decode(CompleteEvent.self, from: data) {
                if c.status == "background_task" {
                    status = .backgroundTask
                    statusLabel = "انتقل إلى مهمة خلفية"
                    pendingTaskId = c.taskId
                } else {
                    finishAssistant(c)
                }
            }
        case "error":
            if let e = try? JSONDecoder().decode(ErrorEvent.self, from: data) {
                status = .failed
                errorMessage = e.message ?? "حدث خطأ"
            }
        default:
            break
        }
    }

    private func finishAssistant(_ c: CompleteEvent) {
        let content = streamingText
        let assistant = ChatMessage(messageId: c.messageId ?? "local-\(UUID().uuidString.prefix(8))",
                                    conversationId: conversationId, role: "assistant", content: content,
                                    citations: liveCitations, toolCalls: nil, attachmentRefs: nil,
                                    taskRefs: nil, deliveryRefs: nil,
                                    executionState: ExecutionState(status: "complete", error: nil),
                                    createdAt: Date().timeIntervalSince1970)
        messages.append(assistant)
        streamingText = ""
        liveCitations = []
        status = .idle
        statusLabel = ""
    }

    func retry() async {
        // يعيد آخر نص مستخدم فشل
        if let last = messages.last(where: { $0.role == "user" })?.content {
            // إزالة الرسالة الفاشلة إن وُجدت
            messages.removeAll { $0.executionState?.status == "failed" }
            await send(last)
        }
    }
}
