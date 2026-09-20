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

    private enum RetryTarget {
        case load(String)
        case send(String)
    }

    private let api: JarvisAPI
    private var retryTarget: RetryTarget?
    private var requestInFlight = false

    init(api: JarvisAPI) { self.api = api }

    func load(_ id: String) async {
        conversationId = id
        errorMessage = nil
        do {
            let detail: ConversationDetail = try await api.getObject("conversations/\(id)")
            messages = detail.messages ?? []
            status = .idle
            statusLabel = ""
            retryTarget = nil
        } catch {
            status = .failed
            statusLabel = ""
            errorMessage = userFacingMessage(for: error, operation: "تحميل المحادثة")
            retryTarget = .load(id)
        }
    }

    func send(_ text: String) async {
        await send(text, appendLocalUserMessage: true)
    }

    private func send(_ text: String, appendLocalUserMessage: Bool) async {
        let cid = conversationId
        guard !cid.isEmpty else { return }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        guard !requestInFlight else { return }

        guard !api.sessionToken.isEmpty else {
            status = .failed
            statusLabel = ""
            errorMessage = "جلسة جارفس غير متاحة. أعد ربط الجهاز ثم حاول مرة أخرى."
            retryTarget = .send(trimmed)
            return
        }

        requestInFlight = true
        defer { requestInFlight = false }

        if appendLocalUserMessage {
            let userMsg = ChatMessage(messageId: "local-\(UUID().uuidString.prefix(8))",
                                      conversationId: cid, role: "user", content: trimmed,
                                      citations: nil, toolCalls: nil, attachmentRefs: nil,
                                      taskRefs: nil, deliveryRefs: nil,
                                      executionState: nil, createdAt: Date().timeIntervalSince1970)
            messages.append(userMsg)
        }

        streamingText = ""
        liveCitations = []
        pendingTaskId = nil
        errorMessage = nil
        status = .working
        statusLabel = "جارٍ المعالجة"
        retryTarget = .send(trimmed)

        var req = URLRequest(url: api.baseURL.appendingPathComponent("conversations/\(cid)/chat"))
        req.httpMethod = "POST"
        req.timeoutInterval = 45
        req.setValue(api.sessionToken, forHTTPHeaderField: "X-Jarvis-Session")
        req.setValue(api.workspace, forHTTPHeaderField: "X-Jarvis-Workspace")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["text": trimmed])

        do {
            let (bytes, response) = try await URLSession.shared.bytes(for: req)
            guard let http = response as? HTTPURLResponse else {
                failSend("استجابة الخادم غير صالحة.")
                return
            }
            guard (200..<300).contains(http.statusCode) else {
                failSend(message(forHTTPStatus: http.statusCode))
                return
            }

            var currentEvent = ""
            var sawTerminalEvent = false
            for try await line in bytes.lines {
                if line.hasPrefix("event: ") {
                    currentEvent = String(line.dropFirst(7))
                } else if line.hasPrefix("data: ") {
                    let payload = String(line.dropFirst(6))
                    if handle(currentEvent, payload) {
                        sawTerminalEvent = true
                    }
                }
            }

            if !sawTerminalEvent && status != .idle && status != .backgroundTask && status != .failed {
                failSend("انتهى الاتصال قبل اكتمال الرد. يمكنك إعادة المحاولة.")
            }
        } catch {
            failSend(userFacingMessage(for: error, operation: "إرسال الرسالة"))
        }
    }

    /// يعيد true عند حدث نهائي حتى نميز انتهاء SSE الطبيعي عن انقطاع صامت.
    private func handle(_ event: String, _ payload: String) -> Bool {
        guard let data = payload.data(using: .utf8) else { return false }
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
                    retryTarget = nil
                    #if os(iOS)
                    if let tid = c.taskId {
                        NotificationManager.shared.notifyTaskHandoff(tid)
                    }
                    #endif
                } else {
                    finishAssistant(c)
                }
                return true
            }
        case "error":
            if let e = try? JSONDecoder().decode(ErrorEvent.self, from: data) {
                status = .failed
                statusLabel = ""
                errorMessage = e.message ?? "حدث خطأ أثناء تنفيذ الطلب"
                return true
            }
        default:
            break
        }
        return false
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
        retryTarget = nil
    }

    private func failSend(_ message: String) {
        status = .failed
        statusLabel = ""
        errorMessage = message
    }

    private func message(forHTTPStatus code: Int) -> String {
        switch code {
        case 401:
            return "انتهت جلسة جارفس أو لم تعد صالحة. أعد ربط الجهاز."
        case 403:
            return "هذه المساحة أو العملية غير مصرح بها."
        case 408, 504:
            return "انتهت مهلة الاتصال بالخادم. يمكنك إعادة المحاولة."
        case 429:
            return "الخدمة مشغولة حاليًا. حاول مرة أخرى بعد قليل."
        case 500...599:
            return "الخادم غير متاح مؤقتًا. يمكنك إعادة المحاولة."
        default:
            return "تعذر تنفيذ الطلب (HTTP \(code))."
        }
    }

    private func userFacingMessage(for error: Error, operation: String) -> String {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .notConnectedToInternet:
                return "لا يوجد اتصال بالإنترنت. تحقق من الشبكة ثم أعد المحاولة."
            case .timedOut:
                return "انتهت مهلة \(operation). أعد المحاولة."
            case .networkConnectionLost:
                return "انقطع اتصال الشبكة أثناء \(operation). أعد المحاولة."
            case .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed:
                return "تعذر الوصول إلى خادم جارفس. تحقق من الشبكة ثم أعد المحاولة."
            default:
                break
            }
        }

        let nsError = error as NSError
        if nsError.domain == "JarvisAPI" {
            return message(forHTTPStatus: nsError.code)
        }
        return "تعذر \(operation). أعد المحاولة."
    }

    func retry() async {
        guard !requestInFlight else { return }
        guard let target = retryTarget else {
            if !conversationId.isEmpty { await load(conversationId) }
            return
        }

        errorMessage = nil
        switch target {
        case .load(let id):
            await load(id)
        case .send(let text):
            // الرسالة المحلية موجودة أصلًا؛ لا نكررها عند retry.
            await send(text, appendLocalUserMessage: false)
        }
    }
}
