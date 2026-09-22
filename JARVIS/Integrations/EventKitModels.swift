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
    let end: Date
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
                                   end: event.end,
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

/// Last-mile gate used immediately before the UI hands a URL to the operating system.
/// It never opens a URL itself. A caller must prove the action was initiated by the
/// user, and the target must still exactly match a freshly re-read EventKit event.
enum MeetingHandoffPolicy {
    static func revalidatedURL(for target: MeetingLaunchTarget,
                               current: MeetingLaunchTarget,
                               now: Date = Date(),
                               userInitiated: Bool) -> URL? {
        guard userInitiated,
              target.eventID == current.eventID,
              target.url == current.url,
              target.provider == current.provider,
              current.end >= now,
              MeetingLinkPolicy.provider(for: current.url) == current.provider else {
            return nil
        }
        return current.url
    }
}

/// Pure selection policy used by EventKit and future authorized calendar adapters.
/// It never opens a URL and never requests permissions. Only currently-valid or
/// upcoming timed events with an allow-listed `meetingURL` can become targets.
enum MeetingDiscoveryPolicy {
    static func upcomingTargets(from events: [JarvisCalendarEvent],
                                now: Date = Date(),
                                limit: Int = 10) -> [MeetingLaunchTarget] {
        let safeLimit = min(max(limit, 0), 20)
        guard safeLimit > 0 else { return [] }

        var seen = Set<String>()
        let targets = events
            .filter { !$0.isAllDay && $0.end >= now }
            .sorted {
                if $0.start == $1.start { return $0.id < $1.id }
                return $0.start < $1.start
            }
            .compactMap { event -> MeetingLaunchTarget? in
                guard let target = event.meetingTarget,
                      seen.insert(target.id).inserted else { return nil }
                return target
            }

        return Array(targets.prefix(safeLimit))
    }
}

extension JarvisCalendarEvent {
    var meetingTarget: MeetingLaunchTarget? { MeetingLinkPolicy.target(for: self) }
}
