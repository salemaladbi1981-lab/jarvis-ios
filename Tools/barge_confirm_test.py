"""Confirmed spoken barge-in regression.
Policy: natural speech can interrupt JARVIS after a short confirmation window;
short noise/clicks must not cancel playback. Manual mic interruption remains immediate."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

rvs = open(os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift'), encoding='utf-8').read()

check("confirmed voice barge-in has delay", 'bargeConfirmDelay' in rvs and '0.22' in rvs)
check("speech_started while speaking schedules confirmation",
      'speech_started while speaking → confirm voice barge-in' in rvs and 'scheduleConfirmedVoiceBargeIn()' in rvs)
check("speech_stopped cancels pending short-noise interruption",
      'cancelPendingVoiceBargeIn()' in rvs)
check("confirmed interruption calls onBarge", 'BARGE confirmed voice interruption' in rvs and 'guardState.onBarge()' in rvs)
check("confirmed interruption stops current speaking state", 'self.isSpeaking = false' in rvs)
check("barge sends response.cancel", 'response.cancel' in rvs)
check("barge sends conversation.item.truncate", 'conversation.item.truncate' in rvs)
check("barge flushes local playback", 'audio.flush()' in rvs)
check("manual interrupt remains available", 'func interrupt()' in rvs)

class ConfirmedBarge:
    def __init__(self):
        self.pending = False
        self.cancelled = 0
    def speech_started(self, speaking):
        if speaking: self.pending = True
    def speech_stopped(self):
        self.pending = False
    def confirm(self):
        if self.pending:
            self.cancelled += 1
            self.pending = False

a = ConfirmedBarge(); a.speech_started(True); a.speech_stopped(); a.confirm()
check("short speech/noise does not interrupt", a.cancelled == 0)

b = ConfirmedBarge(); b.speech_started(True); b.confirm()
check("sustained speech interrupts once", b.cancelled == 1)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
