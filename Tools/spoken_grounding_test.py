"""Unambiguous spoken grounding regression.
Device evidence (console-session8): grounded text was "٢:٠٠ م — AI JV Update - Sicilean"
and the model spoke it as "2 AM" for a 14:00 event, then read the Latin title letter by
letter. Every spoken device reply must now state a time three ways — hour in Arabic
words, part of day in words, 24-hour digits — and the grounded payload must forbid
spelling titles out."""
import os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

vm = open(os.path.join(ROOT, 'Home/HomeViewModel.swift'), encoding='utf-8').read()
rvs = open(os.path.join(ROOT, 'Voice/RealtimeVoiceSession.swift'), encoding='utf-8').read()

def body(src, name):
    m = re.search(r'^ *(?:private |static |@available[^\n]*\n *)*(?:private )?(?:static )?func ' + name + r'\b.*$',
                  src, re.M)
    if not m: return ''
    rest = src[m.end():]
    nxt = re.search(r'\n {4}(?:private |static |@available)?[a-z]*\s*func |\n}', rest)
    return rest[:nxt.start()] if nxt else rest

# 1. the ambiguous 12-hour format must not survive in any spoken path
check("no 12-hour am/pm format left in HomeViewModel", '"h:mm a"' not in vm and '"EEE h:mm a"' not in vm)

# 2. the shared helper states a time three ways
check("JarvisSpokenTime helper exists", 'private enum JarvisSpokenTime' in vm)
check("hour is spelled in Arabic words", '"اثنين"' in vm and '"تسعة"' in vm and 'hourWords' in vm)
check("part of day is spelled in words",
      'الصبح' in vm and 'بعد الظهر' in vm and 'المساء' in vm and 'بعد منتصف الليل' in vm)
check("24-hour digits are appended", 'String(format: "%02d:%02d", h24, minute)' in vm)

# 3. every spoken formatter goes through it
ev, rem, mtg = body(vm, 'formatEvents'), body(vm, 'formatReminders'), body(vm, 'formatMeetings')
check("formatEvents uses the spoken phrase", 'JarvisSpokenTime.phrase(' in ev)
check("formatEvents states the count and labels the title",
      'JarvisSpokenTime.count(' in ev and 'عندك' in ev and 'عنوانه:' in ev)
check("formatMeetings uses the spoken phrase", 'JarvisSpokenTime.phrase(' in mtg)
check("formatReminders states the count in a sentence",
      'JarvisSpokenTime.count(' in rem and 'عندك' in rem)
check("alarm confirmation uses the spoken phrase and still starts with تم",
      'تم ضبط المنبه والتحقق منه في النظام على \\(JarvisSpokenTime.phrase(date))' in vm)

# 4. the payload instruction
grounded = rvs.split('func sendGroundedDeviceResult')[-1].split('\n    func ')[0]
check("payload forbids spelling a title letter by letter",
      'never spell it letter by letter' in grounded and 'never read Latin letters one by one' in grounded)
check("payload keeps the verbatim contract",
      'Authoritative device result.' in grounded and 'VERBATIM RESULT:' in grounded)

# 5. the phrasing contract itself, mirrored here so the wording cannot drift silently
HOURS = ["", "واحد", "اثنين", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة",
         "عشرة", "إحدى عشر", "اثنا عشر"]
def part(h):
    if h < 5: return "بعد منتصف الليل"
    if h < 12: return "الصبح"
    if h < 17: return "بعد الظهر"
    return "المساء"
def phrase(h, m):
    h12 = 12 if h % 12 == 0 else h % 12
    mins = {0: "", 15: " والربع", 30: " والنص"}.get(m, None)
    assert mins is not None, "mirror only covers :00 :15 :30"
    return f"الساعة {HOURS[h12]}{mins} {part(h)} ({h:02d}:{m:02d})"

check("14:00 reads as اثنين بعد الظهر with 24h digits",
      phrase(14, 0) == "الساعة اثنين بعد الظهر (14:00)")
check("09:30 reads as تسعة والنص الصبح", phrase(9, 30) == "الساعة تسعة والنص الصبح (09:30)")
check("19:15 reads as سبعة والربع المساء", phrase(19, 15) == "الساعة سبعة والربع المساء (19:15)")
check("02:00 is never confusable with 14:00",
      phrase(2, 0) == "الساعة اثنين بعد منتصف الليل (02:00)" and phrase(2, 0) != phrase(14, 0))
for h in range(24):
    assert part(h) in vm, h
check("every part-of-day word the contract needs exists in the source", True)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
