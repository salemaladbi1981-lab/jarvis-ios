"""Multi-Account Email — deterministic tests (unified inbox, account_id grounding, cross-account safety)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from realtime_tools import execute_email_tool, build_email_tools, account_list_hint
from test_fakes import fake_registry

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

# Registry بحسابين: personal + work (نفس message id "m1" في كليهما عمداً)
reg = fake_registry([
    ("personal", "Personal", "me@personal.com",
     {"m1": {"from": "friend@x.com", "subject": "Personal note", "body": "hello from personal"},
      "m2": {"from": "bank@x.com", "subject": "Statement", "body": "personal bank"}}),
    ("work", "Work", "me@work.com",
     {"m1": {"from": "boss@x.com", "subject": "Work note", "body": "hello from work"},
      "w1": {"from": "client@x.com", "subject": "Invoice", "body": "work invoice"}}),
])

# 1) حساب واحد backward compatible
one = fake_registry([("personal", "Personal", "me@x.com", {"m1": {"from": "a@x.com", "subject": "Hi", "body": "x"}})])
r = execute_email_tool("email_summary", {"limit": 5}, {}, one)
check("single account → summary ok + account_id tagged", r.get("ok") and r["emails"][0]["account_id"] == "personal")

# 2) حسابان → unified summary صحيح
r = execute_email_tool("email_summary", {"limit": 5}, {}, reg)
emails = r.get("emails", [])
aids = {e["account_id"] for e in emails}
check("unified summary returns messages from BOTH accounts", {"personal", "work"} <= aids)
check("every email tagged account_id", all(e.get("account_id") for e in emails))
check("every email tagged account (display name)", all(e.get("account") for e in emails))
check("unified summary count = 4", len(emails) == 4)

# 3) same message id بين حسابين لا تختلط
r_p = execute_email_tool("email_read", {"account_id": "personal", "message_id": "m1"}, {}, reg)
r_w = execute_email_tool("email_read", {"account_id": "work", "message_id": "m1"}, {}, reg)
check("same id 'm1' → personal returns personal body", r_p["message"]["body"] == "hello from personal")
check("same id 'm1' → work returns work body", r_w["message"]["body"] == "hello from work")
check("read returns account_id", r_p["message"].get("account_id") == "personal")

# 4) read يحافظ على account_id
r = execute_email_tool("email_read", {"account_id": "work", "message_id": "w1"}, {}, reg)
check("read work w1 → account_id work", r["message"].get("account_id") == "work")

# 5) reply يحافظ على الحساب الأصلي
pending = {}
r = execute_email_tool("email_draft_reply", {"account_id": "personal", "message_id": "m1", "body": "شكراً"}, pending, reg)
check("draft_reply stores original account_id", pending["draft"]["account_id"] == "personal")
r = execute_email_tool("email_send", {"confirmed": True}, pending, reg)
check("send goes from the draft's account (personal)", r.get("ok") and r.get("account_id") == "personal")
check("personal provider sent (not work)", len(reg._providers["personal"].sent) == 1 and len(reg._providers["work"].sent) == 0)

# 6) محاولة send من حساب مختلف → blocked
pending2 = {}
execute_email_tool("email_draft_reply", {"account_id": "personal", "message_id": "m1", "body": "hi"}, pending2, reg)
r = execute_email_tool("email_send", {"confirmed": True, "account_id": "work"}, pending2, reg)
check("send from wrong account → account_mismatch (blocked)", r.get("ok") is False and r.get("error") == "account_mismatch")
check("blocked send → pending NOT cleared", "draft" in pending2)
check("blocked send → no extra sent message", len(reg._providers["work"].sent) == 0)

# 7) ambiguous account → no send
r = execute_email_tool("email_read", {"message_id": "m1"}, {}, reg)
check("read without account_id → account_required", r.get("ok") is False and r.get("error") == "account_required")
r = execute_email_tool("email_draft_reply", {"message_id": "m1", "body": "x"}, {}, reg)
check("draft without account_id → account_required", r.get("ok") is False and r.get("error") == "account_required")

# 8) provider failure في حساب لا يكسر الآخر
reg._providers["work"].fail = True
r = execute_email_tool("email_summary", {"limit": 5}, {}, reg)
aids = {e["account_id"] for e in r.get("emails", [])}
check("work fails → personal still returned", r.get("ok") and aids == {"personal"})
reg._providers["work"].fail = False

# 9) search بحساب محدد يرجع حساباً واحداً فقط
r = execute_email_tool("email_search", {"account_id": "work", "query": "invoice"}, {}, reg)
aids = {e["account_id"] for e in r.get("emails", [])}
check("search account_id=work → work only", r.get("ok") and aids == {"work"})

# 10) account_not_found — أي account_id غير موجود → خطأ صريح (لا fallback فارغ)
r = execute_email_tool("email_summary", {"account_id": "nonexistent", "limit": 5}, {}, reg)
check("summary unknown account → account_not_found", r.get("ok") is False and r.get("error") == "account_not_found")
r = execute_email_tool("email_search", {"account_id": "nonexistent", "query": "x"}, {}, reg)
check("search unknown account → account_not_found", r.get("ok") is False and r.get("error") == "account_not_found")
r = execute_email_tool("email_read", {"account_id": "nonexistent", "message_id": "m1"}, {}, reg)
check("read unknown account → account_not_found", r.get("ok") is False and r.get("error") == "account_not_found")
r = execute_email_tool("email_draft_reply", {"account_id": "nonexistent", "message_id": "m1", "body": "x"}, {}, reg)
check("draft unknown account → account_not_found", r.get("ok") is False and r.get("error") == "account_not_found")

# 11) Dynamic Account Grounding — الحسابات الحقيقية للـ reg محقونة في الوصف (personal + work)
tools = build_email_tools(reg)
summary_tool = [t for t in tools if t["name"] == "email_summary"][0]
check("summary desc lists 'personal'", "personal" in summary_tool["description"])
check("summary desc lists 'work'", "work" in summary_tool["description"])
check("summary desc does NOT list 'hotmail'", "hotmail" not in summary_tool["description"])
check("summary desc forbids inventing account_id", "NEVER invent" in summary_tool["description"])

# 12) حساب مستقبلي يظهر تلقائياً (بلا hard-code)
reg3 = fake_registry([
    ("personal", "Personal", "p@x.com", {}),
    ("hotmail", "Hotmail", "h@x.com", {}),
    ("studio", "Salem AI Studio", "s@x.com", {}),
])
hint = account_list_hint(reg3)
check("future account 'studio' appears automatically", "studio" in hint and "Salem AI Studio" in hint)
check("hint lists all 3 accounts", all(a in hint for a in ("personal", "hotmail", "studio")))

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
