"""Regression guard: Siri/App Intent voice handoffs cannot cross enrollment boundaries."""
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


enrollment = open(os.path.join(ROOT, 'JARVIS', 'Auth', 'EnrollmentManager.swift'), encoding='utf-8').read()
intent = open(os.path.join(ROOT, 'JARVIS', 'App', 'JarvisAppIntent.swift'), encoding='utf-8').read()
home_vm = open(os.path.join(ROOT, 'JARVIS', 'Home', 'HomeViewModel.swift'), encoding='utf-8').read()

check("voice App Intent remains authenticated and only arms a short-lived handoff",
      'static var authenticationPolicy: IntentAuthenticationPolicy = .requiresAuthentication' in intent and
      'AppBridge.pendingStartVoice = true' in intent and
      'startListening()' not in intent)

init_section = enrollment.split('init(baseURL: URL)', 1)[1].split('/// يُدخل الرمز', 1)[0]
check("unenrolled app launch clears any pending Siri voice handoff",
      'if sessionToken == nil' in init_section and
      'AppBridge.pendingStartVoice = false' in init_section)

enroll_section = enrollment.split('func enroll(code: String)', 1)[1].split('private func wire', 1)[0]
clear_index = enroll_section.find('AppBridge.pendingStartVoice = false')
enrolled_index = enroll_section.find('isEnrolled = true')
check("successful pairing clears pre-enrollment voice handoff before exposing authenticated UI",
      clear_index >= 0 and enrolled_index >= 0 and clear_index < enrolled_index)

check("enrollment boundary never arms or directly starts microphone capture",
      'AppBridge.pendingStartVoice = true' not in enrollment and
      'AudioCapture' not in enrollment and
      'startListening()' not in enrollment)

check("authenticated home still uses one-shot AppBridge consumption",
      'guard AppBridge.consumePendingStartVoice() else { return }' in home_vm and
      'toggleVoice()' in home_vm[home_vm.find('func handleAppIntentStart()'):home_vm.find('func handleAppBackgrounded()')])

check("bridge remains bounded and destructive on consume",
      'pendingStartVoiceMaxAge: TimeInterval = 30' in intent and
      'age >= 0, age <= pendingStartVoiceMaxAge' in intent and
      'UserDefaults.standard.removeObject(forKey: pendingStartVoiceKey)' in intent)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
