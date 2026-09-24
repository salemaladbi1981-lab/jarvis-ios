"""Stale-cancel regression.
Device evidence (console-session15): a manual mic interrupt fired response.cancel after
the response had already finished, the server answered
response_cancel_not_active / "Cancellation failed: no active response found", and the
client turned that into realtime_error — the red alert that cut the conversation.
response.cancel must go out only while the server still has an active response, and a
stale cancel must stay diagnostic. AA.7 (nearby speech never interrupts) is unchanged."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

src = open(os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift'), encoding='utf-8').read()
FUNC = re.compile(r'^    (?:private |@discardableResult )*func (\w+)', re.M)

def body(name):
    m = re.search(r'^    (?:private |@discardableResult )*func ' + name + r'\b.*$', src, re.M)
    if not m: return ''
    rest = src[m.end():]
    nxt = FUNC.search(rest)
    return rest[:nxt.start()] if nxt else rest

def arm(event):
    m = re.search(r'case\s+"' + re.escape(event) + r'"\s*:', src)
    if not m: return ''
    rest = src[m.end():]
    nxt = re.search(r'\n\s*(case\s+"|default\s*:)', rest)
    return rest[:nxt.start()] if nxt else rest

barge, interrupt = body('bargeIn'), body('interrupt')

check("bargeIn takes the active-response fact from its caller",
      'func bargeIn(hadActiveResponse: Bool)' in src)
check("response.cancel is sent only when a response was active",
      'if hadActiveResponse {' in barge and 'response.cancel' in barge
      and barge.index('if hadActiveResponse {') < barge.index('response.cancel'))
check("the local side of the barge still always runs",
      'conversation.item.truncate' in barge and 'audio.flush()' in barge
      and 'eventPublisher.send(.interrupted)' in barge)
check("interrupt reads currentResponseID before onBarge clears it",
      'let active = self.guardState.currentResponseID != nil' in interrupt
      and interrupt.index('currentResponseID != nil') < interrupt.index('onBarge()'))
check("interrupt passes that fact down", 'bargeIn(hadActiveResponse: hadActiveResponse)' in interrupt)
check("no caller can reach bargeIn without the fact",
      not re.search(r'bargeIn\(\s*\)', src))

err = arm('error')
check("a stale cancel is recognised by code",
      'SessionEventParser.nested(text, "error", "code")' in err
      and 'response_cancel_not_active' in err)
check("a stale cancel raises no realtime_error",
      err.index('response_cancel_not_active') < err.index('eventPublisher.send(.error("realtime_error"))'))
check("a stale cancel is logged for diagnosis",
      '[JARVIS-DIAG][error] ignored benign response_cancel_not_active' in err)
check("a stale cancel leaves the queued turn alone",
      err.index('break') < err.index('dropPendingResponseCreateOnStateQueue()'))
check("every other realtime error still raises the alert",
      'dropPendingResponseCreateOnStateQueue()' in err
      and 'eventPublisher.send(.error("realtime_error"))' in err)

# AA.7 must survive this change
started = arm('input_audio_buffer.speech_started')
check("AA.7 kept: nearby speech while speaking is still ignored",
      'speech_started while speaking ignored — protected playback' in started
      and 'response.cancel' not in started)
check("AA.7 kept: no call site schedules a confirmed voice barge-in",
      not re.search(r'^(?!.*func).*scheduleConfirmedVoiceBargeIn\(\)', src, re.M))


class Session:
    """Cancel policy: only an active response is cancelled; a stale cancel is quiet."""
    def __init__(self, active):
        self.active = active
        self.cancels = 0
        self.flushes = 0
        self.alerts = 0
    def interrupt(self):
        had = self.active is not None
        self.active = None
        if had: self.cancels += 1
        self.flushes += 1            # local stop always happens
    def server_error(self, code):
        if code == "response_cancel_not_active": return
        self.alerts += 1

a = Session("resp_1"); a.interrupt()
check("interrupting an active response cancels once", a.cancels == 1 and a.flushes == 1)
b = Session(None); b.interrupt()
check("interrupting nothing sends no cancel but still stops playback",
      b.cancels == 0 and b.flushes == 1)
b.server_error("response_cancel_not_active")
check("a stale cancel raises no alert", b.alerts == 0)
b.server_error("invalid_request_error")
check("a real error still raises the alert", b.alerts == 1)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
