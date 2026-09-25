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

    @Published private(set) var isSending = false
    @Published private(set) var isLoading = false
    private var pendingText: String?
    private var pendingRequestID: String?
    private var terminalReceived = false
    private let api: JarvisAPI

    init(api: JarvisAPI) { self.api = api }

    func load(_ id: String) async {
        guard !isSending, !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        if conversationId != id {
            pendingText = nil
            pendingRequestID = nil
            messages = []
        }
        conversationId = id
        errorMessage = nil
        do {
            let detail: ConversationDetail = try await api.getObject("conversations/\(id)")
            messages = detail.messages ?? []
        } catch {
            errorMessage = JarvisAPIError.message(for: error)
        }
    }

    func send(_ text: String) async {
        guard !isSending, !isLoading else { return }
        let cid = conversationId
        guard !cid.isEmpty else { errorMessage = "افتح محادثة أولًا."; return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        pendingText = trimmed
        pendingRequestID = UUID().uuidString
        let userMsg = ChatMessage(messageId: "local-\(UUID().uuidString.prefix(8))",
                                  conversationId: cid, role: "user", content: trimmed,
                                  citations: nil, toolCalls: nil, attachmentRefs: nil,
                                  taskRefs: nil, deliveryRefs: nil,
                                  executionState: nil, createdAt: Date().timeIntervalSince1970)
        messages.append(userMsg)

        await transmit()
    }

    private func transmit() async {
        guard !isSending, let text = pendingText, let requestID = pendingRequestID else { return }
        isSending = true
        defer { isSending = false }
        streamingText = ""
        liveCitations = []
        pendingTaskId = nil
        errorMessage = nil
        terminalReceived = false
        status = .working
        statusLabel = "جارٍ المعالجة"
        do {
            var req = try api.request("conversations/\(conversationId)/chat", method: "POST",
                                      body: ["text": text, "client_msg_id": requestID])
            req.setValue("text/event-stream", forHTTPHeaderField: "Accept")
            let (bytes, response) = try await api.session.bytes(for: req)
            try JarvisAPI.validate(response)
            guard response.mimeType == "text/event-stream" else { throw JarvisAPIError.invalidResponse }
            var parser = ChatEventParser()
            for try await byte in bytes {
                try Task.checkCancellation()
                if let event = try parser.consume(byte) { handle(event.name, event.payload) }
                if terminalReceived { break }
            }
            if !terminalReceived, let event = parser.finishStream() { handle(event.name, event.payload) }
            guard terminalReceived else { throw JarvisAPIError.interrupted }
        } catch {
            status = .failed
            statusLabel = "تعذّر إكمال الرد"
            errorMessage = JarvisAPIError.message(for: error)
        }
    }

    private func handle(_ event: String, _ payload: String) {
        guard !terminalReceived, let data = payload.data(using: .utf8) else { return }
        switch event {
        case "message_start":
            status = .working
            statusLabel = "جارٍ المعالجة"
        case "content_delta":
            if let d = try? JarvisJSON.decoder().decode(DeltaEvent.self, from: data) {
                streamingText += d.delta ?? ""
            }
        case "tool_call":
            if let t = try? JarvisJSON.decoder().decode(ToolCallEvent.self, from: data) {
                let name = t.toolName ?? ""
                if name.lowercased().contains("search") || name.lowercased().contains("web") {
                    status = .searching; statusLabel = "يبحث"
                } else {
                    status = .usingTool; statusLabel = "يستخدم أداة"
                }
            }
        case "citation":
            if let c = try? JarvisJSON.decoder().decode(CitationEvent.self, from: data) {
                liveCitations.append(Citation(citationId: c.citationId ?? "",
                                              messageId: nil, title: c.title, url: c.url,
                                              source: c.source, snippet: c.snippet, order: nil))
            }
        case "message_complete":
            if let c = try? JarvisJSON.decoder().decode(CompleteEvent.self, from: data) {
                guard c.status == "complete" || c.status == "background_task" else { return }
                terminalReceived = true
                pendingText = nil
                pendingRequestID = nil
                if c.status == "background_task" {
                    status = .backgroundTask
                    statusLabel = "انتقل إلى مهمة خلفية"
                    pendingTaskId = c.taskId
                    #if os(iOS)
                    if let tid = c.taskId {
                        NotificationManager.shared.notifyTaskHandoff(tid)
                    }
                    #endif
                } else {
                    finishAssistant(c)
                }
            }
        case "error":
            if let e = try? JarvisJSON.decoder().decode(ErrorEvent.self, from: data) {
                terminalReceived = true
                status = .failed
                statusLabel = "تعذّر إكمال الرد"
                switch e.errorType {
                case "auth_error": errorMessage = JarvisAPIError.forbidden.localizedDescription
                case "request_in_progress": errorMessage = JarvisAPIError.conflict.localizedDescription
                case "request_interrupted": errorMessage = "توقف الطلب بعد قبوله. راجع المحادثة قبل إرسال طلب جديد."
                default: errorMessage = "تعذّر إكمال الطلب على الخادم. راجع المحادثة ثم حاول مجددًا."
                }
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
        if !messages.contains(where: { $0.id == assistant.id }) { messages.append(assistant) }
        streamingText = ""
        liveCitations = []
        status = .idle
        statusLabel = ""
    }

    func retry() async {
        guard !isSending, !isLoading else { return }
        if pendingRequestID != nil { await transmit() }
        else { await load(conversationId) }
    }
}

/// SSE fields may omit a space; multiline data is joined at a frame boundary.
struct ChatEventParser {
    struct Event { let name: String; let payload: String }
    private var name = ""
    private var lines: [String] = []
    private var lineBytes: [UInt8] = []
    private var skipLF = false
    private var frameBytes = 0

    // AsyncBytes.lines drops empty lines on some Foundation versions. SSE needs
    // those delimiters, so decode UTF-8 only after assembling each complete line.
    mutating func consume(_ byte: UInt8) throws -> Event? {
        if skipLF { skipLF = false; if byte == 10 { return nil } }
        frameBytes += 1
        guard frameBytes <= 1_048_576 else { throw JarvisAPIError.invalidResponse }
        if byte == 10 || byte == 13 {
            skipLF = byte == 13
            let line = String(decoding: lineBytes, as: UTF8.self)
            lineBytes = []
            return consume(line)
        }
        lineBytes.append(byte)
        return nil
    }

    mutating func finishStream() -> Event? {
        if !lineBytes.isEmpty {
            let line = String(decoding: lineBytes, as: UTF8.self)
            lineBytes = []
            if let event = consume(line) { return event }
        }
        return finish()
    }

    mutating func consume(_ line: String) -> Event? {
        if line.isEmpty { return finish() }
        if line.hasPrefix(":") { return nil }
        let fields = line.split(separator: ":", maxSplits: 1, omittingEmptySubsequences: false)
        let field = String(fields[0])
        var value = fields.count > 1 ? String(fields[1]) : ""
        if value.hasPrefix(" ") { value.removeFirst() }
        switch field {
        case "event": name = value
        case "data": lines.append(value)
        default: break
        }
        return nil
    }

    mutating func finish() -> Event? {
        defer { name = ""; lines = []; frameBytes = 0 }
        guard !lines.isEmpty else { return nil }
        return Event(name: name, payload: lines.joined(separator: "\n"))
    }
}
