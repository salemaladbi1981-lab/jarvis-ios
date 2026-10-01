//
//  MockProviders.swift — Phase 3 integration seams.
//  Phase 2 uses mock implementations only. Phase 3 replaces them without UI rebuild.
//
import Foundation

// MARK: - Smart Home
public protocol SmartHomeProvider {
    /// قراءة الحالة (لا تحتاج موافقة).
    func readDevices() async -> [SmartDevice]
    /// تنفيذ فعل — يعيد false إذا تطلّب موافقة.
    func control(device: String, action: String) async throws -> Bool
}

public struct SmartDevice: Identifiable {
    public let id: String
    public let name: String
    public let value: String
}

// MARK: - Security
public protocol SecurityProvider {
    func status() async -> SecurityStatus?
    func execute(action: String) async throws -> Bool
}

public struct SecurityStatus {
    public let systemsNormal: Bool
    public let doorsLocked: Bool
    public let camerasActive: Bool
}

// MARK: - Calendar
public protocol CalendarProvider {
    func todayEvents() async -> [CalendarEvent]
}

public struct CalendarEvent: Identifiable {
    public let id: String
    public let time: String
    public let title: String
}

// MARK: - Tasks
public protocol TaskProvider {
    func tasks() async -> [TaskItem]
}

public struct TaskItem: Identifiable {
    public let id: String
    public let title: String
    public let done: Bool
}

// MARK: - Media
public protocol MediaProvider {
    func nowPlaying() async -> MediaTrack?
    func send(command: String) async throws -> Bool  // previous / play / next
}

public struct MediaTrack {
    public let title: String
    public let artist: String
    public let current: String
    public let duration: String
}

// MARK: - Weather
public protocol WeatherProvider {
    func current() async -> Weather
}

public struct Weather {
    public let temp: String
    public let condition: String
    public let highLow: String
    public let city: String
}

// MARK: - Voice
public protocol VoiceProvider {
    func start() async throws
    func stop()
    var isListening: Bool { get }
}

// MARK: - Agent State
public protocol AgentStateProvider {
    var currentState: JarvisState { get }
    var activeGroup: String { get }
    func setState(_ s: JarvisState)
    func setGroup(_ g: String)
}

/// Production defaults until authorized integrations are connected.
/// Absence is distinct from an unlocked door, a stopped player, or an empty home.
enum ProviderUnavailable: Error { case notConnected }

struct UnavailableSmartHomeProvider: SmartHomeProvider {
    func readDevices() async -> [SmartDevice] { [] }
    func control(device: String, action: String) async throws -> Bool { throw ProviderUnavailable.notConnected }
}

struct UnavailableSecurityProvider: SecurityProvider {
    func status() async -> SecurityStatus? { nil }
    func execute(action: String) async throws -> Bool { throw ProviderUnavailable.notConnected }
}

struct UnavailableMediaProvider: MediaProvider {
    func nowPlaying() async -> MediaTrack? { nil }
    func send(command: String) async throws -> Bool { throw ProviderUnavailable.notConnected }
}
