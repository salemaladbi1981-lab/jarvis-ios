"""Regression guard for EventKit full-access privacy keys on iOS 17+."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PLIST = (ROOT / "JARVIS" / "Info.plist").read_text(encoding="utf-8")
GEN = (ROOT / "generate_project.py").read_text(encoding="utf-8")
PROVIDER = (ROOT / "JARVIS" / "Integrations" / "AppleEventKitProvider.swift").read_text(encoding="utf-8")

checks = [
    ("calendar full-access key exists", "NSCalendarsFullAccessUsageDescription" in PLIST),
    ("reminders full-access key exists", "NSRemindersFullAccessUsageDescription" in PLIST),
    ("calendar full-access key preserved by generator", "INFOPLIST_KEY_NSCalendarsFullAccessUsageDescription" in GEN),
    ("reminders full-access key preserved by generator", "INFOPLIST_KEY_NSRemindersFullAccessUsageDescription" in GEN),
    ("calendar provider requests full access", "requestFullAccessToEvents()" in PROVIDER),
    ("reminders provider requests full access", "requestFullAccessToReminders()" in PROVIDER),
]

failed = []
for name, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + name)
    if not ok:
        failed.append(name)

print(f"\ncalendar full-access privacy: {len(checks)-len(failed)}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
