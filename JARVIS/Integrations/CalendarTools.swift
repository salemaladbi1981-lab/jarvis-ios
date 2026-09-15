import Foundation

/// Calendar/Reminders read-only tools (typed contracts, provider-injected).
struct CalendarToolResult: Equatable {
    let ok: Bool
    let kind: String
    let events: [JarvisCalendarEvent]
    let reminders: [JarvisReminderItem]
    let error: String?
    let mock: Bool
    let providerMode: String   // "real" | "mock"
    let providerName: String   // "AppleEventKitProvider" | "MockEventKitProvider"
}

struct CalendarTools {
    var provider: AppleEventKitProvider
    var mockProvider: MockEventKitProvider
    var useMock: Bool

    init(useMock: Bool = false) {
        self.provider = AppleEventKitProvider()
        self.mockProvider = MockEventKitProvider()
        self.useMock = useMock
    }

    func today() async -> CalendarToolResult {
        if useMock {
            let e = await mockProvider.todayEvents()
            return CalendarToolResult(ok: true, kind: "today", events: e, reminders: [], error: nil, mock: true, providerMode: "mock", providerName: "MockEventKitProvider")
        }
        let access = await provider.eventAccess()
        guard access == .authorized else {
            return CalendarToolResult(ok: false, kind: "today", events: [], reminders: [],
                                      error: access == .denied ? "permission_denied" : "permission_required", mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        }
        do {
            let e = try await provider.todayEvents()
            return CalendarToolResult(ok: true, kind: "today", events: e, reminders: [], error: nil, mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        } catch {
            return CalendarToolResult(ok: false, kind: "today", events: [], reminders: [], error: "unavailable", mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        }
    }

    func nextEvent() async -> CalendarToolResult {
        if useMock {
            let e = await mockProvider.nextEvent()
            return CalendarToolResult(ok: true, kind: "next_event", events: e.map { [$0] } ?? [], reminders: [], error: nil, mock: true, providerMode: "mock", providerName: "MockEventKitProvider")
        }
        let access = await provider.eventAccess()
        guard access == .authorized else {
            return CalendarToolResult(ok: false, kind: "next_event", events: [], reminders: [], error: "permission_denied", mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        }
        do {
            let e = try await provider.nextEvent()
            return CalendarToolResult(ok: true, kind: "next_event", events: e.map { [$0] } ?? [], reminders: [], error: nil, mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        } catch {
            return CalendarToolResult(ok: false, kind: "next_event", events: [], reminders: [], error: "unavailable", mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        }
    }

    func upcomingReminders() async -> CalendarToolResult {
        if useMock {
            let r = await mockProvider.upcomingReminders()
            return CalendarToolResult(ok: true, kind: "reminders", events: [], reminders: r, error: nil, mock: true, providerMode: "mock", providerName: "MockEventKitProvider")
        }
        let access = await provider.reminderAccess()
        guard access == .authorized else {
            return CalendarToolResult(ok: false, kind: "reminders", events: [], reminders: [], error: "permission_denied", mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        }
        do {
            let r = try await provider.upcomingReminders()
            return CalendarToolResult(ok: true, kind: "reminders", events: [], reminders: r, error: nil, mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        } catch {
            return CalendarToolResult(ok: false, kind: "reminders", events: [], reminders: [], error: "unavailable", mock: false, providerMode: "real", providerName: "AppleEventKitProvider")
        }
    }
}
