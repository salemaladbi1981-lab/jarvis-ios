"""BUG #4 regression: EKAuthorizationStatus mapping must not hide authorized as unavailable."""
import sys, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
prov = read('Integrations/AppleEventKitProvider.swift')
tools = read('Integrations/CalendarTools.swift')
vm = read('Home/HomeViewModel.swift')

# 1) كل حالة صالحة تُعالج صراحة (لا default يخفي authorized)
check("maps .notDetermined", 'case .notDetermined: return .notDetermined' in prov)
check("maps legacy .authorized → authorized", 'case .authorized:    return .authorized' in prov)
check("maps .fullAccess → authorized", 'case .fullAccess:    return .authorized' in prov)
check("maps .writeOnly → restricted", 'case .writeOnly:     return .restricted' in prov)
check("maps .denied → denied", 'case .denied:        return .denied' in prov)
check("maps .restricted → restricted", 'case .restricted:    return .restricted' in prov)
# 2) default لا يخفي authorized (authorized handled explicitly above)
check("default is unknown-only (not catch-all for valid states)", '@unknown default' in prov)
# 3) diagnostic present
check("accessDebugString present", 'func accessDebugString' in prov)
check("CalendarToolResult has debugReason", 'debugReason: String?' in tools)
check("reminders fetch reports count", 'fetched count=' in tools)
check("reminders error carries debugReason", 'debugReason: "access=' in tools or 'debugReason: "fetch error:' in tools)
# 4) runReminders non-catch-all
check("denied → specific message", 'صلاحية التذكيرات مرفوضة' in vm)
check("restricted → specific message", 'الوصول إلى التذكيرات مقيد' in vm)
check("default includes accessDebugString (not bare 'غير متاحة')", 'accessDebugString(.reminder)' in vm)
# 5) لا listening + لا mock
check("reminders path does not set listening", 'state = .listening' not in vm)
check("no mock fallback", 'CalendarTools(useMock: false)' in vm)
# 6) calendar regression
check("calendar still maps via shared map()", 'eventAccess() -> CalendarPermissionState' in prov and 'Self.map(' in prov)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
