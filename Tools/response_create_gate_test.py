"""response.create serialisation regression.
Policy: Realtime rejects a second response.create while one is active
(conversation_already_has_active_response). Every client-originated create must pass
the gate in gateResponseCreate — queued while a response is active or JARVIS speaks,
replayed when the slot frees. Only the authoritative device path
(sendGroundedDeviceResult) may create immediately, because it cancels first."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

PATH = os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift')
src = open(PATH, encoding='utf-8').read()
lines = src.split('\n')

FUNC = re.compile(r'^    (?:private |@discardableResult )*func (\w+)', re.M)
ALLOWED = {'transmitResponseCreate', 'sendGroundedDeviceResult'}

def enclosing_func(index):
    """Name of the method a line belongs to (methods are declared at 4 spaces)."""
    for i in range(index, -1, -1):
        m = FUNC.match(lines[i])
        if m: return m.group(1)
    return None

def body(name):
    m = re.search(r'^    (?:private |@discardableResult )*func ' + name + r'\b.*$', src, re.M)
    if not m: return ''
    rest = src[m.end():]
    nxt = FUNC.search(rest.replace('\r', ''))
    return rest[:nxt.start()] if nxt else rest

creates = [(n + 1, enclosing_func(n)) for n, l in enumerate(lines) if '"type":"response.create"' in l]
outside = [(n, f) for n, f in creates if f not in ALLOWED]

check("file still creates responses at all", bool(creates))
check("every response.create sits behind the gate (transmit) or the device path", not outside)
if outside:
    for n, f in outside:
        print(f"        ungated response.create at line {n} in {f or '<file scope>'}")

req, txt = body('requestResponse'), body('sendText')
check("requestResponse goes through the gate", 'gateResponseCreate(.plain)' in req)
check("requestResponse sends nothing itself", 'ws?.send' not in req)
check("sendText goes through the gate", 'gateResponseCreate(.text(' in txt)
check("sendText sends nothing itself", 'ws?.send' not in txt)

gate = body('gateResponseCreate')
check("gate blocks while a response is active", 'guardState.currentResponseID != nil' in gate)
check("gate blocks while JARVIS is speaking", 'isSpeaking' in gate)
check("gate queues the newest request", 'self.pendingResponseCreate = request' in gate)
check("gate clears the queue entry it sends now", 'self.pendingResponseCreate = nil' in gate)

flush = body('flushPendingResponseCreateOnStateQueue')
check("flush only fires when the slot is free",
      'guardState.currentResponseID == nil' in flush and '!isSpeaking' in flush)
check("flush consumes the queued request once", 'pendingResponseCreate = nil' in flush)

def arm(event):
    m = re.search(r'case\s+"' + re.escape(event) + r'"\s*:', src)
    if not m: return ''
    rest = src[m.end():]
    nxt = re.search(r'\n\s*(case\s+"|default\s*:)', rest)
    return rest[:nxt.start()] if nxt else rest

check("response.done replays the queued turn",
      'flushPendingResponseCreateOnStateQueue()' in arm('response.done'))
check("response.cancelled frees the slot and replays",
      'guardState.onBarge()' in arm('response.cancelled')
      and 'flushPendingResponseCreateOnStateQueue()' in arm('response.cancelled'))
check("a realtime error clears the queue",
      'dropPendingResponseCreateOnStateQueue()' in arm('error'))
check("stopListening clears the queue",
      'dropPendingResponseCreateOnStateQueue()' in body('stopListening'))
check("manual interrupt clears the queue",
      'dropPendingResponseCreateOnStateQueue()' in body('interrupt'))
check("device grounding still creates immediately after cancelling",
      'response.cancel' in body('sendGroundedDeviceResult')
      and '"type":"response.create"' in body('sendGroundedDeviceResult'))


class Gate:
    """The gate's contract: at most one create in flight, newest queued turn wins."""
    def __init__(self):
        self.active = False
        self.speaking = False
        self.pending = None
        self.sent = []
    def create(self, turn):
        if self.active or self.speaking:
            self.pending = turn            # newest replaces older
            return
        self.pending = None
        self.active = True
        self.sent.append(turn)
    def done(self):
        self.active = False
        self.speaking = False
        if self.pending is not None:
            turn, self.pending = self.pending, None
            self.active = True
            self.sent.append(turn)
    def error(self):
        self.pending = None

g = Gate(); g.create("a"); g.create("b")
check("a second create while active is not sent", g.sent == ["a"])
g.done()
check("the queued turn is sent on done", g.sent == ["a", "b"])
g2 = Gate(); g2.create("a"); g2.create("b"); g2.create("c"); g2.done()
check("only the newest queued turn survives", g2.sent == ["a", "c"])
g3 = Gate(); g3.create("a"); g3.create("b"); g3.error(); g3.done()
check("an error leaves nothing queued", g3.sent == ["a"] and g3.pending is None)
g4 = Gate(); g4.speaking = True; g4.create("a")
check("nothing is sent while speaking", g4.sent == [])
g4.done()
check("the held turn is sent once speaking ends", g4.sent == ["a"])

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
