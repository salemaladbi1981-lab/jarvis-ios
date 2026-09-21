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
maps_intent = open(os.path.join(ROOT, 'JARVIS', 'App', 'JarvisMapsIntent.swift'), encoding='utf-8').read()
shortcuts = open(os.path.join(ROOT, 'JARVIS', 'App', 'JarvisShortcuts.swift'), encoding='utf-8').read()
app = open(os.path.join(ROOT, 'JARVIS', 'App', 'JARVISApp.swift'), encoding='utf-8').read()
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
      'let age = now - requestedAt' in intent and
      'age >= 0, age <= pendingStartVoiceMaxAge' in intent and
      'removeObject(forKey: pendingStartVoiceKey)' in intent)

check("pending voice launch is consumed exactly once",
      'static func consumePendingStartVoice' in intent and
      'get { consumePendingStartVoice() }' in intent and
      intent.count('UserDefaults.standard.removeObject(forKey: pendingStartVoiceKey)') >= 2)

check("shortcut phrases expose the voice intent through AppShortcutsProvider",
      'struct JarvisShortcuts: AppShortcutsProvider' in shortcuts and
      'intent: JarvisVoiceIntent()' in shortcuts)

check("open-only lock-screen intent uses official App Intents and requires authentication",
      'struct JarvisOpenIntent: AppIntent' in intent and
      'static var openAppWhenRun: Bool = true' in intent.split('struct JarvisOpenIntent: AppIntent', 1)[1] and
      'static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication' in intent.split('struct JarvisOpenIntent: AppIntent', 1)[1])

open_intent_section = intent.split('struct JarvisOpenIntent: AppIntent', 1)[1]
check("open-only intent never arms the microphone and clears stale voice handoff",
      'AppBridge.pendingStartVoice = false' in open_intent_section and
      'AudioCapture' not in open_intent_section and
      'AVAudio' not in open_intent_section and
      'startListening()' not in open_intent_section)

voice_shortcut_section = shortcuts.split('intent: JarvisVoiceIntent()', 1)[1].split('AppShortcut(', 1)[0]
check("plain open phrases are separated from voice-start shortcut",
      'intent: JarvisOpenIntent()' in shortcuts and
      '"Open \\(.applicationName)"' in shortcuts and
      '"افتح \\(.applicationName)"' in shortcuts and
      '"Open \\(.applicationName)"' not in voice_shortcut_section and
      '"افتح \\(.applicationName)"' not in voice_shortcut_section)

check("app refreshes App Shortcut metadata on launch through Apple's provider API",
      'import AppIntents' in app and
      'JarvisShortcuts.updateAppShortcutParameters()' in app and
      'AudioCapture' not in app and
      'AVAudio' not in app)

check("production UI exposes official ShortcutsLink for device validation",
      'import AppIntents' in home and
      'ShortcutsLink()' in home and
      'JarvisShortcuts.updateAppShortcutParameters()' in home and
      'تحديث اختصارات Siri' in home)

check("navigation shortcut uses App Intents and requires authentication",
      'struct JarvisNavigateIntent: AppIntent' in maps_intent and
      'static var openAppWhenRun: Bool = true' in maps_intent and
      'static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication' in maps_intent)

check("navigation intent is not registered as an App Shortcut with open-ended text parameter",
      'intent: JarvisNavigateIntent()' not in shortcuts and
      'intent: JarvisVoiceIntent()' in shortcuts and
      'intent: JarvisOpenIntent()' in shortcuts)

check("navigation destination is normalized and bounded before handoff",
      'trimmingCharacters(in: .whitespacesAndNewlines)' in maps_intent and
      '!normalized.isEmpty' in maps_intent and
      'normalized.utf8.count <= 512' in maps_intent)

check("navigation handoff uses structured HTTPS URL components",
      'URLComponents(string: "https://www.google.com/maps/dir/")' in maps_intent and
      'URLQueryItem(name: "destination", value: normalized)' in maps_intent and
      'UIApplication.shared.open(url)' in maps_intent and
      'googlemaps://' not in maps_intent)

check("navigation intent does not request hidden location or microphone access",
      'CLLocationManager' not in maps_intent and
      'AVAudio' not in maps_intent and
      'AudioCapture' not in maps_intent)

check("production home consumes the one-shot intent request on cold launch",
      '.task {' in home and
      'voiceVM.handleAppIntentStart()' in home and
      'guard AppBridge.pendingStartVoice else { return }' in home_vm and
      'AppBridge.pendingStartVoice = false' in home_vm)

check("warm-resume path re-checks the one-shot Siri handoff when scene becomes active",
      'else if phase == .active' in home and
      'voiceVM.handleAppIntentStart()' in home[home.find('.onChange(of: scenePhase)'):])

check("microphone still goes through normal permission gate",
      'AudioCapture.micPermission()' in home_vm and
      'AudioCapture.requestMic()' in home_vm)

check("source does not implement an always-on wake word loop",
      'wakeWord' not in intent and
      'alwaysOn' not in intent and
      'startListening()' not in intent and
      'wakeWord' not in app and
      'alwaysOn' not in app)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
