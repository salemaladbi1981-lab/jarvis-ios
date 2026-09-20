"""Production mock guard: real runtime must not silently present demo data as live state."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0

def read(path):
    return open(os.path.join(ROOT, path), encoding='utf-8').read()

def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

vm = read('Home/HomeViewModel.swift')
mock = read('Mocks/MockData.swift')
home = read('Home/HomeView.swift')
mac = read('macOS/MacHomeView.swift')

check("production HomeViewModel defaults are optional, not mocks",
      'smartHome: SmartHomeProvider? = nil' in vm and
      'security: SecurityProvider? = nil' in vm and
      'media: MediaProvider? = nil' in vm)

check("mocks are restricted to -demo runtime",
      'ProcessInfo.processInfo.arguments.contains("-demo")' in vm and
      'demoRuntime ? MockSmartHomeProvider() : UnavailableSmartHomeProvider()' in vm and
      'demoRuntime ? MockSecurityProvider() : UnavailableSecurityProvider()' in vm and
      'demoRuntime ? MockMediaProvider() : UnavailableMediaProvider()' in vm)

check("unavailable providers exist",
      'struct UnavailableSmartHomeProvider' in mock and
      'struct UnavailableSecurityProvider' in mock and
      'struct UnavailableMediaProvider' in mock)

check("production load leaves security/media unknown instead of fake",
      'securityStatus = nil' in vm and 'mediaTrack = nil' in vm)

check("iOS HomeView has no hard-coded all-normal security fallback",
      'SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true)' not in home)

check("iOS HomeView has no hard-coded fake media track",
      'Blinding Lights' not in home and 'The Weeknd' not in home)

check("macOS Home has no hard-coded all-normal security fallback",
      'SecurityStatus(systemsNormal: true, doorsLocked: true, camerasActive: true)' not in mac)

check("macOS Home has no hard-coded fake media track",
      'Blinding Lights' not in mac and 'The Weeknd' not in mac)

check("unavailable UI is explicit",
      'غير متصل' in home and 'غير متصل' in mac)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
