"""Session-level event guards (RealtimeVoiceSession) — response_id / currentResponseID / barge.
اختبارات منطقية على Linux."""
class SessionGuard:
    def __init__(self):
        self.currentResponseID = None
        self.isSpeaking = False
        self.accepted = []          # deltas المقبولة
        self.done_applied = 0       # done المطبقة (flushTail)
        self.state = "idle"

    def on_response_created(self, rid):
        self.currentResponseID = rid

    def on_delta(self, rid):
        # حراسة: لا رد نشط → مرفوض
        if self.currentResponseID is None:
            return
        if rid != self.currentResponseID:
            return   # stale
        self.isSpeaking = True
        self.accepted.append(rid)

    def on_done(self, rid):
        # حراسة: done لرد قديم لا يُطبق
        if self.currentResponseID is not None and rid != self.currentResponseID:
            return
        self.isSpeaking = False
        self.currentResponseID = None
        self.done_applied += 1

    def on_barge(self):
        self.currentResponseID = None
        self.isSpeaking = False
        self.state = "listening"

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# 1. إلغاء R1 ثم delta منه قبل إنشاء R2 → مرفوض (لا رد نشط)
g = SessionGuard()
g.on_response_created("R1")
g.on_barge()               # currentResponseID = None
g.on_delta("R1")           # لا رد نشط → مرفوض
check("delta من R1 بعد الإلغاء (قبل R2) مرفوض", g.accepted == [] and not g.isSpeaking)

# 2. delta من R1 بعد إنشاء R2 → مرفوض (stale)
g = SessionGuard()
g.on_response_created("R1")
g.on_barge()
g.on_response_created("R2")
g.on_delta("R1")           # rid R1 != current R2 → مرفوض
g.on_delta("R2")           # صحيح → مقبول
check("delta من R1 بعد R2 مرفوض، delta R2 مقبول", g.accepted == ["R2"])

# 3. done من R1 بعد R2 → لا يُطبق
g = SessionGuard()
g.on_response_created("R1")
g.on_barge()
g.on_response_created("R2")
g.on_delta("R2")
g.on_done("R1")            # stale done → لا يُطبق
check("done من R1 بعد R2 لا يُطبق (لا flushTail)", g.done_applied == 0 and g.isSpeaking)

# 4. مقاطعة الذيل → Listening
g = SessionGuard()
g.on_response_created("R1")
g.on_delta("R1")
g.on_done("R1")            # done → currentResponseID = nil، isSpeaking=False
g.on_barge()               # مقاطعة tail → listening
check("مقاطعة الذيل تنقل إلى Listening", g.state == "listening" and g.currentResponseID is None)

# 5. delta قبل أي response.created → مرفوض
g = SessionGuard()
g.on_delta("RX")           # لا رد نشط
check("delta قبل response.created مرفوض", g.accepted == [] and not g.isSpeaking)

# 6. done صحيح → يُطبق مرة واحدة
g = SessionGuard()
g.on_response_created("R1")
g.on_delta("R1")
g.on_done("R1")
check("done صحيح يُطبق (flushTail + currentResponseID nil)", g.done_applied == 1 and g.currentResponseID is None)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
