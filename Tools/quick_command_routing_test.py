"""Regression matrix: every Quick Command has a stable ID, correct route, honest status,
and no non-voice command triggers listening."""
import sys, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

qc = read('Home/QuickCommand.swift')
vm = read('Home/HomeViewModel.swift')
qs = read('Home/QuickSuggestions.swift')

# 1) 5 stable unique IDs
cases = re.findall(r'^    case (\w+)$', qc, re.M)   # enum cases only (no '.')
check("6 quick commands defined", len(cases) == 6)
check("command IDs unique", len(set(cases)) == 6)
for c in ["calendar","reminders","tomorrow","focus","doorCamera","calmMedia"]:
    check(f"has '{c}'", c in cases)

# 2) labels present (Arabic displayed text is not the routing key)
for lbl in ["وش عندي في الجدول؟","بطلع بكرة؟","فعّل وضع التركيز","ورّني كاميرا الباب","شغّل شي هادي"]:
    check(f"label '{lbl}' present", lbl in qc)

# 3) typed routing — no fragile text matching in handler
check("handler uses switch on QuickCommand (not text.contains)", 'switch cmd' in vm and 'contains(' not in vm)

# 4) calendar routes to calendar path; others to unavailable (not listening)
check("calendar → runCalendar", 'case .calendar' in vm and 'runCalendar' in vm)
check("tomorrow → unavailable (alert, NOT listening)", 'case .tomorrow' in vm and 'state = .alert' in vm)
check("focus/doorCamera/calmMedia → unavailable", 'case .tomorrow, .focus, .doorCamera, .calmMedia' in vm)

# 5) no non-voice command sets listening
check("no 'state = .listening' in quick-command handler", 'state = .listening' not in vm)

# 6) honest statuses
check("calendar status verified", 'case .calendar:   return .verified' in qc)
check("tomorrow status unavailable", 'case .tomorrow:   return .unavailable' in qc)
check("doorCamera status experimental", 'case .doorCamera: return .experimental' in qc)

# 7) real provider not mock in calendar path
check("calendar uses real provider", 'CalendarTools(useMock: false)' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
