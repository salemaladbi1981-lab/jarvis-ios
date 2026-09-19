"""Barge-in server config regression: eagerness=high + interrupt_response + semantic_vad."""
import re
s = open('realtime.py', encoding='utf-8').read()
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

check("semantic_vad turn_detection", '"type": "semantic_vad"' in s)
check("eagerness=high (يلتقط speech قصير)", '"eagerness": "high"' in s)
check("interrupt_response=True", '"interrupt_response": True' in s)
check("create_response=True", '"create_response": True' in s)
check("no wake-word gate في instructions", 'جارفس مطلوب' not in s and 'wake' not in s.lower())
check("response.cancel pass-through (c2u relay)", 'client_ws.receive_text' in s and 'upstream.send' in s)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
import sys
sys.exit(1 if FAIL else 0)
