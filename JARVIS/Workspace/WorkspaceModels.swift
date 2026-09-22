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

/// Sanitized blocker returned by GET /project/health. The backend deliberately
/// omits internal errors/payloads; the client mirrors only the owner-safe fields.
struct ProjectHealthBlocker: Codable, Identifiable {
    var id: String {
        [type, taskId, job, state, status]
            .compactMap { $0 }
            .joined(separator: ":")
    }

    let type: String?
    let state: String?
    let taskId: String?
    let job: String?
    let status: String?
    let runUrl: String?
}

/// Sanitized owner action. Approval params are intentionally not represented on
/// device so Project Health cannot become a side channel for sensitive payloads.
struct ProjectHealthOwnerAction: Codable, Identifiable {
    var id: String { approvalId ?? [type, agent, action, taskId].compactMap { $0 }.joined(separator: ":") }

    let type: String?
    let approvalId: String?
    let agent: String?
    let action: String?
    let taskId: String?
}

/// Snapshot from GET /project/health. Kept in WorkspaceModels.swift because this file
/// is already part of both iOS and macOS targets; health UI must not depend on an
/// unregistered source file in the generated Xcode project.
struct LegacyRuntimeHealth: Codable {
    let ok: Bool?
    let provider: String?
}

struct ProjectHealth: Codable {
    let ok: Bool?
    let phase: String?
    let currentMilestone: String?
    let nextMilestone: String?
    let buildSha: String?
    let ciStatus: String?
    let testsStatus: String?
    let ciRunId: String?
    let ciRunNumber: String?
    let ciRunUrl: String?
    let ciBranch: String?
    let ciMetadataGeneratedAt: String?
    let ciMetadataState: String?
    let ciMetadataAgeSeconds: Int?
    let ciJobs: [String: String]?
    let provider: String?
    let killSwitch: Bool?
    let workspaceId: String?
    let tasksTotal: Int?
    let tasksActive: Int?
    let tasksFailed: Int?
    let taskStates: [String: Int]?
    let pendingApprovals: Int?
    let ownerActions: Int?
    let ownerActionItems: [ProjectHealthOwnerAction]?
    let capabilityCount: Int?
    let blockers: Int?
    let blockerItems: [ProjectHealthBlocker]?
    let evidence: [String: String]?

    var failedCIJobs: [String] {
        (ciJobs ?? [:])
            .filter { $0.value.lowercased() == "failure" }
            .map(\.key)
            .sorted()
    }

    var ciDisplay: String {
        let run = (ciRunNumber?.isEmpty == false) ? " #\(ciRunNumber!)" : ""
        let build = buildDisplay.map { " • \($0)" } ?? ""
        let metadataState = (ciMetadataState ?? "unknown").lowercased()
        if metadataState == "stale" {
            return "CI قديم\(run)\(build)"
        }
        if metadataState == "unknown", ciMetadataGeneratedAt?.isEmpty == false {
            return "CI غير موثوق\(run)\(build)"
        }
        switch (ciStatus ?? "unknown").lowercased() {
        case "success", "passed", "green": return "CI أخضر\(run)\(build)"
        case "failed", "failure", "red":
            if let failedJob = failedCIJobs.first {
                return "CI فاشل\(run) • \(failedJob)\(build)"
            }
            return "CI فاشل\(run)\(build)"
        case "running", "in_progress": return "CI يعمل\(run)\(build)"
        default: return "CI غير متاح\(build)"
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

    var buildDisplay: String? {
        guard let buildSha, !buildSha.isEmpty else { return nil }
        let short = String(buildSha.prefix(8))
        if let ciBranch, !ciBranch.isEmpty {
            return "\(ciBranch) • \(short)"
        }
        return short
    }
}

extension ProjectHealth {
    /// Honest compatibility snapshot for an older deployed backend that exposes
    /// only /health. CI/build/milestone evidence remains unknown instead of fake.
    static func legacyRuntime(_ health: LegacyRuntimeHealth) -> ProjectHealth {
        ProjectHealth(
            ok: health.ok,
            phase: "runtime",
            currentMilestone: nil,
            nextMilestone: nil,
            buildSha: nil,
            ciStatus: "unknown",
            testsStatus: "unknown",
            ciRunId: nil,
            ciRunNumber: nil,
            ciRunUrl: nil,
            ciBranch: nil,
            ciMetadataGeneratedAt: nil,
            ciMetadataState: "unknown",
            ciMetadataAgeSeconds: nil,
            ciJobs: nil,
            provider: health.provider,
            killSwitch: nil,
            workspaceId: nil,
            tasksTotal: nil,
            tasksActive: nil,
            tasksFailed: nil,
            taskStates: nil,
            pendingApprovals: nil,
            ownerActions: nil,
            ownerActionItems: nil,
            capabilityCount: nil,
            blockers: nil,
            blockerItems: nil,
            evidence: ["project_health_endpoint": "legacy_backend_fallback"]
        )
    }
}

// MARK: - Meeting foundation

/// Describes where meeting content comes from. This is policy/state only: it does
/// not start microphones, screen capture, recording, or any other platform API.
enum MeetingCaptureMode: String, Codable, Equatable {
    /// A transcript/file the owner has already imported into JARVIS.
    case importedTranscript
    /// A future live adapter that may exist only behind explicit authorization.
    case liveAuthorized
}

/// Authorization facts that a future official live-capture adapter must provide.
/// The visible indicator is deliberately part of the gate so a "silent" JARVIS
/// mode can mean no spoken interruption, never hidden recording.
struct MeetingAuthorization: Equatable {
    let ownerAuthorized: Bool
    let participantConsent: Bool
    let visibleCaptureIndicator: Bool

    static let none = MeetingAuthorization(
        ownerAuthorized: false,
        participantConsent: false,
        visibleCaptureIndicator: false
    )
}

enum MeetingSessionState: String, Codable, Equatable {
    case idle
    case awaitingAuthorization
    case ready
    case active
    case stopped
}

enum MeetingAuthorizationPolicy {
    static func canPrepare(mode: MeetingCaptureMode, authorization: MeetingAuthorization) -> Bool {
        switch mode {
        case .importedTranscript:
            return true
        case .liveAuthorized:
            return authorization.ownerAuthorized
                && authorization.participantConsent
                && authorization.visibleCaptureIndicator
        }
    }
}

/// Shared lifecycle for iOS/macOS and a future Meeting Agent. It is fail-closed:
/// live sessions cannot become active without re-checking authorization, and an
/// active live session is stopped if authorization is later revoked.
struct MeetingSessionLifecycle: Equatable {
    private(set) var mode: MeetingCaptureMode?
    private(set) var state: MeetingSessionState = .idle
    private(set) var authorization: MeetingAuthorization = .none

    var requiresVisibleCaptureIndicator: Bool { mode == .liveAuthorized }

    mutating func prepare(mode: MeetingCaptureMode, authorization: MeetingAuthorization = .none) {
        self.mode = mode
        self.authorization = authorization
        state = MeetingAuthorizationPolicy.canPrepare(mode: mode, authorization: authorization)
            ? .ready
            : .awaitingAuthorization
    }

    @discardableResult
    mutating func start() -> Bool {
        guard let mode, state == .ready else { return false }
        guard MeetingAuthorizationPolicy.canPrepare(mode: mode, authorization: authorization) else {
            state = .awaitingAuthorization
            return false
        }
        state = .active
        return true
    }

    mutating func updateAuthorization(_ authorization: MeetingAuthorization) {
        self.authorization = authorization
        guard mode == .liveAuthorized else { return }
        let allowed = MeetingAuthorizationPolicy.canPrepare(mode: .liveAuthorized, authorization: authorization)

        switch state {
        case .active where !allowed:
            state = .stopped
        case .ready where !allowed:
            state = .awaitingAuthorization
        case .awaitingAuthorization where allowed:
            state = .ready
        default:
            break
        }
    }

    mutating func stop() {
        switch state {
        case .awaitingAuthorization, .ready, .active:
            state = .stopped
        case .idle, .stopped:
            break
        }
    }

    mutating func reset() {
        mode = nil
        authorization = .none
        state = .idle
    }
}
