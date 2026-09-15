//
//  JarvisState.swift — the seven approved system states.
//  UI state is driven from this model (no independent animation).
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
