#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
models = (ROOT / 'JARVIS/Integrations/EventKitModels.swift').read_text()
provider = (ROOT / 'JARVIS/Integrations/AppleEventKitProvider.swift').read_text()

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

failed = [name for name, ok in checks if not ok]
print(f'\nmeeting foundation: {len(checks)-len(failed)}/{len(checks)} checks passed')
if failed:
    raise SystemExit(1)
