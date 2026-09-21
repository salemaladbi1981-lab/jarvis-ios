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
    /// Meeting URL supplied by Apple's EventKit `EKEvent.url` only.
    /// JARVIS does not scrape notes/location for join links.
    let meetingURL: URL?

    init(id: String,
         title: String,
         start: Date,
         end: Date,
         isAllDay: Bool,
         calendarName: String?,
         location: String?,
         meetingURL: URL? = nil) {
        self.id = id
        self.title = title
        self.start = start
        self.end = end
        self.isAllDay = isAllDay
        self.calendarName = calendarName
        self.location = location
        self.meetingURL = meetingURL
    }
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

/// Providers that JARVIS may surface from a calendar-supplied HTTPS meeting URL.
/// This is an allowlist for eligibility only; it does not auto-open or auto-join anything.
enum MeetingProvider: String, Equatable {
    case zoom
    case googleMeet
    case microsoftTeams
    case webex
    case faceTime

    var displayName: String {
        switch self {
        case .zoom: return "Zoom"
        case .googleMeet: return "Google Meet"
        case .microsoftTeams: return "Microsoft Teams"
        case .webex: return "Webex"
        case .faceTime: return "FaceTime"
        }
    }
}

/// Safe, read-only meeting handoff candidate derived from an EventKit event.
/// Opening the URL must remain an explicit user action in the UI layer.
struct MeetingLaunchTarget: Identifiable, Equatable {
    let eventID: String
    let title: String
    let start: Date
    let url: URL
    let provider: MeetingProvider

    var id: String { eventID + "|" + url.absoluteString }
}

/// Conservative meeting-link policy: HTTPS + known provider host only.
/// No custom schemes, no arbitrary web links, no note/location scraping, no auto-join.
enum MeetingLinkPolicy {
    static func target(for event: JarvisCalendarEvent) -> MeetingLaunchTarget? {
        guard let url = event.meetingURL,
              let provider = provider(for: url) else { return nil }
        return MeetingLaunchTarget(eventID: event.id,
                                   title: event.title,
                                   start: event.start,
                                   url: url,
                                   provider: provider)
    }

    static func provider(for url: URL) -> MeetingProvider? {
        guard url.scheme?.lowercased() == "https",
              let host = url.host?.lowercased() else { return nil }

        if matches(host, domain: "zoom.us") { return .zoom }
        if host == "meet.google.com" { return .googleMeet }
        if host == "teams.microsoft.com" || host == "teams.live.com" { return .microsoftTeams }
        if matches(host, domain: "webex.com") { return .webex }
        if host == "facetime.apple.com" { return .faceTime }
        return nil
    }

    private static func matches(_ host: String, domain: String) -> Bool {
        host == domain || host.hasSuffix("." + domain)
    }
}

extension JarvisCalendarEvent {
    var meetingTarget: MeetingLaunchTarget? { MeetingLinkPolicy.target(for: self) }
}
