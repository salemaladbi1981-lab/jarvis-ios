import Foundation
import EventKit

/// نتيجة عملية كتابة (لا تحمل بيانات شخصية في error).
struct ToolWriteResult: Equatable {
    let ok: Bool
    let error: String?
    let newID: String?
    init(ok: Bool, error: String? = nil, newID: String? = nil) {
        self.ok = ok; self.error = error; self.newID = newID
    }
}

/// عمليات الكتابة على التقويم/التذكيرات (معزولة عن provider القراءة المجمّد).
/// كل كتابة تتطلب صلاحية كاملة مسبقاً — والتأكيد يُدار في طبقة ViewModel لا هنا.
final class AppleEventKitWriter {
    private let store = EKEventStore()

    private func eventAccessGranted() -> Bool {
        let s = EKEventStore.authorizationStatus(for: .event)
        return s == .fullAccess || s == .authorized
    }
    private func reminderAccessGranted() -> Bool {
        let s = EKEventStore.authorizationStatus(for: .reminder)
        return s == .fullAccess || s == .authorized
    }

    // MARK: Calendar — create/update/delete
    func createEvent(title: String, start: Date, end: Date) -> ToolWriteResult {
        guard eventAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        let e = EKEvent(eventStore: store)
        e.title = title; e.startDate = start; e.endDate = end
        e.calendar = store.defaultCalendarForNewEvents
        do { try store.save(e, span: .thisEvent); return ToolWriteResult(ok: true, newID: e.eventIdentifier) }
        catch { return ToolWriteResult(ok: false, error: "save_failed") }
    }

    func updateEvent(id: String, title: String?, start: Date?, end: Date?) -> ToolWriteResult {
        guard eventAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        guard let e = store.event(withIdentifier: id) else { return ToolWriteResult(ok: false, error: "not_found") }
        if let title { e.title = title }
        if let start { e.startDate = start }
        if let end { e.endDate = end }
        do { try store.save(e, span: .thisEvent); return ToolWriteResult(ok: true) }
        catch { return ToolWriteResult(ok: false, error: "save_failed") }
    }

    func deleteEvent(id: String) -> ToolWriteResult {
        guard eventAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        guard let e = store.event(withIdentifier: id) else { return ToolWriteResult(ok: false, error: "not_found") }
        do { try store.remove(e, span: .thisEvent); return ToolWriteResult(ok: true) }
        catch { return ToolWriteResult(ok: false, error: "delete_failed") }
    }

    // MARK: Reminders — create/update/complete/delete
    func createReminder(title: String, due: Date?) -> ToolWriteResult {
        guard reminderAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        let r = EKReminder(eventStore: store)
        r.title = title
        if let due {
            r.dueDateComponents = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: due)
        }
        r.calendar = store.defaultCalendarForNewReminders()
        do { try store.save(r, commit: true); return ToolWriteResult(ok: true, newID: r.calendarItemIdentifier) }
        catch { return ToolWriteResult(ok: false, error: "save_failed") }
    }

    func updateReminder(id: String, title: String?, due: Date?) -> ToolWriteResult {
        guard reminderAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        guard let r = store.calendarItem(withIdentifier: id) as? EKReminder else {
            return ToolWriteResult(ok: false, error: "not_found")
        }
        if let title { r.title = title }
        if let due {
            r.dueDateComponents = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: due)
        }
        do { try store.save(r, commit: true); return ToolWriteResult(ok: true) }
        catch { return ToolWriteResult(ok: false, error: "save_failed") }
    }

    func completeReminder(id: String) -> ToolWriteResult {
        guard reminderAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        guard let r = store.calendarItem(withIdentifier: id) as? EKReminder else {
            return ToolWriteResult(ok: false, error: "not_found")
        }
        r.isCompleted = true
        do { try store.save(r, commit: true); return ToolWriteResult(ok: true) }
        catch { return ToolWriteResult(ok: false, error: "save_failed") }
    }

    func deleteReminder(id: String) -> ToolWriteResult {
        guard reminderAccessGranted() else { return ToolWriteResult(ok: false, error: "permission_denied") }
        guard let r = store.calendarItem(withIdentifier: id) as? EKReminder else {
            return ToolWriteResult(ok: false, error: "not_found")
        }
        do { try store.remove(r, commit: true); return ToolWriteResult(ok: true) }
        catch { return ToolWriteResult(ok: false, error: "delete_failed") }
    }
}
