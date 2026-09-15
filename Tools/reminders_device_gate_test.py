"""M3.4 Reminders Device Gate — regression (source-level). Physical retest required."""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
qc = read('Home/QuickCommand.swift')
vm = read('Home/HomeViewModel.swift')

# 1) reminders ID فريد + typed
check("reminders is a typed QuickCommand case", 'case reminders' in qc)
check("reminders label 'وش عندي من تذكيرات؟'", 'وش عندي من تذكيرات؟' in qc)
# 2) status = IMPLEMENTED / DEVICE-PENDING (ليس verified بعد)
check("reminders status = devicePending (not verified)", 'case .reminders: return .devicePending' in qc)
# 3) tap → handler → runReminders
check("reminders routes to runReminders", 'case .reminders' in vm and 'runReminders' in vm)
# 4) real provider (ليس mock)
check("uses real provider (not mock)", 'CalendarTools(useMock: false)' in vm)
# 5) notDetermined → requestReminders reachable
check("requestReminders reachable", 'requestReminders()' in vm)
# 6) authorized → upcomingReminders path
check("upcomingReminders path", 'upcomingReminders()' in vm)
# 7) denied → structured denied message
check("denied structured message", 'صلاحية التذكيرات مرفوضة' in vm)
# 8) empty state message
check("empty state 'لا توجد تذكيرات قادمة'", 'لا توجد تذكيرات قادمة' in vm)
# 9) provider error structured
check("provider error structured", 'التذكيرات غير متاحة' in vm)
# 10) reminders لا يغيّر listening
check("reminders path does not set listening", 'state = .listening' not in vm)
# 11) calendar لا يتراجع
check("calendar still routes to runCalendar", 'case .calendar' in vm and 'runCalendar' in vm)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
