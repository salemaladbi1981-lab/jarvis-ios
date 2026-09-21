#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
models = (ROOT / 'JARVIS/Integrations/EventKitModels.swift').read_text()
provider = (ROOT / 'JARVIS/Integrations/AppleEventKitProvider.swift').read_text()
home_vm = (ROOT / 'JARVIS/Home/HomeViewModel.swift').read_text()
home = (ROOT / 'JARVIS/Workspace/HomeEntryView.swift').read_text()

checks = []
def check(name, ok):
    checks.append((name, bool(ok)))
    print(('PASS' if ok else 'FAIL') + ': ' + name)

check('Calendar model carries optional meeting URL', 'let meetingURL: URL?' in models and 'meetingURL: URL? = nil' in models)
check('Meeting target is read-only domain data', 'struct MeetingLaunchTarget: Identifiable, Equatable' in models)
check('Meeting target keeps event end for stale-link rejection', 'let end: Date' in models and 'end: event.end' in models)
check('Meeting policy requires HTTPS', 'url.scheme?.lowercased() == "https"' in models)
check('Meeting policy uses exact/subdomain boundary matching', 'host == domain || host.hasSuffix("." + domain)' in models)
check('Zoom allowlisted', 'domain: "zoom.us"' in models)
check('Google Meet allowlisted', 'host == "meet.google.com"' in models)
check('Microsoft Teams allowlisted', 'host == "teams.microsoft.com" || host == "teams.live.com"' in models)
check('Webex allowlisted', 'domain: "webex.com"' in models)
check('FaceTime allowlisted', 'host == "facetime.apple.com"' in models)
check('Unknown hosts fail closed', 'return nil' in models)
check('EventKit supplies meeting URL directly', 'meetingURL: ek.url' in provider)
check('Provider does not scrape event notes for links', 'ek.notes' not in provider)
check('Provider does not parse location as a link', 'meetingURL: ek.location' not in provider)
check('Foundation documents explicit-user-action handoff', 'explicit user action' in models)
check('Foundation documents no auto-join', 'no auto-join' in models)
check('No custom URL schemes are allowlisted', 'zoommtg:' not in models and 'msteams:' not in models and 'facetime://' not in models)

# Authorized upcoming-meeting discovery remains read-only and fail-closed.
check('Pure upcoming meeting selector exists', 'enum MeetingDiscoveryPolicy' in models and 'static func upcomingTargets' in models)
check('Discovery excludes all-day and ended events', '.filter { !$0.isAllDay && $0.end >= now }' in models)
check('Discovery caps result size', 'let safeLimit = min(max(limit, 0), 20)' in models and 'targets.prefix(safeLimit)' in models)
check('Discovery deduplicates launch targets', 'var seen = Set<String>()' in models and 'seen.insert(target.id).inserted' in models)
check('Provider exposes upcoming meeting discovery', 'func upcomingMeetingTargets' in provider)
check('Meeting discovery requires existing EventKit authorization', 'guard eventAccess() == .authorized else { return [] }' in provider)
check('Meeting discovery horizon is bounded', 'let safeDays = min(max(horizonDays, 1), 30)' in provider)
check('Meeting discovery can retain an in-progress meeting', 'value: -12, to: now' in provider and '$0.end >= now' in models)
check('Provider delegates eligibility to pure policy', 'MeetingDiscoveryPolicy.upcomingTargets(from: events, now: now, limit: limit)' in provider)
check('Meeting foundation does not auto-open URLs', 'UIApplication.shared.open' not in provider and 'UIApplication.shared.open' not in models)
check('Meeting foundation does not silently request access during discovery', 'upcomingMeetingTargets' in provider and 'guard eventAccess() == .authorized' in provider)

# Explicit handoff must be revalidated against a fresh EventKit read.
check('Handoff policy requires explicit user initiation', 'enum MeetingHandoffPolicy' in models and 'guard userInitiated' in models)
check('Handoff policy rejects stale or changed targets', 'target == current' in models)
check('Handoff policy rejects ended meetings', 'current.end >= now' in models)
check('Handoff policy revalidates provider allowlist', 'MeetingLinkPolicy.provider(for: current.url) == current.provider' in models)
check('Provider re-reads EventKit event by identifier before handoff', 'store.event(withIdentifier: target.eventID)' in provider)
check('Provider handoff requires existing authorization', 'func handoffURL' in provider and 'eventAccess() == .authorized' in provider)
check('Provider rejects all-day handoff after re-read', 'guard !currentEvent.isAllDay' in provider)
check('Provider delegates final URL gate to handoff policy', 'MeetingHandoffPolicy.revalidatedURL' in provider)
check('Provider handoff never requests EventKit permission', 'func handoffURL' in provider and 'requestEvents()' in provider and 'requestEvents()' not in provider.split('func handoffURL', 1)[1].split('func upcomingReminders', 1)[0])

# Production UI integration: discovery is explicit, opening is a user tap, and
# the URL is revalidated immediately before SwiftUI hands it to the OS.
check('Home VM publishes authorized meeting targets', '@Published private(set) var meetingTargets: [MeetingLaunchTarget]' in home_vm)
check('UI refresh can request EventKit permission only from explicit refresh', 'refreshMeetings(requestPermissionIfNeeded: true)' in home)
check('Background meeting refresh does not silently request permission', 'if access == .notDetermined && requestPermissionIfNeeded' in home_vm)
check('Home VM exposes revalidated handoff only', 'func meetingHandoffURL(for target: MeetingLaunchTarget) -> URL?' in home_vm and 'calendarProvider.handoffURL(for: target, userInitiated: true)' in home_vm)
check('Meeting UI injects SwiftUI openURL environment', '@Environment(\\.openURL) private var openURL' in home)
check('Meeting UI opens only after revalidation', 'guard let url = voiceVM.meetingHandoffURL(for: meeting)' in home and 'openURL(url)' in home)
check('Meeting UI has explicit open button', 'Button("فتح")' in home and '.accessibilityLabel("فتح اجتماع \\(meeting.title)")' in home)
check('Meeting UI does not auto-open on discovery', 'onAppear' not in home.split('Label("الاجتماعات القادمة"', 1)[1].split('// نقطة دخول واضحة', 1)[0])
check('Meeting UI uses gold cinematic shell', 'Label("الاجتماعات القادمة"' in home and 'stroke(JarvisColor.primary_gold.opacity(0.16)' in home)

# Milestone ownership intentionally lives in Project Health tests. Meeting regression
# must not pin the global roadmap to this already-built foundation.

failed = [name for name, ok in checks if not ok]
print(f'\nmeeting foundation: {len(checks)-len(failed)}/{len(checks)} checks passed')
if failed:
    raise SystemExit(1)
