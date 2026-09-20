"""Location stability (iOS source-level) — Core Location + real city + structured navigation handoff."""
import os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()

hdr = read('Home/HeaderView.swift')
lm = read('Providers/LocationManager.swift')
plist = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS', 'Info.plist'), encoding='utf-8').read()
mi = read('App/JarvisMapsIntent.swift')

check("HeaderView no hardcoded الدوحة", '"الدوحة"' not in hdr)
check("HeaderView uses LocationManager displayCity", 'location.displayCity' in hdr and 'LocationManager()' in hdr)
check("HeaderView requests location on appear", 'requestWhenNeeded()' in hdr)
check("LocationManager uses When In Use (no Always)", 'requestWhenInUseAuthorization' in lm and 'requestAlwaysAuthorization' not in lm)
check("LocationManager single read (requestLocation, no continuous)", 'manager.requestLocation()' in lm and 'startUpdatingLocation' not in lm)
check("LocationManager exposes unavailable state", 'الموقع غير متاح' in lm)
check("LocationManager handles denied/restricted", '.denied' in lm and '.restricted' in lm)
check("LocationManager has timeout", 'timeout' in lm.lower())
check("Info.plist NSLocationWhenInUseUsageDescription", 'NSLocationWhenInUseUsageDescription' in plist)
check(
    "JarvisMapsIntent structured dir_action=navigate",
    'URLComponents' in mi
    and 'URLQueryItem' in mi
    and 'name: "dir_action"' in mi
    and 'value: "navigate"' in mi,
)
check("JarvisMapsIntent leaves location ownership to Maps", 'CLLocationManager' not in mi)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(0 if FAIL == 0 else 1)
