"""اختبارات ذاكرة PHASE A: recall من ملف + سجل محادثات + miss + خصوصية audit + identity."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_bridge, memory_tools, audit_memory

IDENT = {
    "user_id": "salem-aladbi",
    "session_id": "sess-mem-test",
    "conversation_id": "salem-aladbi-conv-memtest",
    "memory_namespace": "jarvis:salem-aladbi:conv-memtest",
}
results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

# 1) recall من memory file
r1 = memory_bridge.recall("Blue Falcon", dict(IDENT))
check("recall_from_memory_file",
      r1["found"] and any(e.get("source") == "memory_file" for e in r1["evidence"]),
      f"sources={r1['sources']}")

# 2) recall من conversation log (state.db فعلي)
r2 = memory_bridge.recall("هيثرو", dict(IDENT))
check("recall_from_conversation_log",
      r2["found"] and any(e.get("source") == "conversation_log" for e in r2["evidence"]),
      f"sources={r2['sources']} n={len(r2['evidence'])}")

# 3) recall miss بلا تخمين
r3 = memory_bridge.recall("zzz-nonexistent-topic-999", dict(IDENT))
check("recall_miss_no_guess",
      (not r3["found"]) and r3["reason"] == "no_stored_context",
      f"reason={r3['reason']}")

# 4) لا نص حساس داخل audit log
SENSITIVE = "SECRET-BLUE-FALCON-472-UNIQUE-STRING"
audit_path = audit_memory.AUDIT_PATH
os.makedirs(os.path.dirname(audit_path), exist_ok=True)
open(audit_path, "w", encoding="utf-8").close()
memory_tools.execute_memory_tool("jarvis_recall", {"query": SENSITIVE, **IDENT})
raw = open(audit_path, encoding="utf-8").read()
check("audit_no_sensitive_text", SENSITIVE not in raw and "query_hash" in raw, "")

# 5) identity موجودة فعليًا في recall path
r5 = memory_tools.execute_memory_tool("jarvis_recall", {"query": "Blue Falcon", **IDENT})
check("identity_in_recall_path",
      r5.get("identity", {}).get("user_id") == "salem-aladbi"
      and r5.get("identity", {}).get("memory_namespace") == IDENT["memory_namespace"],
      f"identity={r5.get('identity')}")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
