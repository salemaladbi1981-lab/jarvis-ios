"""Language/dialect config — Gulf default (unspecified only) + explicit requests win + no AI-apology."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

cfg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py"), encoding="utf-8").read()

check("no hard dialect prohibition (وليس المصرية أبداً)", "وليس المصرية أبداً" not in cfg)
check("Gulf is DEFAULT (افتراضيًا), not a hard constraint", "افتراضي" in cfg and "الخليجية البيضاء" in cfg)
check("explicit request priority over default persona", "أولوية الطلب الصريح" in cfg)
check("distinguish content language vs pronunciation accent", "ميّز بين لغة المحتوى" in cfg)
check("persist chosen language until owner changes it", "حافظ على اللغة/اللكنة المختارة" in cfg)
check("no apologetic AI intro before switching", "دون مقدمات اعتذار" in cfg)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
