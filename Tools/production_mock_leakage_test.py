"""Regression checks: synthetic providers must not fabricate production data/actions."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
mock = (root / "JARVIS/Mocks/MockData.swift").read_text(encoding="utf-8")
home = (root / "JARVIS/Home/HomeViewModel.swift").read_text(encoding="utf-8")
mac_home = (root / "JARVIS/macOS/MacHomeView.swift").read_text(encoding="utf-8")
calendar = (root / "JARVIS/Integrations/CalendarTools.swift").read_text(encoding="utf-8")

checks = {
    "demo providers require explicit -demo launch": 'ProcessInfo.processInfo.arguments.contains("-demo")' in mock,
    "smart-home synthetic reads are gated": 'guard DemoProviderGate.enabled else { return [] }' in mock,
    "mock controls cannot report production success": mock.count('DemoProviderGate.enabled') >= 7,
    "security provider does not fabricate normal production state": 'systemsNormal: false, doorsLocked: false, camerasActive: false' in mock,
    "mock voice refuses production activation": 'disabledOutsideDemoMode' in mock,
    "calendar tools default to real EventKit": 'init(useMock: Bool = false)' in calendar,
    "home calendar explicitly requests real path": 'CalendarTools(useMock: false)' in home,
    "mac provider cards require explicit demo mode": (
        'ProcessInfo.processInfo.arguments.contains("-demo")' in mac_home
        and 'if demoMode {' in mac_home
    ),
    "mac view has no synthetic security fallback": 'SecurityStatus(systemsNormal: true' not in mac_home,
    "mac view has no synthetic media fallback": 'Blinding Lights' not in mac_home,
    "mac production path states provider unavailability": 'البيانات المباشرة غير متصلة' in mac_home,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("Failed:", ", ".join(failed))
    sys.exit(1)
