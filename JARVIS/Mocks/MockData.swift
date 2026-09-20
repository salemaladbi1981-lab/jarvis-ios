import Foundation

/// Concrete demo providers for P2.2 screenshots / explicitly launched demo mode.
/// They must never return synthetic success/data in a normal production launch.
private enum DemoProviderGate {
    static var enabled: Bool {
        ProcessInfo.processInfo.arguments.contains("-demo")
    }
}

enum DemoProviderError: Error {
    case disabledOutsideDemoMode
}

struct MockSmartHomeProvider: SmartHomeProvider {
    func readDevices() async -> [SmartDevice] {
        guard DemoProviderGate.enabled else { return [] }
        return [
            SmartDevice(id: "light", name: "الإضاءة", value: "35%"),
            SmartDevice(id: "ac", name: "المكيف", value: "22°"),
            SmartDevice(id: "curtains", name: "الستائر", value: "مغلقة"),
            SmartDevice(id: "tv", name: "التلفزيون", value: "مطفأ"),
        ]
    }

    func control(device: String, action: String) async throws -> Bool {
        // A mock control must never report a production action as successful.
        DemoProviderGate.enabled
    }
}

struct MockSecurityProvider: SecurityProvider {
    func status() async -> SecurityStatus {
        guard DemoProviderGate.enabled else {
            // Conservative unknown/unavailable representation: never fabricate "all normal".
            return SecurityStatus(systemsNormal: false, doorsLocked: false, camerasActive: false)
        }
        return SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true)
    }

    func execute(action: String) async throws -> Bool {
        DemoProviderGate.enabled
    }
}

struct MockCalendarProvider: CalendarProvider {
    func todayEvents() async -> [CalendarEvent] {
        guard DemoProviderGate.enabled else { return [] }
        return [
            CalendarEvent(id: "e1", time: "09:00", title: "موعد"),
            CalendarEvent(id: "e2", time: "11:30", title: "موعد"),
            CalendarEvent(id: "e3", time: "01:00", title: "موعد"),
        ]
    }
}

struct MockTaskProvider: TaskProvider {
    func tasks() async -> [TaskItem] {
        guard DemoProviderGate.enabled else { return [] }
        return [
            TaskItem(id: "t1", title: "مراجعة خطة المحتوى", done: false),
            TaskItem(id: "t2", title: "اجتماع الاستوديو", done: true),
        ]
    }
}

struct MockMediaProvider: MediaProvider {
    func nowPlaying() async -> MediaTrack {
        guard DemoProviderGate.enabled else {
            return MediaTrack(title: "", artist: "", current: "", duration: "")
        }
        return MediaTrack(title: "Blinding Lights", artist: "The Weeknd", current: "2:06", duration: "3:20")
    }

    func send(command: String) async throws -> Bool {
        DemoProviderGate.enabled
    }
}

struct MockWeatherProvider: WeatherProvider {
    func current() async -> Weather {
        guard DemoProviderGate.enabled else {
            return Weather(temp: "", condition: "", highLow: "", city: "")
        }
        return Weather(temp: "28°", condition: "مشمس", highLow: "24° / 32°", city: "الدوحة")
    }
}

final class MockVoiceProvider: VoiceProvider {
    private(set) var isListening = false

    func start() async throws {
        guard DemoProviderGate.enabled else {
            throw DemoProviderError.disabledOutsideDemoMode
        }
        isListening = true
    }

    func stop() { isListening = false }
}
