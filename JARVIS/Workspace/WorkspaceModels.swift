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

/// استجابة POST /conversations: {"ok":…, "created":…, "conversation":{…}} — المحادثة مُغلّفة.
struct ConversationEnvelope: Codable {
    let ok: Bool?
    let created: Bool?
    let conversation: Conversation
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

struct InboxItem: Codable, Identifiable, Hashable {
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

struct DerivativeItem: Codable, Hashable {
    let status: String?
    let ref: String?
}

struct FileItem: Codable, Identifiable {
    var id: String { fileId }
    let fileId: String
    let filename: String?
    let mimeType: String?
    let size: Int?
    let mediaKind: String?
    let status: String?
    let derivatives: [String: DerivativeItem]?

    var isImage: Bool { mediaKind == "image" }
    var isVideo: Bool { mediaKind == "video" }
    var isAudio: Bool { mediaKind == "audio" }
    var isDocument: Bool { mediaKind == "document" || (mimeType ?? "").contains("pdf") || (mimeType ?? "").contains("document") }

    /// هل يوجد مشتق thumbnail (image/video poster/audio waveform) جاهز؟
    var hasThumbnail: Bool { derivatives?["thumbnail"]?.status == "GENERATED" }
    var hasPreview: Bool { derivatives?["preview"]?.status == "GENERATED" }
}

/// Snapshot from GET /project/health. Kept in WorkspaceModels.swift because this file
/// is already part of both iOS and macOS targets; health UI must not depend on an
/// unregistered source file in the generated Xcode project.
struct ProjectHealth: Codable {
    let ok: Bool?
    let phase: String?
    let currentMilestone: String?
    let nextMilestone: String?
    let buildSha: String?
    let ciStatus: String?
    let testsStatus: String?
    let provider: String?
    let killSwitch: Bool?
    let workspaceId: String?
    let tasksTotal: Int?
    let tasksActive: Int?
    let tasksFailed: Int?
    let pendingApprovals: Int?
    let ownerActions: Int?
    let capabilityCount: Int?
    let blockers: Int?

    var ciDisplay: String {
        switch (ciStatus ?? "unknown").lowercased() {
        case "success", "passed", "green": return "CI أخضر"
        case "failed", "failure", "red": return "CI فاشل"
        case "running", "in_progress": return "CI يعمل"
        default: return "CI غير متاح"
        }
    }

    var testsDisplay: String {
        switch (testsStatus ?? "unknown").lowercased() {
        case "success", "passed", "green": return "الاختبارات ناجحة"
        case "failed", "failure", "red": return "الاختبارات فاشلة"
        case "running", "in_progress": return "الاختبارات تعمل"
        default: return "حالة الاختبارات غير متاحة"
        }
    }
}
