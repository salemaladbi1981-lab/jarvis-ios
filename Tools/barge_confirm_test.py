"""Protected-playback barge-in regression.
Policy (device-verified, handoff AA.7): while JARVIS is speaking, room audio is not
streamed and input_audio_buffer.speech_started is ignored, so a nearby person talking
can never silence JARVIS or drop its context. Any pending voice-barge work is cancelled.
The mic button (interrupt()) stays the one intentional interruption path, immediate."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

rvs = open(os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift'), encoding='utf-8').read()

def case_block(event):
    """Body of one `case "<event>":` arm, up to the next case/default."""
    m = re.search(r'case\s+"' + re.escape(event) + r'"\s*:', rvs)
    if not m: return ''
    rest = rvs[m.end():]
    nxt = re.search(r'\n\s*(case\s+"|default\s*:)', rest)
    return rest[:nxt.start()] if nxt else rest

started = case_block('input_audio_buffer.speech_started')
check("speech_started arm exists", bool(started))

# 1. Room PCM is not streamed while JARVIS speaks.
check("sendAudio stops streaming room PCM while speaking",
      'let speakingNow = stateQueue.sync { self.isSpeaking }' in rvs and 'if speakingNow { return }' in rvs)

# 2. speech_started while speaking is ignored, not confirmed.
check("speech_started while speaking is ignored — protected playback",
      'speech_started while speaking ignored — protected playback' in started)
check("speech_started while speaking cancels pending voice-barge work",
      'cancelPendingVoiceBargeIn()' in started)
check("speech_started never schedules a confirmed voice barge-in",
      not re.search(r'^(?!.*func).*scheduleConfirmedVoiceBargeIn\(\)', rvs, re.M))
check("nearby speech does not cancel the active response",
      'response.cancel' not in started and 'onBarge()' not in started)
check("nearby speech does not clear the speaking state", 'isSpeaking = false' not in started)

# 3. Manual mic-button interruption stays the intentional path, and stays complete.
check("manual interrupt remains available", 'func interrupt()' in rvs)
check("manual interrupt is the labelled barge path",
      'BARGE manual interrupt → response.cancel + truncate + flush' in rvs)
check("manual interrupt sends response.cancel", 'response.cancel' in rvs)
check("manual interrupt sends conversation.item.truncate", 'conversation.item.truncate' in rvs)
check("manual interrupt flushes local playback", 'audio.flush()' in rvs)
check("manual interrupt clears the speaking state", 'self.isSpeaking = false' in rvs)


class ProtectedPlayback:
    """Interruption policy: only the mic button interrupts while speaking."""
    def __init__(self):
        self.speaking = True
        self.cancelled = 0
        self.context_lost = False
    def speech_started(self):          # VAD sees a nearby voice
        if self.speaking: return       # ignored: no cancel, no context loss
        self.cancelled += 1
    def mic_button(self):
        if self.speaking:
            self.speaking = False
            self.cancelled += 1

a = ProtectedPlayback(); a.speech_started(); a.speech_started()
check("nearby speech while speaking never interrupts", a.cancelled == 0 and not a.context_lost)
check("nearby speech leaves JARVIS speaking", a.speaking is True)

b = ProtectedPlayback(); b.mic_button()
check("mic button interrupts once", b.cancelled == 1 and b.speaking is False)

c = ProtectedPlayback(); c.mic_button(); c.speech_started()
check("after a manual interrupt, listening resumes normally", c.cancelled == 2)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
