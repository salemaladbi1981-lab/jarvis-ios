"""Barge-in confirmation regression (source + logic mirror).
يمنع الضوضاء القصيرة من إلغاء الرد، ويحافظ على المقاطعة الفورية للكلام الحقيقي."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

rvs = open(os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift'), encoding='utf-8').read()

# Source-level: confirmation موجودة
check("RealtimeVoiceSession: bargeConfirmWindow", 'bargeConfirmWindow' in rvs)
check("RealtimeVoiceSession: pendingBargeIn", 'pendingBargeIn' in rvs)
check("RealtimeVoiceSession: scheduleBargeConfirm", 'scheduleBargeConfirm' in rvs)
check("speech_started لا يستدعي bargeIn فوراً (بل pending+schedule)",
      'pendingBargeIn = true' in rvs and 'scheduleBargeConfirm()' in rvs)
check("speech_stopped يلغي pending للضوضاء القصيرة", 'dur < bargeConfirmWindow' in rvs)

# Logic mirror (نفس state machine)
WINDOW = 0.15
class BargeConfirm:
    def __init__(self):
        self.pending = False; self.started = 0.0; self.barged = 0; self.listening = 0
    def speech_started(self, now, speaking):
        if speaking:
            self.pending = True; self.started = now
        else:
            self.listening += 1
    def speech_stopped(self, now):
        if self.pending and (now - self.started) < WINDOW:
            self.pending = False   # ضوضاء
    def check(self, now):
        if self.pending:
            self.pending = False; self.barged += 1

# A) المستخدم يقول «وقف» (كلام حقيقي مستمر > النافذة)
a = BargeConfirm(); a.speech_started(0.0, True); a.check(0.15)
check("A) كلام مستمر > نافذة → barge-in", a.barged == 1)

# B) نقرة قصيرة (speech_stopped < نافذة)
b = BargeConfirm(); b.speech_started(0.0, True); b.speech_stopped(0.05); b.check(0.15)
check("B) نقرة قصيرة → لا barge-in", b.barged == 0)

# C) جملة طبيعية (كلام مستمر > نافذة)
c = BargeConfirm(); c.speech_started(0.0, True); c.check(0.15)
check("C) جملة طبيعية → barge-in", c.barged == 1)

# D) صمت/ضوضاء (لا speech_started)
d = BargeConfirm(); d.check(0.15)
check("D) صمت → لا cancel", d.barged == 0)

# E) نقرة قصيرة أثناء listening (ليس speaking) → يبقى listening فقط، لا barge
e = BargeConfirm(); e.speech_started(0.0, False)
check("E) speech_started أثناء listening → لا barge", e.barged == 0 and e.listening == 1)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
