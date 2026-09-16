"""Playback sync logic test — يحاكي VoiceAudioEngine (advance-on-completion + .dataPlayedBack + drain + generation).
اختبارات منطقية على Linux (لا تثبت AVFoundation/بناء iOS/الجهاز).
يميّز: اكتمال الرندر (schedule) vs اكتمال التشغيل (dataPlayedBack)."""
MAX_AHEAD = 3

class PlaybackSync:
    def __init__(self):
        self.pending = []          # (bytes, level)
        self.scheduled = 0
        self.scheduled_levels = [] # levels للمقاطع المجدولة (باستثناء الأول)
        self.gen = 0
        self.published = []        # levels المنشورة بالترتيب
        self.has_drained = False
        self.is_speaking = False

    def begin_speaking(self):
        self.gen += 1
        self.scheduled_levels = []
        self.has_drained = False
        self.is_speaking = True

    def enqueue(self, nbytes, level):
        self.pending.append((nbytes, level))

    def schedule_next(self):       # جدولة مقطع واحد (نهاية الرندر، وليس التشغيل)
        if not self.pending:
            return None
        chunk = self.pending.pop(0)
        self.scheduled += 1
        if self.scheduled == 1:
            self.published.append(chunk[1])   # أول مقطع يبدأ التشغيل الآن
        else:
            self.scheduled_levels.append(chunk[1])
        return chunk

    def complete_playback(self, gen):   # اكتمال التشغيل (dataPlayedBack)
        if gen != self.gen:
            return  # stale callback من دورة قديمة
        self.scheduled -= 1
        if self.scheduled_levels:
            self.published.append(self.scheduled_levels.pop(0))  # advance للـ التالي
        self.check_drain()

    def check_drain(self):
        if (not self.has_drained and not self.is_speaking
                and not self.pending and self.scheduled == 0):
            self.has_drained = True
            self.published.append(0.0)

    def flush_tail(self):          # response.done
        self.is_speaking = False
        self.check_drain()

    def flush(self):               # barge-in
        self.gen += 1
        self.pending = []
        self.scheduled = 0
        self.scheduled_levels = []
        self.is_speaking = False
        self.has_drained = False
        self.published.append(0.0)

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# 1. مستوى المقطع الجاري أثناء مقاطع مجدولة لاحقاً (advance-on-completion)
p = PlaybackSync()
p.begin_speaking()
for lv in [0.1, 0.2, 0.3]:
    p.enqueue(4800, lv)
c0 = p.schedule_next()   # 0.1 ينشر
c1 = p.schedule_next()   # 0.2 في scheduled_levels
c2 = p.schedule_next()   # 0.3 في scheduled_levels
check("المقطع الجاري (الأول) يُنشر فوراً، اللاحق مؤجل", p.published == [0.1])
p.complete_playback(p.gen)  # نهاية 0.1 → انشر 0.2
check("بعد اكتمال تشغيل الأول → يُنشر مستوى الثاني", p.published == [0.1, 0.2])
p.complete_playback(p.gen)  # نهاية 0.2 → انشر 0.3
check("بعد اكتمال الثاني → يُنشر الثالث", p.published == [0.1, 0.2, 0.3])
p.complete_playback(p.gen)  # نهاية 0.3 → لا advance (فارغ)
check("لا level إضافي بعد آخر مقطع (بدون drain بعد)", p.published == [0.1, 0.2, 0.3])

# 2. انتهاء الصوت قبل response.done → drain عند response.done
p = PlaybackSync()
p.begin_speaking()
p.enqueue(4800, 0.5)
p.schedule_next()
p.complete_playback(p.gen)   # انتهى الصوت، لكن is_speaking=True → لا drain
check("لا drain قبل response.done (التوليد ما زال نشط)", not p.has_drained)
p.flush_tail()               # response.done → drain
check("drain عند response.done (مرة واحدة) + reset 0", p.has_drained and p.published[-1] == 0.0)

# 3. response.done قبل انتهاء الصوت → drain عند اكتمال آخر مقطع
p = PlaybackSync()
p.begin_speaking()
p.enqueue(4800, 0.3)
p.enqueue(4800, 0.4)
p.schedule_next()
p.schedule_next()
p.flush_tail()               # response.done، لكن scheduled=2 → لا drain
check("response.done مع صوت متبقٍ لا ينهي فوراً", not p.has_drained)
p.complete_playback(p.gen)   # نهاية الأول → انشر 0.4
p.complete_playback(p.gen)   # نهاية الثاني → drain
check("drain عند اكتمال آخر مقطع (وليس عند response.done)", p.has_drained and p.published[-1] == 0.0)

# 4. المقاطعة أثناء الذيل (صوت متبقٍ بعد response.done)
p = PlaybackSync()
p.begin_speaking()
p.enqueue(4800, 0.2)
p.enqueue(4800, 0.3)
p.schedule_next()
p.schedule_next()
p.flush_tail()               # response.done (scheduled=2)
old_gen = p.gen
p.flush()                    # barge-in: gen++ + reset + level 0
check("المقاطعة أثناء الذيل تمسح pending + scheduled", len(p.pending) == 0 and p.scheduled == 0)
check("المقاطعة تصفّر المستوى فوراً", p.published[-1] == 0.0)
# stale completions من الدورة القديمة لا تنشر
p.complete_playback(old_gen)
p.complete_playback(old_gen)
check("stale completion (gen قديم) لا ينشر level بعد المقاطعة", p.published[-1] == 0.0)

# 5. رد جديد بعد الإلغاء: begin_speaking يبطل الدورة القديمة
p.begin_speaking()           # رد جديد (gen++)
p.enqueue(4800, 0.9)
p.schedule_next()
check("الرد الجديد ينشر level نظيفاً (0.9)", 0.9 in p.published)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
