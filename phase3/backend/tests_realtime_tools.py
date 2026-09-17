"""Realtime Tool Orchestration — deterministic tests (grounded contract + confirmation gate + account_id)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from realtime_tools import EMAIL_TOOLS, execute_email_tool
from test_fakes import fake_registry

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

# A) الأدوات الخمس موجودة بأسماء صحيحة
names = [t["name"] for t in EMAIL_TOOLS]
for n in ["email_summary", "email_search", "email_read", "email_draft_reply", "email_send"]:
    check(f"tool defined: {n}", n in names)

# A2) read/draft تتطلب account_id (لا اعتماد على message_id وحده)
read_t = [t for t in EMAIL_TOOLS if t["name"] == "email_read"][0]
draft_t = [t for t in EMAIL_TOOLS if t["name"] == "email_draft_reply"][0]
check("email_read requires account_id", "account_id" in read_t["parameters"]["required"])
check("email_read requires message_id", "message_id" in read_t["parameters"]["required"])
check("email_draft_reply requires account_id", "account_id" in draft_t["parameters"]["required"])

# B) email_send يتطلب confirmed صريحاً
send_tool = [t for t in EMAIL_TOOLS if t["name"] == "email_send"][0]
check("email_send requires 'confirmed' param", "confirmed" in send_tool["parameters"]["required"])

# registry افتراضي بحساب شخصي واحد (backward compatible)
reg = fake_registry([("personal", "Personal", "me@x.com", {"m1": {"from": "a@x.com", "subject": "Hello", "body": "hi there"}})])

# C) الإرسال ممنوع بدون تأكيد
r = execute_email_tool("email_send", {"confirmed": False}, {}, reg)
check("send without confirmation → confirmation_required", r.get("ok") is False and r.get("error") == "confirmation_required")

# D) الإرسال ممنوع بدون مسودة معلّقة
r = execute_email_tool("email_send", {"confirmed": True}, {}, reg)
check("send with no pending draft → no_pending_draft", r.get("ok") is False and r.get("error") == "no_pending_draft")

# E) draft reply لا يرسل (يخزّن pending فقط مع account_id)
pending3 = {}
r = execute_email_tool("email_draft_reply", {"account_id": "personal", "message_id": "m1", "body": "تمام"}, pending3, reg)
check("draft_reply returns draft (no send)", r.get("ok") is True and "draft" in r)
check("draft_reply stores account_id", pending3.get("draft", {}).get("account_id") == "personal")
check("draft_reply stores message_id", pending3.get("draft", {}).get("message_id") == "m1")

# F) أداة مجهولة → unknown_tool
r = execute_email_tool("not_a_tool", {}, {}, reg)
check("unknown tool → unknown_tool", r.get("ok") is False and r.get("error") == "unknown_tool")

# G) realtime.py يربط tools + tool_choice + اعتراض function call
rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()
check("realtime.py registers tools", 'session["tools"] = EMAIL_TOOLS' in rt)
check("realtime.py tool_choice auto", 'session["tool_choice"] = "auto"' in rt)
check("realtime.py intercepts function_call_arguments.done", '"response.function_call_arguments.done"' in rt)
check("realtime.py feeds function_call_output", '"function_call_output"' in rt and '"response.create"' in rt)
check("realtime.py function-calling (no cancel-then-answer workaround)", '"function_call_output"' in rt and '"type": "response.cancel"' not in rt)

# H) provider failure → لا success (error صريح)
p5 = {"draft": {"account_id": "personal", "message_id": "m1", "to": "a@x.com", "subject": "Re: Hello", "body": "ok"}}
reg._providers["personal"].fail = True
r = execute_email_tool("email_send", {"confirmed": True}, p5, reg)
check("provider failure → ok False (no success claim)", r.get("ok") is False)
check("provider failure → pending NOT cleared (لم يُرسل)", "draft" in p5)
reg._providers["personal"].fail = False

# I) success → success فقط بعد message id حقيقي + مسح pending + account_id
p6 = {"draft": {"account_id": "personal", "message_id": "m1", "to": "a@x.com", "subject": "Re: Hello", "body": "ok"}}
r = execute_email_tool("email_send", {"confirmed": True}, p6, reg)
check("success → sent_message_id حقيقي", r.get("ok") is True and r.get("sent_message_id") == "sent_1")
check("success → account_id حاضر", r.get("account_id") == "personal")
check("success → pending cleared (no double-send)", "draft" not in p6)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
