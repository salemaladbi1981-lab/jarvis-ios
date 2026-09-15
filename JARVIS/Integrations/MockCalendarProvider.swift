import Foundation

/// Mock EventKit provider — explicitly mock, never confused with real.
struct MockEventKitProvider {
    var mode: CalendarProviderMode { .mock }

    func todayEvents() -> [JarvisCalendarEvent] {
        let cal = Calendar.current
        func mk(_ h: Int, _ t: String) -> JarvisCalendarEvent {
            let d = cal.date(bySettingHour: h, minute: 0, second: 0, of: Date()) ?? Date()
            return JarvisCalendarEvent(id: UUID().uuidString, title: t, start: d,
                                       end: d.addingTimeInterval(3600), isAllDay: false,
                                       calendarName: nil, location: nil)
        }
        return [mk(9, "Marketing Meeting — 09:00"), mk(11, "Project Review — 11:30")]
    }

    func nextEvent() -> JarvisCalendarEvent? { todayEvents().first }

    func upcomingReminders() -> [JarvisReminderItem] {
        [JarvisReminderItem(id: UUID().uuidString, title: "Review document",
                            dueDate: Date().addingTimeInterval(7200), isCompleted: false, listName: nil)]
    }
}
