"""Regression: Siri/Shortcuts intents use Apple foreground/main-app execution contracts."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INTENT = (ROOT / "JARVIS/App/JarvisAppIntent.swift").read_text(encoding="utf-8")
MAPS = (ROOT / "JARVIS/App/JarvisMapsIntent.swift").read_text(encoding="utf-8")

PASS = FAIL = 0

def check(name, condition):
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition: PASS += 1
    else: FAIL += 1

def section(source, name):
    return source.split(f"struct {name}: AppIntent", 1)[1].split("struct ", 1)[0]

for source, name in [(INTENT, "JarvisVoiceIntent"), (INTENT, "JarvisOpenIntent"), (MAPS, "JarvisNavigateIntent")]:
    body = section(source, name)
    check(f"{name} keeps pre-iOS-26 open-app compatibility", "static var openAppWhenRun: Bool = true" in body)
    check(f"{name} uses immediate foreground mode on iOS 26+", "#if compiler(>=6.2)" in body and "@available(iOS 26.0, *)" in body and "static var supportedModes: IntentModes { .foreground(.immediate) }" in body)
    check(f"{name} executes in main app on iOS 27+", "#if compiler(>=6.4)" in body and "@available(iOS 27.0, *)" in body and "static var allowedExecutionTargets: IntentExecutionTargets { .main }" in body)
    check(f"{name} remains authenticated", "authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication" in body)

check("voice intent never starts audio inside AppIntent perform", "startListening()" not in section(INTENT, "JarvisVoiceIntent") and "AudioCapture" not in section(INTENT, "JarvisVoiceIntent"))
check("open intent never arms voice capture", "pendingStartVoice = true" not in section(INTENT, "JarvisOpenIntent"))
check("navigation intent has no hidden location capture", "CLLocationManager" not in MAPS)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
