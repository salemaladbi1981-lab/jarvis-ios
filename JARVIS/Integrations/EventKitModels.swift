import Foundation

/// Typed JARVIS domain models (unique names; never raw EventKit objects).
struct JarvisCalendarEvent: Identifiable, Equatable {
    let id: String
    let title: String
    let start: Date
    let end: Date
    let isAllDay: Bool
    let calendarName: String?
    let location: String?
}

struct JarvisReminderItem: Identifiable, Equatable {
    let id: String
    let title: String
    let dueDate: Date?
    let isCompleted: Bool
    let listName: String?
}

enum CalendarPermissionState: Equatable {
    case notDetermined
    case authorized
    case denied
    case restricted
    case unavailable
}

enum CalendarProviderMode {
    case real
    case mock
}
