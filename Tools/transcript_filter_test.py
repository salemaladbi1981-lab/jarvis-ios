"""Transcript admission regression.
Device evidence (sessions 8/10/12/15/16): whisper fills silence with stock phrases
("شكرا", "شكرا على المشاهدة", "اشتركوا في القناة", "Transcribed by https://otter.ai")
and a TV in the room produced courtesy fragments. Every transcript reached the backend
and asked for an answer, so JARVIS答 talked to the room. Filler is now dropped, an
identical utterance inside 10s is dropped, and "الكالندر" reaches the calendar tool —
in session 4 "وش عندي في الكالندر" fell through to the backend because the marker list
only had "كلندر"."""
import os, re, sys, unicodedata
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

vm = open(os.path.join(ROOT, 'Home/HomeViewModel.swift'), encoding='utf-8').read()

def body(name):
    m = re.search(r'^    (?:private |static |)+func ' + name + r'\b.*$', vm, re.M)
    if not m: return ''
    rest = vm[m.end():]
    nxt = re.search(r'\n    (?:private |static |@|/// )', rest)
    return rest[:nxt.start()] if nxt else rest

router = body('routeVoiceTranscript')

# --- the guard exists and runs before anything asks for an answer ---
check("router drops filler before routing",
      'if Self.isFillerTranscript(text) {' in router and 'ignored-filler' in router)
check("router drops a repeat inside the window",
      'Self.repeatWindow' in router and 'ignored-repeat' in router)
check("filler/repeat return without requesting a response",
      router.index('ignored-filler') < router.index('requestResponse()'))
check("the window is 10 seconds", 'repeatWindow: TimeInterval = 10' in vm)
check("device tools stay reachable on a repeat",
      '!Self.isDeviceToolRequest(t)' in router)

# --- the filler list covers what the device actually produced ---
for phrase in ["شكرا", "شكرا على المشاهدة", "شكرا لكم", "اشتركوا في القناة", "ترجمة",
               "thank you", "bye"]:
    check(f"filler list covers {phrase}", f'"{phrase}"' in vm)
check("transcription artefacts are covered by prefix",
      '"transcribed by"' in vm and 'fillerPrefixes' in vm)
check("empty and letterless transcripts are dropped",
      'n.isEmpty { return true }' in vm and 'contains(where: { $0.isLetter })' in vm)

# --- calendar trigger ---
cal = body('isCalendarQuestion')
for marker in ["كالندر", "كلندر", "تقويم", "calendar", "بكرة", "مواعيد"]:
    check(f"calendar marker {marker}", f'"{marker}"' in cal)
check("the router uses the shared calendar predicate", 'if Self.isCalendarQuestion(t) {' in router)
check("no inline calendar marker list is left behind",
      't.contains("كلندر") || t.contains("calendar")' not in vm)


# --- the admission contract, mirrored so the wording cannot drift ---
FILLERS = {"شكرا", "شكرا لكم", "شكرا جزيلا", "شكرا على المشاهدة", "شكرا للمشاهدة",
           "اشتركوا في القناة", "اشترك في القناة", "لا تنسى الاشتراك", "اشتركوا بالقناة",
           "ترجمة", "ترجمه", "الترجمة", "اراكم على خير", "الى اللقاء", "مع السلامة",
           "thank you", "thanks", "thank you for watching", "bye", "bye bye",
           "subscribe", "please subscribe", "you", "okay", "ok"}
PREFIXES = ("transcribed by", "ترجمة نانسي", "ترجمه نانسي", "subtitles by", "amara.org")

def normalize(text):
    out = ''.join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    out = ''.join(' ' if unicodedata.category(c).startswith('P') or unicodedata.category(c).startswith('S') else c
                  for c in out)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي")):
        out = out.replace(a, b)
    return ' '.join(out.split()).lower()

FILLERS = {normalize(x) for x in FILLERS}
PREFIXES = tuple(normalize(x) for x in PREFIXES)

def is_filler(text):
    n = normalize(text)
    if not n: return True
    if not any(c.isalpha() for c in n): return True
    return n in FILLERS or n.startswith(PREFIXES)

for t in ["شكرا", "شكراً", "شكرا لكم", "شكراً على المشاهدة", "اشتركوا في القناة",
          "Thank you.", "Bye.", "Transcribed by https://otter.ai", "...", "   ", "!!"]:
    check(f"dropped: {t.strip()[:34] or '<blank>'}", is_filler(t))
for t in ["وش عندي اليوم؟", "اقرأ للكلندر اش عندي بكرة", "ذكرني بالاجتماع",
          "صحني الساعة سبعة", "من هو المدرب؟", "وش عندي في الكالندر"]:
    check(f"kept: {t}", not is_filler(t))

class Admission:
    """Repeat policy: same utterance inside 10s is one turn, device tools exempt."""
    def __init__(self):
        self.last = ""
        self.at = -999.0
        self.routed = []
    def offer(self, text, now, device_tool=False):
        if is_filler(text): return "ignored-filler"
        n = normalize(text)
        if n == self.last and now - self.at < 10 and not device_tool:
            return "ignored-repeat"
        self.last, self.at = n, now
        self.routed.append(text)
        return "routed"

a = Admission()
check("first utterance routes", a.offer("وش الجديد", 0) == "routed")
check("same utterance after 3s is dropped", a.offer("وش الجديد", 3) == "ignored-repeat")
check("same utterance after 11s routes again", a.offer("وش الجديد", 11.5) == "routed")
b = Admission()
b.offer("وش عندي اليوم", 0, device_tool=True)
check("a repeated device-tool request still routes",
      b.offer("وش عندي اليوم", 2, device_tool=True) == "routed")
c = Admission()
check("filler never routes", c.offer("شكرا", 0) == "ignored-filler" and c.routed == [])

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
