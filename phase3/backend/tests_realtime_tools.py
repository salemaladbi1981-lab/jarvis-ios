"""Realtime Tool Orchestration — deterministic tests (grounded contract + confirmation gate)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from realtime_tools import EMAIL_TOOLS, execute_email_tool

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

# A) الأدوات الخمس موجودة بأسماء صحيحة
names = [t["name"] for t in EMAIL_TOOLS]
for n in ["email_summary", "email_search", "email_read", "email_draft_reply", "email_send"]:
    check(f"tool defined: {n}", n in names)

# B) email_send يتطلب confirmed صريحاً (parameter required)
send_tool = [t for t in EMAIL_TOOLS if t["name"] == "email_send"][0]
check("email_send requires 'confirmed' param", "confirmed" in send_tool["parameters"]["required"])

# C) الإرسال ممنوع بدون تأكيد (confirmed=False)
pending = {}
r = execute_email_tool("email_send", {"confirmed": False}, pending)
check("send without confirmation → confirmation_required", r.get("ok") is False and r.get("error") == "confirmation_required")

# D) الإرسال ممنوع بدون مسودة معلّقة
pending2 = {}
r = execute_email_tool("email_send", {"confirmed": True}, pending2)
check("send with no pending draft → no_pending_draft", r.get("ok") is False and r.get("error") == "no_pending_draft")

# E) draft reply لا يرسل (يخزّن pending فقط، لا gmail send)
# (نحاكي message_headers عبر monkeypatch لتجنب Gmail)
import realtime_tools, gmail_tools
orig = gmail_tools.message_headers
gmail_tools.message_headers = lambda mid: {"from": "x@y.com", "subject": "Hello"}
pending3 = {}
r = execute_email_tool("email_draft_reply", {"message_id": "m1", "body": "تمام"}, pending3)
check("draft_reply returns draft (no send)", r.get("ok") is True and "draft" in r)
check("draft_reply stores pending draft", pending3.get("draft", {}).get("to") == "x@y.com")
gmail_tools.message_headers = orig

# F) أداة مجهولة → unknown_tool
r = execute_email_tool("not_a_tool", {}, {})
check("unknown tool → unknown_tool", r.get("ok") is False and r.get("error") == "unknown_tool")

# G) realtime.py يربط tools + tool_choice + اعتراض function call
rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()
check("realtime.py registers tools", 'session["tools"] = EMAIL_TOOLS' in rt)
check("realtime.py tool_choice auto", 'session["tool_choice"] = "auto"' in rt)
check("realtime.py intercepts function_call_arguments.done", '"response.function_call_arguments.done"' in rt)
check("realtime.py feeds function_call_output", '"function_call_output"' in rt and '"response.create"' in rt)
check("realtime.py function-calling (no cancel-then-answer workaround)", '"function_call_output"' in rt and '"type": "response.cancel"' not in rt)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
