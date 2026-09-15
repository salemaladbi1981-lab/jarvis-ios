import Foundation
import EventKit

/// Real Apple Calendar + Reminders provider (READ-ONLY).
/// Normalizes EventKit objects into typed JARVIS domain models.
final class AppleEventKitProvider {
    private let store = EKEventStore()

    // MARK: Permission

    func eventAccess() async -> CalendarPermissionState {
        switch EKEventStore.authorizationStatus(for: .event) {
        case .notDetermined: return .notDetermined
        case .fullAccess: return .authorized
        case .writeOnly: return .restricted
        case .denied: return .denied
        case .restricted: return .restricted
        @unknown default: return .unavailable
        }
    }

    func reminderAccess() async -> CalendarPermissionState {
        switch EKEventStore.authorizationStatus(for: .reminder) {
        case .notDetermined: return .notDetermined
        case .fullAccess: return .authorized
        case .writeOnly: return .restricted
        case .denied: return .denied
        case .restricted: return .restricted
        @unknown default: return .unavailable
        }
    }

    func requestEvents() async -> CalendarPermissionState {
        do {
            let ok = try await store.requestFullAccessToEvents()
            return ok ? .authorized : .denied
        } catch {
            return .denied
        }
    }

    func requestReminders() async -> CalendarPermissionState {
        do {
            let ok = try await store.requestFullAccessToReminders()
            return ok ? .authorized : .denied
        } catch {
            return .denied
        }
    }

    // MARK: Reads

    func todayEvents() async throws -> [CalendarEvent] {
        let cal = Calendar.current
        let start = cal.startOfDay(for: Date())
        guard let end = cal.date(byAdding: .day, value: 1, to: start) else { return [] }
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: nil)
        return store.events(matching: predicate)
            .sorted { $0.startDate < $1.startDate }
            .map(CalendarEvent.init(ek:))
    }

    func nextEvent() async throws -> CalendarEvent? {
        let cal = Calendar.current
        let now = Date()
        guard let horizon = cal.date(byAdding: .day, value: 30, to: now) else { return nil }
        let predicate = store.predicateForEvents(withStart: now, end: horizon, calendars: nil)
        return store.events(matching: predicate)
            .filter { $0.startDate >= now }
            .sorted { $0.startDate < $1.startDate }
            .first
            .map(CalendarEvent.init(ek:))
    }

    func upcomingReminders(limit: Int = 20) async throws -> [ReminderItem] {
        let predicate = store.predicateForIncompleteReminders(withDueDateStarting: nil,
                                                              ending: nil,
                                                              calendars: nil)
        let reminders = try await store.fetchReminders(matching: predicate)
        return reminders
            .prefix(limit)
            .map(ReminderItem.init(ek:))
    }
}

extension CalendarEvent {
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

extension ReminderItem {
    init(ek: EKReminder) {
        id = ek.calendarItemIdentifier
        title = ek.title ?? "بدون عنوان"
        dueDate = ek.dueDateComponents?.date
        isCompleted = ek.isCompleted
        listName = ek.calendar?.title
    }
}
