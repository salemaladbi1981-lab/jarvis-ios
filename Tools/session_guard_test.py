"""Session-level event guards (RealtimeVoiceSession) — مرآة للمنطق الفعلي في Swift.
يحاكي: جيل الاتصال + هوية الرد + جاهزية الجلسة + completion token بهوية دورة التشغيل.
اختبارات منطقية على Linux."""
class SessionGuard:
    def __init__(self):
        self.currentResponseID = None
        self.isSessionReady = False
        self.pendingCompletion = None   # None | "success" | "failed"
        self.pendingCompletionCycle = 0
        self.connectionGeneration = 0
        self.done_applied = 0
        self.accepted_deltas = []
        self.connected = 0
        self.listening = 0

    # دورة الاتصال
    def begin_connection(self):
        self.connectionGeneration += 1
        return self.connectionGeneration

    def is_valid_connection(self, gen):
        return gen == self.connectionGeneration

    # دورة الجلسة/الرد
    def session_created(self):
        self.isSessionReady = True

    def on_response_created(self, rid):
        if not self.isSessionReady:
            return False
        self.currentResponseID = rid
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        return True

    def on_delta(self, rid):
        if not self.isSessionReady or self.currentResponseID is None:
            return False
        if rid != self.currentResponseID:
            return False
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        self.accepted_deltas.append(rid)
        return True

    def on_done(self, rid, cycle, status="completed"):
        if self.currentResponseID is None or rid != self.currentResponseID:
            return False
        self.pendingCompletion = "failed" if status == "failed" else "success"
        self.pendingCompletionCycle = cycle
        self.currentResponseID = None
        self.done_applied += 1
        return True

    def on_speech_started(self):
        if not self.isSessionReady:
            return False
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        self.currentResponseID = None
        return True

    def consume_completion(self, cycle):
        if cycle != self.pendingCompletionCycle:
            return None
        c = self.pendingCompletion
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        return c

    def on_stop(self):
        self.currentResponseID = None
        self.isSessionReady = False
        self.pendingCompletion = None; self.pendingCompletionCycle = 0
        self.connectionGeneration += 1   # إبطال دورة الاتصال

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# 1. done R1 بعد الإيقاف → مرفوض
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_stop()
check("done R1 بعد الإيقاف مرفوض", g.on_done("R1", 1) == False)

# 2. done R1 أثناء R2 → لا يؤثر
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_stop()
g.session_created(); g.on_response_created("R2"); g.on_delta("R2")
check("done R1 أثناء R2 لا يُطبق", g.on_done("R1", 1) == False and g.done_applied == 0)

# 3. تكرار done الصحيح → مرة واحدة
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_delta("R1")
g.on_done("R1", 1); g.on_done("R1", 1)
check("done الصحيح يطبّق مرة واحدة", g.done_applied == 1)

# 4. إيقاف أثناء الرد → أحداثه مرفوضة
g = SessionGuard(); g.session_created(); g.on_response_created("R1"); g.on_delta("R1")
g.on_stop()
check("أحداث الدورة الموقوفة لا تُطبّق", g.on_delta("R1") == False and g.on_done("R1", 1) == False)

# 5. إعادة بدء رد جديد
g = SessionGuard(); g.session_created(); g.on_response_created("R2"); g.on_delta("R2")
g.on_done("R2", 2)
check("رد جديد + اكتمال طبيعي", g.done_applied == 1 and g.pendingCompletion == "success")

# 6. stopListening يبطل دورة الاتصال → session.created متأخر مرفوض
g = SessionGuard()
genA = g.begin_connection()
g.session_created()
g.on_stop()
late_ready = g.is_valid_connection(genA)
check("stop يبطل جيل الاتصال (session.created المتأخر لا يُعالج)", late_ready == False)

# 7. بدء جلسة جديدة بعد الإيقاف بصورة صحيحة
g = SessionGuard(); g.begin_connection(); g.session_created(); g.on_stop()
genB = g.begin_connection()
check("بدء جلسة جديدة بعد الإيقاف صحيح", g.is_valid_connection(genB))

# 8. هوية دورة الـ drain (success) — drain قديم لا يمس الجديد
g = SessionGuard(); g.session_created()
g.on_response_created("R1"); g.on_delta("R1"); g.on_done("R1", 1, "completed")
g.on_response_created("R2"); g.on_delta("R2"); g.on_done("R2", 2, "completed")
check("drain(R1) لا ينشر ولا يمس R2 (success)", g.consume_completion(1) is None and g.pendingCompletion == "success")
check("drain(R2) يستهلك نتيجته مرة واحدة (success)", g.consume_completion(2) == "success" and g.consume_completion(2) is None)

# 9. هوية دورة الـ drain (failed)
g = SessionGuard(); g.session_created()
g.on_response_created("R1"); g.on_delta("R1"); g.on_done("R1", 1, "failed")
g.on_response_created("R2"); g.on_delta("R2"); g.on_done("R2", 2, "failed")
check("drain(R1) لا يمس R2 (failed)", g.consume_completion(1) is None and g.pendingCompletion == "failed")
check("drain(R2) يستهلك failed", g.consume_completion(2) == "failed")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
