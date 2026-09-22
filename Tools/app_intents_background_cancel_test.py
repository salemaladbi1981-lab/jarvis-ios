"""Regression: abandoned Siri voice handoffs must not survive an app background transition."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP_DELEGATE = (ROOT / "JARVIS" / "App" / "AppDelegate.swift").read_text(encoding="utf-8")
INTENT = (ROOT / "JARVIS" / "App" / "JarvisAppIntent.swift").read_text(encoding="utf-8")

PASS = FAIL = 0


def check(name: str, condition: bool) -> None:
    global PASS, FAIL
    print(("  PASS  " if condition else "  FAIL  ") + name)
    if condition:
        PASS += 1
    else:
        FAIL += 1


check(
    "iOS delegate has an explicit background lifecycle boundary",
    "func applicationDidEnterBackground(_ application: UIApplication)" in APP_DELEGATE,
)

background = APP_DELEGATE.split(
    "func applicationDidEnterBackground(_ application: UIApplication)", 1
)[1].split("func application(_ application: UIApplication,", 1)[0]

check(
    "backgrounding cancels any unconsumed Siri voice handoff",
    "AppBridge.pendingStartVoice = false" in background,
)

check(
    "background lifecycle never starts microphone or audio work",
    "AudioCapture" not in background
    and "AVAudio" not in background
    and "startListening" not in background
    and "toggleVoice" not in background,
)

check(
    "voice handoff remains one-shot and short lived",
    "static func consumePendingStartVoice" in INTENT
    and "pendingStartVoiceMaxAge: TimeInterval = 30" in INTENT
    and "removeObject(forKey: pendingStartVoiceKey)" in INTENT,
)

check(
    "Siri voice intent still requires authentication and opens the app officially",
    "static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication" in INTENT
    and "static var openAppWhenRun: Bool = true" in INTENT,
)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
