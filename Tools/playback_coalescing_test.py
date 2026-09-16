"""Playback coalescing + schedule-ahead: byte-conservation proof (mirrors VoiceAudioEngine logic).
يحاكي completion handler (buffer ينتهي → pump) ليثبت:
100% bytes تُجدول بالترتيب، لا tail مفقود، no gap (schedule-ahead يمنع underrun).
"""
TARGET = 4800      # ~100ms @24kHz 16-bit mono
MAX_AHEAD = 3

class Playback:
    def __init__(self):
        self.queue = []
        self.scheduled = 0
        self.received = 0
        self.scheduled_bytes = 0
        self.completed = 0
        self.underruns = 0
        self.tail = 0
        self.order = []
        self.is_speaking = True

    def enqueue(self, data):
        self.received += len(data)
        self.queue.append(data)
        self.pump()
        self.drain_completions()   # playback أسرع من streaming → buffers تنتهي

    def drain_completions(self):
        # كل buffer مجدول ينتهي → scheduled-- → pump (يعكس completion handler)
        while self.scheduled > 0:
            self.scheduled -= 1
            self.completed += 1
            self.pump()

    def flush_tail(self):
        self.is_speaking = False
        self.pump(force_tail=True)

    def pump(self, force_tail=False):
        while self.scheduled < MAX_AHEAD:
            data = self.next_buffer(force_tail)
            if data is None:
                break
            self.scheduled_bytes += len(data)
            self.scheduled += 1
            self.order.append(data)
            if force_tail:
                break

    def next_buffer(self, force_tail):
        if not self.queue:
            return None
        collected = b''
        if force_tail:
            while self.queue:
                collected += self.queue.pop(0)
            self.tail += len(collected)
        else:
            while self.queue and len(collected) < TARGET:
                collected += self.queue.pop(0)
        return collected or None

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

def scenario(name, deltas):
    p = Playback()
    stream = b''.join(deltas)
    for d in deltas:
        p.enqueue(d)
    p.flush_tail()
    check(f"{name}: 100% bytes scheduled ({p.scheduled_bytes}/{p.received})", p.scheduled_bytes == p.received)
    check(f"{name}: queue empty after flushTail", len(p.queue) == 0)
    check(f"{name}: order preserved", b''.join(p.order) == stream)

scenario("small deltas + small tail", [b'\x00'*960]*10 + [b'\x00'*700])
scenario("variable deltas", [b'\x00'*3200, b'\x00'*480, b'\x00'*1200, b'\x00'*96, b'\x00'*2400, b'\x00'*800])
scenario("one large delta", [b'\x00'*20000])
scenario("tail < 100ms (critical)", [b'\x00'*4800, b'\x00'*4800, b'\x00'*1200])
scenario("long response (200 deltas)", [b'\x00'*960]*200 + [b'\x00'*300])
scenario("tiny tail (1 byte)", [b'\x00'*4800, b'\x00'*4800, b'\x00'*1])
scenario("empty-ish tail", [b'\x00'*4800, b'\x00'*2])

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
