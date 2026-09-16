"""Playback sync logic test — يحاكي VoiceAudioEngine (generation + level-at-render).
اختبارات منطقية على Linux (لا تثبت AVFoundation/بناء iOS/الجهاز)."""
TARGET = 4800
MAX_AHEAD = 3

class PlaybackSync:
    def __init__(self):
        self.pending = []          # (bytes, level)
        self.scheduled = 0
        self.gen = 0
        self.published = []        # levels المنشورة بالترتيب
        self.drained = False
        self.is_speaking = False

    def begin_speaking(self):
        self.gen += 1
        self.is_speaking = True
        self.drained = False

    def enqueue(self, nbytes, level):
        self.pending.append((nbytes, level))
        self.pump()

    def pump(self):
        while self.scheduled < MAX_AHEAD and self.pending:
            chunk = self.pending.pop(0)
            self.scheduled += 1
            g = self.gen
            self._complete(chunk, g)   # completion عند بداية render

    def _complete(self, chunk, g):
        if g != self.gen:
            return  # stale callback
        self.published.append(chunk[1])
        self.scheduled -= 1
        self.pump()
        if not self.pending and self.scheduled == 0 and not self.is_speaking:
            self.published.append(0.0)   # reset عند drain
            self.drained = True

    def flush_tail(self):
        self.is_speaking = False
        self.pump()
        if not self.pending and self.scheduled == 0 and not self.drained:
            self.published.append(0.0)
            self.drained = True

    @staticmethod
    def _stale_completion_sim(p, level, old_gen):
        # يحاكي completion handler مع gen guard: إذا old_gen != current gen → لا ينشر
        if old_gen != p.gen:
            return None
        p.published.append(level)
        return level

    def flush(self):
        self.gen += 1
        self.pending = []
        self.scheduled = 0
        self.is_speaking = False
        self.published.append(0.0)   # reset فوري

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# 1. جدولة عدة buffers + level بالترتيب + reset عند drain
p = PlaybackSync()
p.begin_speaking()
for lv in [0.1, 0.2, 0.3, 0.4, 0.5]:
    p.enqueue(TARGET, lv)
p.flush_tail()
check("levels تُنشر بالترتيب (كل chunk عند بداية render)", p.published[:5] == [0.1, 0.2, 0.3, 0.4, 0.5])
check("reset إلى 0 عند اكتمال التشغيل", p.published[-1] == 0.0)
check("drained بعد آخر chunk", p.drained)

# 2. response.done قبل انتهاء الصوت المحلي: flush_tail مع scheduled>0 لا يصفّر فوراً
# (ينتظر completion الـ آخر chunk)؛ مع scheduled==0 يصفّر فوراً
p = PlaybackSync()
p.begin_speaking()
# حالة A: صوت ما زال قيد التشغيل عند response.done (scheduled>0)
p.enqueue(TARGET, 0.3)
p.scheduled = 1           # نحاكي أن buffer ما زال قيد التشغيل
p.is_speaking = False     # response.done (generation done)
p.flush_tail()            # يجب ألا يصفّر لأن scheduled>0 (ينتظر الـ completion)
check("flush_tail مع scheduled>0 لا يصفّر فوراً (ينتظر آخر chunk)", p.published[-1] == 0.3)
# حالة B: صوت انتهى قبل response.done (scheduled==0)
p.scheduled = 0
p.flush_tail()            # يصفّر فوراً
check("flush_tail مع scheduled==0 يصفّر فوراً (drain)", p.drained and p.published[-1] == 0.0)

# 3. barge-in: gen++ + مسح pending + level reset فوري
p = PlaybackSync()
p.begin_speaking()
p.enqueue(TARGET, 0.2)
p.enqueue(TARGET, 0.3)
p.flush()
check("barge-in يصفّر المستوى فوراً", p.published[-1] == 0.0)
check("barge-in يمسح pending + scheduled", len(p.pending) == 0 and p.scheduled == 0)

# 4. stale completion من دورة قديمة لا ينشر level (gen guard)
p = PlaybackSync()
p.begin_speaking()          # gen=1
p.enqueue(TARGET, 0.9)      # يُنشر 0.9 (gen=1 صالح)
p.flush()                   # gen=2 + reset
p.begin_speaking()          # gen=3 (رد جديد)
# محاكاة: completion قديم من gen=1 يحاول النشر — الـ gen guard يمنعه
stale = PlaybackSync._stale_completion_sim(p, 0.9, 1)
check("stale callback (gen قديم) لا ينشر level", stale is None)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
