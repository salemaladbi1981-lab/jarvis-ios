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

/// انتقالات جلسة الاجتماع المشتركة بين macOS وأي Meeting Agent مستقبلي.
/// هذه طبقة حالة فقط: لا تفتح الميكروفون، لا تبدأ تسجيلًا، ولا تمنح صلاحيات.
public enum MeetingSessionLifecycle {
    /// يحول نتيجة بوابة الالتقاط إلى حالة استعداد واحدة يمكن للواجهات والوكلاء الاعتماد عليها.
    /// أي live capture غير مكتمل الموافقات يبقى صراحة في awaitingAuthorization.
    public static func preparedState(
        inputMode: MeetingInputMode,
        ownerAuthorized: Bool,
        participantConsentConfirmed: Bool
    ) -> MeetingSessionState {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: inputMode,
            ownerAuthorized: ownerAuthorized,
            participantConsentConfirmed: participantConsentConfirmed
        )
        return decision.allowed ? .ready : .awaitingAuthorization
    }

    /// يمنع القفز مباشرة إلى active قبل المرور بحالة ready.
    /// التكرار لنفس الحالة مسموح لجعل handoff/reconnect idempotent.
    public static func canTransition(from: MeetingSessionState, to: MeetingSessionState) -> Bool {
        if from == to { return true }

        switch (from, to) {
        case (.idle, .awaitingAuthorization),
             (.idle, .ready),
             (.idle, .failed),
             (.awaitingAuthorization, .ready),
             (.awaitingAuthorization, .stopped),
             (.awaitingAuthorization, .failed),
             (.ready, .awaitingAuthorization),
             (.ready, .active),
             (.ready, .stopped),
             (.ready, .failed),
             (.active, .stopped),
             (.active, .failed),
             (.stopped, .idle),
             (.failed, .idle):
            return true
        default:
            return false
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

/// أخطاء متوقعة عند قيادة جلسة اجتماع عبر الـcoordinator المشترك.
/// لا تتضمن أي تنفيذ منصة أو صلاحيات فعلية.
public enum MeetingSessionTransitionError: Error, Equatable {
    case invalidTransition(from: MeetingSessionState, to: MeetingSessionState)
    case captureBlocked(MeetingCaptureBlockReason)
}

/// واجهة حالة مشتركة آمنة للـDesktop وMeeting Agent المستقبلي.
/// الهدف منع المستهلكين من تغيير state مباشرة بطريقة تتجاوز بوابة الموافقات.
/// لا يطلب هذا النوع إذن ميكروفون ولا يبدأ تسجيلًا ولا يلتقط أي محتوى.
public struct MeetingSessionCoordinator {
    public private(set) var descriptor: MeetingSessionDescriptor

    public init(descriptor: MeetingSessionDescriptor) {
        self.descriptor = descriptor
    }

    /// يقيّم سياسة المصدر وينقل الجلسة فقط إلى ready أو awaitingAuthorization.
    /// الاستدعاء المتكرر آمن طالما الحالة الحالية تسمح بنفس الانتقال.
    @discardableResult
    public mutating func prepare(
        ownerAuthorized: Bool,
        participantConsentConfirmed: Bool
    ) throws -> MeetingCaptureDecision {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: descriptor.inputMode,
            ownerAuthorized: ownerAuthorized,
            participantConsentConfirmed: participantConsentConfirmed
        )
        let target: MeetingSessionState = decision.allowed ? .ready : .awaitingAuthorization
        try transition(to: target)
        return decision
    }

    /// لا يسمح بتنشيط جلسة live حتى لو أُنشئ descriptor خارجيًا بحالة ready؛
    /// تتم إعادة فحص بوابة الموافقات عند لحظة التفعيل لمنع bypass بحالة محقونة.
    public mutating func activate(
        ownerAuthorized: Bool,
        participantConsentConfirmed: Bool
    ) throws {
        let decision = MeetingCapturePolicy.evaluate(
            inputMode: descriptor.inputMode,
            ownerAuthorized: ownerAuthorized,
            participantConsentConfirmed: participantConsentConfirmed
        )
        if let reason = decision.blockReason {
            throw MeetingSessionTransitionError.captureBlocked(reason)
        }
        try transition(to: .active)
    }

    public mutating func stop() throws {
        try transition(to: .stopped)
    }

    public mutating func reset() throws {
        try transition(to: .idle)
    }

    public mutating func markFailed() throws {
        try transition(to: .failed)
    }

    private mutating func transition(to target: MeetingSessionState) throws {
        guard MeetingSessionLifecycle.canTransition(from: descriptor.state, to: target) else {
            throw MeetingSessionTransitionError.invalidTransition(from: descriptor.state, to: target)
        }
        descriptor.state = target
    }
}

/// نقطة توسعة مستقبلية لمصدر اجتماع. أي مزود حقيقي يجب أن يمر عبر MeetingCapturePolicy
/// قبل التنفيذ. لا يوجد مزود تسجيل ضمن هذه المرحلة.
public protocol MeetingInputProvider {
    var mode: MeetingInputMode { get }
    var supportsLiveCapture: Bool { get }
}
