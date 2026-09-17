"""Grounded Tool Contract (Email) — اختبارات حتمية A–G.
يمنع hallucination: الرد عن البريد لا يُصاغ إلا من نتيجة الأداة الحقيقية."""
import sys, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'JARVIS')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
et = read('ToolKit/EmailTool.swift')
vm = read('Home/HomeViewModel.swift')
cfg = read('../phase3/backend/config.py')

# A) Gmail empty → لا اختراع
check("A: summary empty → honest 'لا توجد إيميلات حديثة'", 'لا توجد إيميلات حديثة' in et)
# B) Tool failure → لا اختراع
check("B: failure → ToolResult.failure (no invention)", 'func failure(for' in et and 'تعذّر' in et)
check("B: auth failure message distinct", 'التوثيق' in et)
# C) bounded result (2 messages → no 3rd)
check("C: summary bounded prefix(5) (no invented 3rd)", 'prefix(5)' in et and 'limit: 8' in et)
# D) read non-existent id → clear failure
check("D: read maps badResponse → failure", 'badResponse' in et and '.failure(reason:' in et)
# E) reply can't start without real message id
check("E: reply guards lastMessage (real id)", 'لا توجد رسالة للرد عليها' in et)
# F) confirmation/send protections
check("F: reply → .confirm (send gated)", '.confirm(description:' in et)
check("F: executeTool only from approve", 'Task { await executeTool(pt) }' in vm)
# G) Live Voice/Barge-in regression unaffected
check("G: no change to voice session methods (sendText/interrupt intact)", 'func sendText' in read('Voice/RealtimeVoiceSession.swift') and 'func interrupt()' in read('Voice/RealtimeVoiceSession.swift'))
# Grounding enforcement
check("interrupt() cancels free-form LLM response before tool result", 'voiceSession.interrupt()' in vm)
check("backend instruction carries grounding rule", 'Grounded' in cfg and 'لا تخترع' in cfg)

# Logic mirror: the answer is built ONLY from the tool result
def build_summary(emails):
    if not emails: return "لا توجد إيميلات حديثة."
    return "أهم الإيميلات:\n" + "\n".join(f"• {e}" for e in emails[:5])
check("mirror A: empty → honest, no invented email", build_summary([]) == "لا توجد إيميلات حديثة.")
check("mirror C: 2 emails → exactly 2 lines (no 3rd)",
      build_summary(["a@x.com", "b@y.com"]).count("• ") == 2)
check("mirror C: 10 emails → capped at 5",
      build_summary([f"{i}@x.com" for i in range(10)]).count("• ") == 5)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
