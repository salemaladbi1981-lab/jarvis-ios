"""Alarm time-parsing regression.
Device evidence (console-session17): "اضبطلي المنبه بعد دقيقتين شغل المنبه" and
"اضبط لي المنبه على ٤:٥٦ pm" both failed to parse, so the request fell through to the
model, which invented "ما عندي صلاحية لضبط المنبه" — the on-device alarm path never ran
(no route=alarm, no [JARVIS-DIAG][alarm] line, authorizationState never even read).
The parser must read the dual form, spelled numbers, fractions of an hour, Arabic-Indic
digits, HH:MM and the meridiem words; and an alarm request whose time is unreadable must
be answered from the device, never handed to the model."""
import os, re, sys
from datetime import datetime, timedelta
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

vm = open(os.path.join(ROOT, 'Home/HomeViewModel.swift'), encoding='utf-8').read()

# --- the Swift side carries the vocabulary and the fallback ---
check("parser is split into relative and clock readers",
      'private static func relativeOffset(in t: String)' in vm and 'private static func clockDate(in t: String' in vm)
check("dual forms are handled", '"دقيقتين"' in vm and '"ساعتين"' in vm)
check("fractions of an hour are handled",
      'return 900' in vm and 'return 1800' in vm and 'return 5400' in vm and 'return 1200' in vm)
check("spelled numbers table exists", 'spelledNumbers' in vm and '"خمس"' in vm and '"عشرين"' in vm)
check("Arabic-Indic digits are normalised", '"٤": "4"' in vm and 'normalizedDigits' in vm)
check("HH:MM is read", r'\\d{1,2}\\s*[:.]\\s*\\d{2}' in vm)
check("both الساعة and على introduce a clock time",
      'الساعة|الساعه|ساعة|ساعه|على|عند' in vm)
check("meridiem words are covered",
      all(w in vm for w in ['"مساء"', '"العصر"', '"الفجر"', '"pm"', '"am"']))
check("alarm intent without a time is answered on device",
      'diagRoute("alarm-time-unclear"' in vm and 'ما فهمت الوقت، قلّه مرة ثانية' in vm)

router = vm.split('func routeVoiceTranscript')[1].split('\n    }\n')[0]
arm = router[router.index('isAlarmRequest'):router.index('parseCreateReminder')]
check("the unclear-time branch never asks the model for an answer",
      'requestResponse()' not in arm and 'sendGroundedDeviceResult' in arm)
EASTERN = {ord(a): b for a, b in zip("٠١٢٣٤٥٦٧٨٩", "0123456789")}
SPELLED = [("خمسة عشر",15),("خمس عشرة",15),("عشرين",20),("عشرة",10),("عشر",10),
           ("تسعة",9),("تسع",9),("ثمانية",8),("ثماني",8),("ثمان",8),("سبعة",7),("سبع",7),
           ("ستة",6),("ست",6),("خمسة",5),("خمس",5),("أربعة",4),("اربعة",4),("أربع",4),("اربع",4),
           ("ثلاثة",3),("ثلاث",3),("اثنتين",2),("اثنين",2),("ثنتين",2)]
MIN = r"(?:دقيقة|دقيقه|دقايق|دقائق)"
HOUR = r"(?:ساعة|ساعه|ساعات)"

def norm(raw): return raw.lower().translate(EASTERN).replace("ـ", "")

def relative_offset(t):
    if re.search(r"(?:ساعة|ساعه)\s*و\s*(?:نص|نصف)", t): return 5400
    if re.search(r"(?:ربع)\s*(?:ساعة|ساعه)", t): return 900
    if re.search(r"(?:نص|نصف)\s*(?:ساعة|ساعه)", t): return 1800
    if re.search(r"(?:ثلث)\s*(?:ساعة|ساعه)", t): return 1200
    if "دقيقتين" in t or "دقيقتان" in t: return 120
    if "ساعتين" in t or "ساعتان" in t: return 7200
    m = re.search(r"\d{1,3}\s*" + MIN, t)
    if m:
        n = int(re.search(r"\d+", m.group()).group())
        if n > 0: return n * 60
    m = re.search(r"\d{1,2}\s*" + HOUR, t)
    if m:
        n = int(re.search(r"\d+", m.group()).group())
        if n > 0: return n * 3600
    for w, v in SPELLED:
        if re.search(w + r"\s*" + MIN, t): return v * 60
        if re.search(w + r"\s*" + HOUR, t): return v * 3600
    if re.search(r"بعد\s*" + MIN, t): return 60
    if re.search(r"بعد\s*" + HOUR, t): return 3600
    return None

PM = ["مساء","مساءً","مساءا","بالليل","الليل","العصر","المغرب","العشاء","الظهر","بعد الظهر"]
AM = ["صباح","صباحاً","صباحا","الصبح","الفجر"]

def clock_date(t, now):
    m = re.search(r"\d{1,2}\s*[:.]\s*\d{2}", t)
    if m:
        nums = [int(x) for x in re.findall(r"\d+", m.group())]
        if len(nums) < 2: return None
        hour, minute = nums[0], nums[1]
    else:
        m = re.search(r"(?:الساعة|الساعه|ساعة|ساعه|على|عند)\s*\d{1,2}(?:\s*و\s*\d{1,2}(?:\s*(?:دقيقة|دقيقه|دقايق|دقائق))?)?", t)
        if not m: return None
        nums = [int(x) for x in re.findall(r"\d+", m.group())]
        hour, minute = nums[0], 0
        if len(nums) > 1 and 0 <= nums[1] <= 59: minute = nums[1]
    if not (0 <= hour <= 23 and 0 <= minute <= 59): return None
    if re.search(r"(?:ونص|و نص|ونصف|و نصف)", t) and minute == 0: minute = 30
    if re.search(r"(?:وربع|و ربع)", t) and minute == 0: minute = 15
    is_pm = "pm" in t or "p.m" in t or re.search(r"\d\s*م(?:\b|$)", t) or any(w in t for w in PM)
    is_am = "am" in t or "a.m" in t or re.search(r"\d\s*ص(?:\b|$)", t) or any(w in t for w in AM)
    if is_pm and hour < 12: hour += 12
    if is_am and hour == 12: hour = 0
    d = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if d > now: return d
    if not is_pm and not is_am and hour < 12:
        later = now.replace(hour=hour + 12, minute=minute, second=0, microsecond=0)
        if later > now: return later
    return d + timedelta(days=1)

def parse_alarm_date(raw, now):
    t = norm(raw)
    if "بعد" in t:
        off = relative_offset(t)
        if off is not None: return now + timedelta(seconds=off)
    d = clock_date(t, now)
    if d is not None: return d
    off = relative_offset(t)
    return None if off is None else now + timedelta(seconds=off)

# --- the contract itself, mirrored so the vocabulary cannot regress silently ---
NOW = datetime(2026, 9, 24, 17, 10, 0)
def hhmm(raw):
    d = parse_alarm_date(raw, NOW)
    return None if d is None else d.strftime("%H:%M")

CASES = [
    ("اضبطلي المنبه بعد دقيقتين شغل المنبه", "17:12"),   # the exact failing transcript
    ("اضبط لي المنبه على ٤:٥٦ pm",           "16:56"),   # the second failing transcript
    ("المنبه بعد ساعتين",                     "19:10"),
    ("صحني بعد خمس دقايق",                    "17:15"),
    ("ذكرني المنبه بعد ربع ساعة",             "17:25"),
    ("المنبه بعد نص ساعة",                    "17:40"),
    ("المنبه بعد ثلث ساعة",                   "17:30"),
    ("المنبه بعد ساعة ونص",                   "18:40"),
    ("اضبط المنبه بعد 10 دقائق",              "17:20"),
    ("المنبه بعد عشرين دقيقة",                "17:30"),
    ("اضبط المنبه الساعة 7",                  "19:00"),  # said at 17:10 with no meridiem:
                                                          # the nearest future 7 o'clock is 19:00
    ("المنبه الساعة ٨ ونص مساءً",             "20:30"),
    ("المنبه الساعة 8 وربع مساء",             "20:15"),
    ("صحني الفجر الساعة 5",                   "05:00"),
    ("المنبه الساعة 12 صباحا",                "00:00"),
    ("المنبه على الساعة 4 العصر",             "16:00"),
    ("المنبه 6:05 am",                        "06:05"),
    ("اضغط المنبه على ساعة 4 و 56",           "04:56"),   # session 18 read it as 04:00; the
                                                           # minutes are now read, and with no
                                                           # مساء/pm the nearest future 4:56
                                                           # at 17:10 is tomorrow morning
    ("اضبط المنبه على الساعة 5 و 6 دقائق p.m.", "17:06"),  # session 18: set 17:10 by mistake
    ("اضبط المنبه الساعة 4 و 56 مساء",        "16:56"),
    ("المنبه بعد 6 دقائق",                    "17:16"),   # "بعد" still means a delay
    ("المنبه الساعة 9 م",                     "21:00"),
    ("المنبه الساعة 9 ص",                     "09:00"),
]
for raw, want in CASES:
    got = hhmm(raw)
    check(f"{want} ← {raw}", got == want)

# the same sentence said in the morning resolves to the afternoon reading
NOON = datetime(2026, 9, 24, 10, 0, 0)
def hhmm_at(raw, when):
    d = parse_alarm_date(raw, when)
    return None if d is None else d.strftime("%H:%M")
check("ambiguous 4 و 56 said at 10:00 → 16:56 today",
      hhmm_at("اضغط المنبه على ساعة 4 و 56", NOON) == "16:56")
check("explicit صباحاً is respected, not shifted",
      hhmm_at("المنبه الساعة 4 و 56 صباحا", NOON) == "04:56")

for raw in ["اضبط المنبه", "المنبه من فضلك", "شغل المنبه بكرة"]:
    check(f"unreadable stays nil ← {raw}", hhmm(raw) is None)

check("a 25th hour is rejected", hhmm("المنبه الساعة 25") is None)
check("62 minutes past the hour is rejected", hhmm("المنبه 7:62") is None)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
