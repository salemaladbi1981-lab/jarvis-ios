import Foundation

/// Mock Calendar/Reminders provider — explicitly mock, never confused with real.
struct MockCalendarProvider {
    var mode: CalendarProviderMode { .mock }

    func todayEvents() async -> [CalendarEvent] {
        let cal = Calendar.current
        let mk = { (h: Int, t: String) -> CalendarEvent in
            let d = cal.date(bySettingHour: h, minute: 0, second: 0, of: Date()) ?? Date()
            return CalendarEvent(id: UUID().uuidString, title: t, start: d,
                                 end: d.addingTimeInterval(3600), isAllDay: false,
                                 calendarName: nil, location: nil)
        }
        return [mk(9, "Marketing Meeting — 09:00"), mk(11, "Project Review — 11:30")]
    }

    func nextEvent() async -> CalendarEvent? {
        todayEvents().first
    }

    func upcomingReminders() async -> [ReminderItem] {
        [ReminderItem(id: UUID().uuidString, title: "Review document",
                      dueDate: Date().addingTimeInterval(7200), isCompleted: false, listName: nil)]
    }
}
