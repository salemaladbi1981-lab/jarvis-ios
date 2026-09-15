import Foundation

/// Honest capability status — never fake a real action as executed.
enum CapabilityStatus: String {
    case verified = "REAL / VERIFIED"
    case devicePending = "IMPLEMENTED / DEVICE-PENDING"
    case experimental = "EXPERIMENTAL"
    case unavailable = "UNAVAILABLE / NOT INTEGRATED"
}

/// Typed quick command: stable ID (not text matching), label, honest status.
enum QuickCommand: String, CaseIterable, Identifiable {
    case calendar
    case reminders
    case tomorrow
    case focus
    case doorCamera
    case calmMedia

    var id: String { rawValue }

    var label: String {
        switch self {
        case .calendar:   return "وش عندي في الجدول؟"
        case .reminders: return "وش عندي من تذكيرات؟"
        case .tomorrow:   return "بطلع بكرة؟"
        case .focus:      return "فعّل وضع التركيز"
        case .doorCamera: return "ورّني كاميرا الباب"
        case .calmMedia:  return "شغّل شي هادي"
        }
    }

    var capabilityStatus: CapabilityStatus {
        switch self {
        case .calendar:   return .verified
        case .reminders: return .devicePending
        case .tomorrow:   return .unavailable
        case .focus:      return .unavailable
        case .doorCamera: return .experimental
        case .calmMedia:  return .experimental
        }
    }

    var unavailableReason: String {
        switch self {
        case .calendar:   return ""
        case .reminders: return ""
        case .tomorrow:   return "يحتاج تكامل بيانات الغد (جدول + طقس)"
        case .focus:      return "يحتاج تكامل نظام التركيز"
        case .doorCamera: return "لا يوجد تكامل كاميرا حقيقي بعد"
        case .calmMedia:  return "لا توجد خدمة وسائط حقيقية بعد"
        }
    }
}
