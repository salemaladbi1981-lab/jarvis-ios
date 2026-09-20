"""Regression guard for the official Siri / App Intents voice-launch foundation."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PASS = FAIL = 0


def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond:
        PASS += 1
    else:
        FAIL += 1


intent = open(os.path.join(ROOT, 'JARVIS', 'App', 'JarvisAppIntent.swift'), encoding='utf-8').read()
shortcuts = open(os.path.join(ROOT, 'JARVIS', 'App', 'JarvisShortcuts.swift'), encoding='utf-8').read()
home = open(os.path.join(ROOT, 'JARVIS', 'Workspace', 'HomeEntryView.swift'), encoding='utf-8').read()
home_vm = open(os.path.join(ROOT, 'JARVIS', 'Home', 'HomeViewModel.swift'), encoding='utf-8').read()

check("voice launch uses official App Intents framework",
      'import AppIntents' in intent and 'struct JarvisVoiceIntent: AppIntent' in intent)

check("voice launch requires authentication on locked device",
      'static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication' in intent)

check("intent asks the system to open the app instead of starting hidden audio",
      'static var openAppWhenRun: Bool = true' in intent and
      'AppBridge.pendingStartVoice = true' in intent and
      'AudioCapture' not in intent and
      'AVAudio' not in intent)

check("pending voice launch is short-lived instead of indefinitely sticky",
      'pendingStartVoiceMaxAge: TimeInterval = 30' in intent and
      'Date().timeIntervalSince1970 - requestedAt' in intent and
      'age >= 0, age <= pendingStartVoiceMaxAge' in intent and
      'removeObject(forKey: pendingStartVoiceKey)' in intent)

check("shortcut phrases expose the intent through AppShortcutsProvider",
      'struct JarvisShortcuts: AppShortcutsProvider' in shortcuts and
      'intent: JarvisVoiceIntent()' in shortcuts)

check("production home consumes the one-shot intent request",
      'voiceVM.handleAppIntentStart()' in home and
      'guard AppBridge.pendingStartVoice else { return }' in home_vm and
      'AppBridge.pendingStartVoice = false' in home_vm)

check("microphone still goes through normal permission gate",
      'AudioCapture.micPermission()' in home_vm and
      'AudioCapture.requestMic()' in home_vm)

check("source does not implement an always-on wake word loop",
      'wakeWord' not in intent and
      'alwaysOn' not in intent and
      'startListening()' not in intent)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
