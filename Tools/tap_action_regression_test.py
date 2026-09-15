"""Regression: Quick Command taps are wired to real actions (calendar/reminders).
Source-level invariants — device tap still requires physical retest."""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
qs = read('Home/QuickSuggestions.swift')
vm = read('Home/HomeViewModel.swift')
hv = read('Home/HomeView.swift')

check("QuickSuggestions has onTapGesture", '.onTapGesture { onTap(s) }' in qs)
check("QuickSuggestions chip is hit-testable (contentShape)", '.contentShape(Capsule())' in qs)
check("QuickSuggestions exposes isButton trait", '.isButton' in qs)
check("HomeViewModel has handleQuickCommand", 'func handleQuickCommand' in vm)
check("'جدول' routes to calendar", '"جدول"' in vm and 'runCalendar' in vm)
check("'تذكير' routes to reminders", '"تذكير"' in vm and 'runReminders' in vm)
check("Calendar uses REAL provider (not mock)", 'CalendarTools(useMock: false)' in vm)
check("Calendar permission request is reachable", 'requestEvents()' in vm)
check("Reminders permission request is reachable", 'requestReminders()' in vm)
check("HomeView passes onTap to handleQuickCommand", 'vm.handleQuickCommand(text)' in hv)
check("HomeView displays calendar result", 'vm.calendarMessage' in hv)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
