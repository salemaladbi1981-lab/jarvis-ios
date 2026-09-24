"""Voice stability — realtime.py: non-blocking tool execution + cancel tracking + structured logging."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()

# A) تنفيذ الأدوات في مهمة منفصلة (لا يعيق حلقة قراءة upstream)
check("non-blocking tool task (asyncio.create_task)", "asyncio.create_task" in rt)
check("u2c keeps forwarding loop (async for msg in upstream)", "async for msg in upstream" in rt)
check("tool dispatch runs in to_thread", "asyncio.to_thread" in rt)

# B) تتبع جيل الدور عند response.cancel — لا response.create لنتيجة أداة متأخرة
check("tracks turn_generation on response.cancel", "turn_generation" in rt)
check("late tool result skips response.create", "skip response.create" in rt and "gen == turn_generation" in rt)

# C) لا except صامت — سجلّات منظمة بلا محتوى شخصي
check("no bare except: pass", re.search(r"except\s*:\s*\n\s*pass", rt) is None)
check("no except Exception: pass", re.search(r"except\s+Exception\s*:\s*\n\s*pass", rt) is None)
check("structured trace logging (_trace)", "_trace" in rt)

# D) VAD ثابت — server_vad لأن semantic_vad تجاهل create_response=false وأعاده true
#    في session.updated (دليل console-session5)، فكان السيرفر يردّ بعد كل commit.
check("server_vad kept", '"type": "server_vad"' in rt)
check("semantic_vad not restored", '"type": "semantic_vad"' not in rt)
check("create_response=False kept (server must not answer on its own)", '"create_response": False' in rt)
check("interrupt_response=False kept (documented)", '"interrupt_response": False' in rt)

# E) التوزيع بالبادئة سليم (لا كسر للرفع/الأدوات الأخرى)
for s in ['name.startswith("maps_")', 'name.startswith("telegram_")', 'name.startswith("youtube_")', 'name.startswith("instagram_")']:
    check(f"dispatch keeps {s}", s in rt)
check("grounded function_call_output kept", '"function_call_output"' in rt)
check("no auto response.cancel in proxy", '"type": "response.cancel"' not in rt)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
