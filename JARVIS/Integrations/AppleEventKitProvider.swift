import Foundation
import EventKit

/// Real Apple Calendar + Reminders provider (READ-ONLY).
final class AppleEventKitProvider {
    private let store = EKEventStore()

    func eventAccess() -> CalendarPermissionState {
        Self.map(EKEventStore.authorizationStatus(for: .event))
    }

    func reminderAccess() -> CalendarPermissionState {
        Self.map(EKEventStore.authorizationStatus(for: .reminder))
    }

    /// Single mapping for every EKAuthorizationStatus (includes legacy .authorized).
    static func map(_ s: EKAuthorizationStatus) -> CalendarPermissionState {
        switch s {
        case .notDetermined: return .notDetermined
        case .authorized:    return .authorized   // legacy alias (iOS <17 shape)
        case .fullAccess:    return .authorized
        case .writeOnly:     return .restricted
        case .denied:        return .denied
        case .restricted:    return .restricted
        @unknown default:    return .unavailable
        }
    }

    /// Safe diagnostic string (no personal data) — for device debugging.
    static func accessDebugString(_ entity: EKEntityType) -> String {
        let s = EKEventStore.authorizationStatus(for: entity)
        let raw = s.rawValue
        let name: String
        switch s {
        case .notDetermined: name = "notDetermined"
        case .authorized:    name = "authorized(legacy)"
        case .fullAccess:    name = "fullAccess"
        case .writeOnly:     name = "writeOnly"
        case .denied:        name = "denied"
        case .restricted:    name = "restricted"
        @unknown default:    name = "unknown"
        }
        return "\(name) [raw \(raw)]"
    }

    func requestEvents() async -> CalendarPermissionState {
        do { return try await store.requestFullAccessToEvents() ? .authorized : .denied }
        catch { return .denied }
    }

    func requestReminders() async -> CalendarPermissionState {
        do { return try await store.requestFullAccessToReminders() ? .authorized : .denied }
        catch { return .denied }
    }

    func todayEvents() async throws -> [JarvisCalendarEvent] {
        let cal = Calendar.current
        let start = cal.startOfDay(for: Date())
        guard let end = cal.date(byAdding: .day, value: 1, to: start) else { return [] }
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: nil)
        return store.events(matching: predicate)
            .sorted { $0.startDate < $1.startDate }
            .map { JarvisCalendarEvent(ek: $0) }
    }

    func nextEvent() async throws -> JarvisCalendarEvent? {
        let cal = Calendar.current
        let now = Date()
        guard let horizon = cal.date(byAdding: .day, value: 30, to: now) else { return nil }
        let predicate = store.predicateForEvents(withStart: now, end: horizon, calendars: nil)
        return store.events(matching: predicate)
            .filter { $0.startDate >= now }
            .sorted { $0.startDate < $1.startDate }
            .first
            .map { JarvisCalendarEvent(ek: $0) }
    }

    func upcomingReminders(limit: Int = 20) async throws -> [JarvisReminderItem] {
        let predicate = store.predicateForIncompleteReminders(withDueDateStarting: nil,
                                                              ending: nil, calendars: nil)
        return try await withCheckedThrowingContinuation { cont in
            store.fetchReminders(matching: predicate) { reminders in
                cont.resume(returning: (reminders ?? []).prefix(limit).map { JarvisReminderItem(ek: $0) })
            }
        }
    }
}

extension JarvisCalendarEvent {
    init(ek: EKEvent) {
        id = ek.eventIdentifier ?? UUID().uuidString
        title = ek.title ?? "بدون عنوان"
        start = ek.startDate
        end = ek.endDate
        isAllDay = ek.isAllDay
        calendarName = ek.calendar?.title
        location = ek.location
    }
}

extension JarvisReminderItem {
    init(ek: EKReminder) {
        id = ek.calendarItemIdentifier
        title = ek.title ?? "بدون عنوان"
        dueDate = ek.dueDateComponents?.date
        isCompleted = ek.isCompleted
        listName = ek.calendar?.title
    }
}
