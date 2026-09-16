"""Session-level event guards (RealtimeVoiceSession) — مرآة للمنطق الفعلي في Swift.
يحاكي: جيل الاتصال + هوية الرد + جاهزية الجلسة + completion token بهوية دورة التشغيل
+ مسار إنهاء الرد بلا صوت (resolveDone → publishImmediately)."""
class SessionGuard:
    def __init__(self):
        self.currentResponseID = None
        self.isSessionReady = False
        self.pendingCompletion = None   # None | "success" | "failed"
        self.pendingCompletionCycle = 0
        self.currentResponseHasAudio = False
        self.connectionGeneration = 0
        self.done_applied = 0
        self.accepted_deltas = []
        self.immediate_published = []   # نتائج النشر الفوري (بلا صوت)

    def begin_connection(self):
        self.connectionGeneration += 1
        return self.connectionGeneration

    def is_valid_connection(self, gen):
        return gen == self.connectionGeneration

    def session_created(self):
        self.isSessionReady = True

    def on_response_created(self, rid):
        if not self.isSessionReady:
            return False
        self.currentResponseID = rid
        self.currentResponseHasAudio = False
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        return True

    def on_delta(self, rid):
        if not self.isSessionReady or self.currentResponseID is None:
            return False
        if rid != self.currentResponseID:
            return False
        self.currentResponseHasAudio = True
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        self.accepted_deltas.append(rid)
        return True

    def resolve_done(self, rid, cycle, status="completed"):
        # يعيد: "ignore" | "waitForDrain" | ("publishImmediately", result)
        if self.currentResponseID is None or rid != self.currentResponseID:
            return "ignore"
        result = "failed" if status == "failed" else "success"
        self.currentResponseID = None
        if self.currentResponseHasAudio:
            self.pendingCompletion = result
            self.pendingCompletionCycle = cycle
            self.done_applied += 1
            return "waitForDrain"
        else:
            self.pendingCompletion = None; self.pendingCompletionCycle = 0
            self.immediate_published.append(result)
            return ("publishImmediately", result)

    def on_speech_started(self):
        if not self.isSessionReady:
            return False
        # لا يُبطل الرد هنا — التأكيد يؤجل الإبطال (منع micro-cut)
        return True

    def on_barge(self):
        self.currentResponseID = None
        self.currentResponseHasAudio = False
        self.pendingCompletion = None; self.pendingCompletionCycle = 0

    def consume_completion(self, cycle):
        if cycle != self.pendingCompletionCycle:
            return None
        c = self.pendingCompletion
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        return c

    def on_stop(self):
        self.currentResponseID = None
        self.isSessionReady = False
        self.currentResponseHasAudio = False
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        self.connectionGeneration += 1

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# 1. done R1 بعد الإيقاف مرفوض
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_stop()
check("done R1 بعد الإيقاف مرفوض", g.resolve_done("R1", 1) == "ignore")

# 2. done R1 أثناء R2 لا يُطبق
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_stop()
g.session_created(); g.on_response_created("R2"); g.on_delta("R2")
check("done R1 أثناء R2 لا يُطبق", g.resolve_done("R1", 1) == "ignore")

# 3. تكرار done الصحيح مرة واحدة
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_delta("R1")
g.resolve_done("R1", 1); g.resolve_done("R1", 1)
check("done الصحيح (بصوت) يطبّق مرة واحدة", g.done_applied == 1)

# 4. إيقاف أثناء الرد → أحداثه مرفوضة
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_delta("R1"); g.on_stop()
check("أحداث الدورة الموقوفة لا تُطبّق", g.on_delta("R1") == False and g.resolve_done("R1", 1) == "ignore")

# 5. رد جديد بصوت + اكتمال طبيعي
g = SessionGuard(); g.session_created(); g.on_response_created("R2"); g.on_delta("R2")
g.resolve_done("R2", 2)
check("رد جديد بصوت + اكتمال طبيعي", g.done_applied == 1 and g.pendingCompletion == "success")

# 6. stop يبطل جيل الاتصال
g = SessionGuard(); genA = g.begin_connection(); g.session_created(); g.on_stop()
check("stop يبطل جيل الاتصال", g.is_valid_connection(genA) == False)

# 7. بدء جلسة جديدة بعد الإيقاف
g = SessionGuard(); g.begin_connection(); g.session_created(); g.on_stop()
genB = g.begin_connection()
check("بدء جلسة جديدة بعد الإيقاف", g.is_valid_connection(genB))

# 8. هوية دورة الـ drain (success)
g = SessionGuard(); g.session_created()
g.on_response_created("R1"); g.on_delta("R1"); g.resolve_done("R1", 1, "completed")
g.on_response_created("R2"); g.on_delta("R2"); g.resolve_done("R2", 2, "completed")
check("drain(R1) لا يمس R2 (success)", g.consume_completion(1) is None and g.pendingCompletion == "success")
check("drain(R2) يستهلك مرة واحدة (success)", g.consume_completion(2) == "success" and g.consume_completion(2) is None)

# 9. هوية دورة الـ drain (failed)
g = SessionGuard(); g.session_created()
g.on_response_created("R1"); g.on_delta("R1"); g.resolve_done("R1", 1, "failed")
g.on_response_created("R2"); g.on_delta("R2"); g.resolve_done("R2", 2, "failed")
check("drain(R1) لا يمس R2 (failed)", g.consume_completion(1) is None and g.pendingCompletion == "failed")

# 10. رد بلا صوت بعد R1 مكتمل → نشر فوري مرة واحدة + لا نتيجة معلقة
g = SessionGuard(); g.session_created()
g.on_response_created("R1"); g.on_delta("R1"); g.resolve_done("R1", 1, "completed")
g.consume_completion(1)   # R1 drain استهلك
g.on_response_created("R2")   # بلا delta
r = g.resolve_done("R2", 1, "failed")
check("رد بلا صوت ينشر فوراً (failed)", r == ("publishImmediately", "failed"))
check("لا نتيجة معلقة بعد النشر الفوري", g.pendingCompletion is None and g.pendingCompletionCycle == 0)
check("تكرار done بلا صوت مرفوض", g.resolve_done("R2", 1, "failed") == "ignore")

# 11. speech_started لا يُبطل الرد (delta يبقى مقبولاً — منع micro-cut)
g = SessionGuard(); g.session_created(); g.on_response_created("R1")
check("speech_started لا يُبطل الرد (delta مقبول)", g.on_speech_started() and g.on_delta("R1") == True)

# 12. on_barge (بعد التأكيد) يبطل الرد
g = SessionGuard(); g.session_created(); g.on_response_created("R1")
g.on_speech_started(); g.on_barge()
check("on_barge يبطل الرد", g.on_delta("R1") == False and g.resolve_done("R1", 1) == "ignore")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
