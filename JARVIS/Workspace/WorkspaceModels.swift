import Foundation

/// Decoder موحّد — backend يستخدم snake_case.
enum JarvisJSON {
    static func decoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }
}

struct Conversation: Codable, Identifiable {
    var id: String { conversationId }
    let conversationId: String
    let userId: String?
    let workspaceId: String?
    let source: String?
    let title: String?
    let memoryNamespace: String?
    let lastActivity: Double?
    let taskIds: [String]?
    let deliveryIds: [String]?
    let messageIds: [String]?
}

struct Citation: Codable, Identifiable {
    var id: String { citationId }
    let citationId: String
    let messageId: String?
    let title: String?
    let url: String?
    let source: String?
    let snippet: String?
    let order: Int?
}

struct ToolCall: Codable {
    let toolName: String?
    let callId: String?
    let status: String?
    let ts: Double?
}

struct ChatMessage: Codable, Identifiable {
    var id: String { messageId }
    let messageId: String
    let conversationId: String?
    let role: String?
    let content: String?
    let citations: [Citation]?
    let toolCalls: [ToolCall]?
    let attachmentRefs: [String]?
    let taskRefs: [String]?
    let deliveryRefs: [String]?
    let executionState: ExecutionState?
    let createdAt: Double?
}

struct ExecutionState: Codable {
    let status: String?
    let error: String?
}

struct JarvisTask: Codable, Identifiable {
    var id: String { taskId }
    let taskId: String
    let conversationId: String?
    let prompt: String?
    let status: String?
    let jobState: String?
    let progress: Int?
    let outputs: [String]?
    let error: String?
    let lastError: String?
    let attempts: Int?
    let selectedAgent: String?
    let createdAt: Double?
    let completedAt: Double?
}

struct DeliveryItem: Codable, Identifiable {
    var id: String { deliveryId }
    let deliveryId: String
    let taskId: String?
    let conversationId: String?
    let filename: String?
    let type: String?
    let size: Int?
    let status: String?
    let createdAt: Double?
}

struct InboxItem: Codable, Identifiable {
    var id: String { "\(type)-\(approvalId ?? taskId ?? deliveryId ?? "x")" }
    let type: String
    let title: String?
    let approvalId: String?
    let taskId: String?
    let conversationId: String?
    let deliveryId: String?
    let ts: Double?

    var kind: InboxKind {
        switch type {
        case "approval": return .approval
        case "task_failed": return .failed
        case "task_completed": return .completed
        case "delivery": return .delivery
        default: return .action
        }
    }
}

enum InboxKind: String {
    case approval, failed, completed, delivery, action

    var label: String {
        switch self {
        case .approval: return "يتطلب موافقة"
        case .failed: return "فشلت"
        case .completed: return "اكتملت"
        case .delivery: return "تسليم جاهز"
        case .action: return "إجراء مطلوب"
        }
    }

    var systemImage: String {
        switch self {
        case .approval: return "checkmark.shield"
        case .failed: return "exclamationmark.triangle"
        case .completed: return "checkmark.circle"
        case .delivery: return "doc.fill"
        case .action: return "bell"
        }
    }
}
