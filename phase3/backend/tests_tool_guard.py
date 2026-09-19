"""UPG-2 — منع تقني عند حدود التنفيذ (Tool Guard) + enforcement في مسار الوكيل."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tool_guard, agent_runner

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# A) tool_guard: أفعال غير قابلة للعكس
check("email_send sensitive", tool_guard.is_sensitive("email_send"))
check("telegram_send sensitive", tool_guard.is_sensitive("telegram_send"))
check("maps_navigate NOT sensitive", not tool_guard.is_sensitive("maps_navigate"))

# B) sensitive بلا موافقة → ممنوع
r = tool_guard.check("email_send", None)
check("email_send without approval → blocked", (not r["allowed"]) and r["reason"] == "approval_required")
# sensitive بموافقة صالحة → مسموح
r = tool_guard.check("email_send", {"valid": True, "approval_id": "a1"})
check("email_send with valid approval → allowed", r["allowed"])
# موافقة غير صالحة → ممنوع
r = tool_guard.check("email_send", {"valid": False})
check("email_send with invalid approval → blocked", not r["allowed"])
# غير sensitive → مسموح دائمًا
check("maps_navigate allowed without approval", tool_guard.check("maps_navigate", None)["allowed"])

# C) enforcement في مسار الوكيل: sensitive معطّل تقنيًا
prof = agent_runner.enforce("core_coordinator", ["email_send"], [])
check("agent path blocks email_send (sensitive)", (not prof["allowed"]) and "email_send" in prof["sensitive_blocked"])
# أداة غير sensitive مسموحة (لو ضمن allowlist)
prof2 = agent_runner.enforce("core_coordinator", ["maps_navigate"], [])
check("agent path: non-sensitive not in sensitive_blocked", "maps_navigate" not in prof2["sensitive_blocked"])

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
