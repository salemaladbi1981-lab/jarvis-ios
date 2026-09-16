"""Session-level event guards (RealtimeVoiceSession) — response.id (nested) + currentResponseID + stop.
يحاكي الـ parsing الفعلي (jsonNestedString لـ response.id) والحراسة المستخدمة في Swift.
اختبارات منطقية على Linux."""
class SessionGuard:
    def __init__(self):
        self.currentResponseID = None
        self.isSpeaking = False
        self.done_applied = 0
        self.accepted_deltas = []
        self.state = "idle"   # idle/listening/speaking

    def on_response_created(self, rid):
        self.currentResponseID = rid

    def on_delta(self, rid):   # rid من response_id (top-level)
        if self.currentResponseID is None:
            return
        if rid != self.currentResponseID:
            return
        self.isSpeaking = True
        self.accepted_deltas.append(rid)

    def on_done(self, rid):    # rid من response.id (nested)
        # guard إلزامي قبل أي تغيير حالة/flushTail
        if self.currentResponseID is None:
            return
        if rid != self.currentResponseID:
            return
        self.isSpeaking = False
        self.currentResponseID = None
        self.done_applied += 1
        self.state = "idle"

    def on_stop(self):         # stopListening/interrupt/disconnect
        self.currentResponseID = None
        self.isSpeaking = False
        self.state = "idle"

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# 1. إلغاء R1 (stop) ثم done R1 قبل R2 → مرفوض (لا رد نشط)
g = SessionGuard()
g.on_response_created("R1")
g.on_stop()
g.on_done("R1")
check("done R1 بعد الإيقاف (قبل R2) مرفوض", g.done_applied == 0)

# 2. done R1 أثناء R2 → لا يؤثر
g = SessionGuard()
g.on_response_created("R1")
g.on_stop()
g.on_response_created("R2")
g.on_delta("R2")
g.on_done("R1")   # stale
check("done R1 أثناء R2 لا يُطبق ولا يغيّر R2", g.done_applied == 0 and g.isSpeaking)

# 3. تكرار done الصحيح → يطبّق مرة واحدة
g = SessionGuard()
g.on_response_created("R1")
g.on_delta("R1")
g.on_done("R1")
g.on_done("R1")   # تكرار (currentResponseID None)
check("done الصحيح يطبّق مرة واحدة (التكرار مرفوض)", g.done_applied == 1)

# 4. ضغط زر الإيقاف أثناء الرد ثم أحداثه → تبقى متوقفة + مستوى صفر
g = SessionGuard()
g.on_response_created("R1")
g.on_delta("R1")
g.on_stop()               # stopListening
g.on_delta("R1")          # stale delta → مرفوض
g.on_done("R1")           # stale done → مرفوض
check("أحداث الدورة الموقوفة لا تُطبّق (يبقى متوقفاً)", g.done_applied == 0 and not g.isSpeaking and g.currentResponseID is None)

# 5. إعادة البدء: رد جديد يعمل + اكتمال طبيعي ينهي Speaking
g = SessionGuard()
g.on_response_created("R2")
g.on_delta("R2")
check("الرد الجديد يعمل (delta مقبول)", g.accepted_deltas == ["R2"] and g.isSpeaking)
g.on_done("R2")
check("اكتمال طبيعي ينهي Speaking (done R2)", g.done_applied == 1 and not g.isSpeaking)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
