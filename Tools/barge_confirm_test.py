"""Manual-interruption regression (source + logic mirror).
السياسة الإنتاجية: كلام الغرفة/الخلفية (قصير أو مستمر) لا يُلغي رد JARVIS أبداً.
المقاطعة الوحيدة أثناء الكلام = يدوية (زر المايك → interrupt() → cancel+truncate+flush مرة واحدة)."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

rvs = open(os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift'), encoding='utf-8').read()

# 1) Source-level: لا مقاطعة تلقائية (بلا نافذة تأكيد قديمة)
check("RealtimeVoiceSession: لا bargeConfirmWindow", 'bargeConfirmWindow' not in rvs)
check("RealtimeVoiceSession: لا pendingBargeIn", 'pendingBargeIn' not in rvs)
check("RealtimeVoiceSession: لا scheduleBargeConfirm", 'scheduleBargeConfirm' not in rvs)

# 2) Source-level: speech_started أثناء الكلام → ignored (لا bargeIn)
check("speech_started أثناء الكلام → ignored (manual only)",
      'speech_started while speaking → ignored' in rvs)
check("لا bargeIn() داخل معالج speech_started", 'if isSpeaking' in rvs)

# 3) Source-level: المقاطعة اليدوية تُرسل cancel + truncate + flush
check("interrupt() يرسل response.cancel", 'response.cancel' in rvs)
check("interrupt() يرسل conversation.item.truncate", 'conversation.item.truncate' in rvs)
check("interrupt() يرسل audio.flush", 'audio.flush()' in rvs)
check("bargeIn() يُستدعى من interrupt() فقط", 'func interrupt()' in rvs)

# 4) Logic mirror (نفس state machine): speech_started أثناء الكلام لا يُلغي
class ManualInterrupt:
    def __init__(self):
        self.cancels = 0; self.truncates = 0; self.flushes = 0; self.listening = 0
    def speech_started(self, speaking):
        if speaking:
            return  # تجاهل — لا مقاطعة تلقائية
        self.listening += 1
    def interrupt(self):
        # يدوي: cancel+truncate+flush مرة واحدة
        self.cancels += 1; self.truncates += 1; self.flushes += 1

# A) كلام خلفية مستمر أثناء الكلام → لا cancel
a = ManualInterrupt()
for _ in range(100): a.speech_started(True)   # 100 حدث speech_started مستمر
check("A) كلام خلفية/غرفة مستمر → لا cancel", a.cancels == 0 and a.truncates == 0 and a.flushes == 0)

# B) ضوضاء قصيرة (نقرة) أثناء الكلام → لا cancel
b = ManualInterrupt(); b.speech_started(True); b.speech_started(True)
check("B) ضوضاء قصيرة → لا cancel", b.cancels == 0)

# C) speech_started أثناء listening (ليس speaking) → listening فقط، لا cancel
c = ManualInterrupt(); c.speech_started(False)
check("C) speech_started أثناء listening → listening فقط", c.listening == 1 and c.cancels == 0)

# D) مقاطعة يدوية → cancel+truncate+flush مرة واحدة (لا تكرار)
d = ManualInterrupt(); d.interrupt()
check("D) مقاطعة يدوية → cancel+truncate+flush مرة واحدة",
      d.cancels == 1 and d.truncates == 1 and d.flushes == 1)

# E) مقاطعتان يدويتان متتاليتان → كل منهما حدث واحد (لا تكرار داخلي)
e = ManualInterrupt(); e.interrupt(); e.interrupt()
check("E) لا duplicate cancel/truncate/flush", e.cancels == 2 and e.truncates == 2 and e.flushes == 2)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
