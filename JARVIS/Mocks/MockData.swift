import Foundation

/// Concrete mock providers for screenshots/demo mode only.
/// Production defaults use explicit unavailable providers so the UI never presents
/// fabricated device/security/media state as real user data.

enum ProviderUnavailableError: LocalizedError {
    case notConnected(String)

    var errorDescription: String? {
        switch self {
        case .notConnected(let capability):
            return "\(capability) غير متصل"
        }
    }
}

// MARK: - Production-safe unavailable providers

struct UnavailableSmartHomeProvider: SmartHomeProvider {
    func readDevices() async -> [SmartDevice] { [] }
    func control(device: String, action: String) async throws -> Bool {
        throw ProviderUnavailableError.notConnected("المنزل الذكي")
    }
}

struct UnavailableSecurityProvider: SecurityProvider {
    func status() async -> SecurityStatus {
        // HomeViewModel intentionally does not expose this placeholder as live status.
        SecurityStatus(systemsNormal: false, doorsLocked: false, camerasActive: false)
    }
    func execute(action: String) async throws -> Bool {
        throw ProviderUnavailableError.notConnected("الأمان")
    }
}

struct UnavailableMediaProvider: MediaProvider {
    func nowPlaying() async -> MediaTrack {
        // HomeViewModel intentionally does not expose this placeholder as live media.
        MediaTrack(title: "", artist: "", current: "", duration: "")
    }
    func send(command: String) async throws -> Bool {
        throw ProviderUnavailableError.notConnected("الوسائط")
    }
}

// MARK: - Demo/screenshot providers

struct MockSmartHomeProvider: SmartHomeProvider {
    func readDevices() async -> [SmartDevice] {
        [
            SmartDevice(id: "light", name: "الإضاءة", value: "35%"),
            SmartDevice(id: "ac", name: "المكيف", value: "22°"),
            SmartDevice(id: "curtains", name: "الستائر", value: "مغلقة"),
            SmartDevice(id: "tv", name: "التلفزيون", value: "مطفأ"),
        ]
    }
    func control(device: String, action: String) async throws -> Bool { true }
}

struct MockSecurityProvider: SecurityProvider {
    func status() async -> SecurityStatus {
        SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true)
    }
    func execute(action: String) async throws -> Bool { true }
}

struct MockCalendarProvider: CalendarProvider {
    func todayEvents() async -> [CalendarEvent] {
        [
            CalendarEvent(id: "e1", time: "09:00", title: "موعد"),
            CalendarEvent(id: "e2", time: "11:30", title: "موعد"),
            CalendarEvent(id: "e3", time: "01:00", title: "موعد"),
        ]
    }
}

struct MockTaskProvider: TaskProvider {
    func tasks() async -> [TaskItem] {
        [
            TaskItem(id: "t1", title: "مراجعة خطة المحتوى", done: false),
            TaskItem(id: "t2", title: "اجتماع الاستوديو", done: true),
        ]
    }
}

struct MockMediaProvider: MediaProvider {
    func nowPlaying() async -> MediaTrack {
        MediaTrack(title: "Blinding Lights", artist: "The Weeknd", current: "2:06", duration: "3:20")
    }
    func send(command: String) async throws -> Bool { true }
}

struct MockWeatherProvider: WeatherProvider {
    func current() async -> Weather {
        Weather(temp: "28°", condition: "مشمس", highLow: "24° / 32°", city: "الدوحة")
    }
}

final class MockVoiceProvider: VoiceProvider {
    private(set) var isListening = false
    func start() async throws { isListening = true }
    func stop() { isListening = false }
}
