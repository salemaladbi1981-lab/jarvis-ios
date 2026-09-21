#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
models = (ROOT / 'JARVIS/Integrations/EventKitModels.swift').read_text()
provider = (ROOT / 'JARVIS/Integrations/AppleEventKitProvider.swift').read_text()
plan = (ROOT / 'docs/PROJECT-HEALTH-PLAN.json').read_text()

checks = []
def check(name, ok):
    checks.append((name, bool(ok)))
    print(('PASS' if ok else 'FAIL') + ': ' + name)

check('Calendar model carries optional meeting URL', 'let meetingURL: URL?' in models and 'meetingURL: URL? = nil' in models)
check('Meeting target is read-only domain data', 'struct MeetingLaunchTarget: Identifiable, Equatable' in models)
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
check('Meeting discovery can retain an in-progress meeting', 'value: -12, to: now' in provider and 'event.end >= now' in models)
check('Provider delegates eligibility to pure policy', 'MeetingDiscoveryPolicy.upcomingTargets(from: events, now: now, limit: limit)' in provider)
check('Meeting foundation does not auto-open URLs', 'UIApplication.shared.open' not in provider and 'UIApplication.shared.open' not in models)
check('Meeting foundation does not silently request access during discovery', 'upcomingMeetingTargets' in provider and 'guard eventAccess() == .authorized' in provider)

check('Project Health plan identifies Meeting foundation as current milestone', '"current_milestone": "Meeting foundation' in plan)
check('Project Health plan keeps physical device acceptance as next milestone', '"next_milestone": "Physical device acceptance' in plan)

failed = [name for name, ok in checks if not ok]
print(f'\nmeeting foundation: {len(checks)-len(failed)}/{len(checks)} checks passed')
if failed:
    raise SystemExit(1)
