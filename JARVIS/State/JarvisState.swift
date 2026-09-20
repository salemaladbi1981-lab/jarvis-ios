//
//  JarvisState.swift — approved shared system states.
//  UI state is driven from these models (no independent animation).
//
import Foundation

public enum JarvisState: String, CaseIterable, Codable {
    case idle
    case listening
    case thinking
    case speaking
    case executing
    case alert
    case approval

    public var arabicLabel: String {
        switch self {
        case .idle: return "خامل"
        case .listening: return "استماع"
        case .thinking: return "تفكير"
        case .speaking: return "يتكلم"
        case .executing: return "تنفيذ"
        case .alert: return "تنبيه"
        case .approval: return "موافقة"
        }
    }

    /// هل الحالة تعطّل تنفيذ الأفعال عالية الخطورة (موافقة معلّقة)؟
    public var blocksExecution: Bool { self == .approval }
}

// MARK: - Meeting foundation

/// مصدر معلومات الاجتماع. لا يحتوي هذا النوع على أي تنفيذ تسجيل أو وصول للميكروفون.
public enum MeetingInputMode: String, CaseIterable, Codable {
    /// عنوان/موعد/حضور ومعلومات وصفية فقط، بدون التقاط صوت.
    case metadataOnly
    /// نص/تفريغ تم استيراده صراحة من ملف أو تكامل مصرح.
    case importedTranscript
    /// التقاط حي مستقبلي؛ يبقى خلف موافقة المالك + تأكيد موافقة المشاركين.
    case authorizedLiveCapture
}

/// يحدد هل يتكلم JARVIS أثناء الاجتماع. "silentObserver" تعني عدم المقاطعة صوتيًا،
/// ولا تعني تسجيلًا خفيًا ولا تلغي مؤشرات النظام أو متطلبات الموافقة.
public enum MeetingAssistantPresence: String, CaseIterable, Codable {
    case interactive
    case silentObserver
}

public enum MeetingSessionState: String, CaseIterable, Codable {
    case idle
    case awaitingAuthorization
    case ready
    case active
    case stopped
    case failed
}

public enum MeetingCaptureBlockReason: String, Codable {
    case ownerAuthorizationRequired
    case participantConsentRequired
}

public struct MeetingCaptureDecision: Equatable, Codable {
    public let allowed: Bool
    public let blockReason: MeetingCaptureBlockReason?
    /// أي التقاط حي مستقبلي يجب أن يبقى مرئيًا للمستخدم/النظام؛ لا يوجد وضع stealth.
    public let requiresVisibleCaptureIndicator: Bool

    public init(
        allowed: Bool,
        blockReason: MeetingCaptureBlockReason?,
        requiresVisibleCaptureIndicator: Bool
    ) {
        self.allowed = allowed
        self.blockReason = blockReason
        self.requiresVisibleCaptureIndicator = requiresVisibleCaptureIndicator
    }
}

/// بوابة سياسة مشتركة فقط. لا تبدأ تسجيلًا ولا تطلب صلاحيات ولا تتجاوز قيود المنصة.
public enum MeetingCapturePolicy {
    public static func evaluate(
        inputMode: MeetingInputMode,
        ownerAuthorized: Bool,
        participantConsentConfirmed: Bool
    ) -> MeetingCaptureDecision {
        switch inputMode {
        case .metadataOnly, .importedTranscript:
            return MeetingCaptureDecision(
                allowed: true,
                blockReason: nil,
                requiresVisibleCaptureIndicator: false
            )
        case .authorizedLiveCapture:
            guard ownerAuthorized else {
                return MeetingCaptureDecision(
                    allowed: false,
                    blockReason: .ownerAuthorizationRequired,
                    requiresVisibleCaptureIndicator: true
                )
            }
            guard participantConsentConfirmed else {
                return MeetingCaptureDecision(
                    allowed: false,
                    blockReason: .participantConsentRequired,
                    requiresVisibleCaptureIndicator: true
                )
            }
            return MeetingCaptureDecision(
                allowed: true,
                blockReason: nil,
                requiresVisibleCaptureIndicator: true
            )
        }
    }
}

/// حالة مشتركة قابلة للنقل بين واجهة macOS وأي Meeting Agent مستقبلي.
/// لا تُخزّن صوتًا ولا تمنح أي صلاحية بحد ذاتها.
public struct MeetingSessionDescriptor: Identifiable, Equatable, Codable {
    public let id: String
    public var title: String
    public var inputMode: MeetingInputMode
    public var presence: MeetingAssistantPresence
    public var state: MeetingSessionState

    public init(
        id: String = UUID().uuidString,
        title: String,
        inputMode: MeetingInputMode,
        presence: MeetingAssistantPresence = .silentObserver,
        state: MeetingSessionState = .idle
    ) {
        self.id = id
        self.title = title
        self.inputMode = inputMode
        self.presence = presence
        self.state = state
    }
}

/// نقطة توسعة مستقبلية لمصدر اجتماع. أي مزود حقيقي يجب أن يمر عبر MeetingCapturePolicy
/// قبل التنفيذ. لا يوجد مزود تسجيل ضمن هذه المرحلة.
public protocol MeetingInputProvider {
    var mode: MeetingInputMode { get }
    var supportsLiveCapture: Bool { get }
}
