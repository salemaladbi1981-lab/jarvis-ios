"""UPG-2 — موافقات ملزمة + تدقيق مقاوم للعبث + زر إيقاف."""
import sys, os, time, json

os.environ["JARVIS_APPROVAL_PATH"] = "/tmp/jarvis-approval-test.json"
os.environ["JARVIS_AUDIT_PATH"] = "/tmp/jarvis-audit-test.jsonl"
os.environ["JARVIS_KILL_SWITCH"] = "/tmp/jarvis-kill-test.json"
for p in ["/tmp/jarvis-approval-test.json", "/tmp/jarvis-audit-test.jsonl", "/tmp/jarvis-kill-test.json"]:
    if os.path.exists(p):
        os.remove(p)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from approval import ApprovalStore
import audit, kill_switch

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

# ===== الموافقات الملزمة =====
store = ApprovalStore()
aid = store.request("concierge", "book_restaurant",
                    {"name": "Nobu", "date": "Thu 20:00"}, ttl=120,
                    workspace_id="PERSONAL", task_id="t1")
check("request returns id", bool(aid))

r = store.resolve(aid, True, agent_id="concierge", action="book_restaurant",
                  params={"name": "Nobu", "date": "Thu 20:00"}, workspace_id="PERSONAL")
check("resolve matching params → approved", r["ok"] and r["status"] == "approved")

r = store.resolve(aid, True, agent_id="concierge", action="book_restaurant",
                  params={"name": "Nobu", "date": "Thu 20:00"}, workspace_id="PERSONAL")
check("re-use → already_used (one-time)", (not r["ok"]) and r["reason"] == "already_used")

aid2 = store.request("concierge", "book_restaurant", {"name": "Nobu", "date": "Thu 20:00"},
                     ttl=120, workspace_id="PERSONAL", task_id="t2")
r = store.resolve(aid2, True, agent_id="concierge", action="book_restaurant",
                  params={"name": "Nobu", "date": "Fri 21:00"}, workspace_id="PERSONAL")
check("changed params → parameter_mismatch", (not r["ok"]) and r["reason"] == "parameter_mismatch")

aid3 = store.request("concierge", "book_restaurant", {"name": "Nobu"}, ttl=120,
                     workspace_id="PERSONAL", task_id="t3")
r = store.resolve(aid3, True, agent_id="concierge", action="book_restaurant",
                  params={"name": "Nobu"}, workspace_id="VENTURES")
check("workspace mismatch → workspace_mismatch", (not r["ok"]) and r["reason"] == "workspace_mismatch")

aid4 = store.request("x", "y", {}, ttl=-1)
r = store.resolve(aid4, True)
check("expired → expired_or_unknown", (not r["ok"]) and r["reason"] == "expired_or_unknown")

# persistence: new store reads back
store2 = ApprovalStore()
check("approval persists across store instances", aid2 in store2._pending)

# ===== التدقيق (hash chain) =====
audit.log("test_event", session_id="s", workspace_id="PERSONAL", agent="a", result="ok")
audit.log("test_event2", session_id="s", workspace_id="PERSONAL", agent="a")
v = audit.verify()
check("audit chain verifies ok", v["ok"] and v["entries"] >= 2)

# tamper: append a bad record
with open("/tmp/jarvis-audit-test.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps({"ts": time.time(), "event": "tampered", "prev_hash": "WRONG", "entry_hash": "WRONG"}) + "\n")
v = audit.verify()
check("audit detects tamper", v["ok"] is False and v["broken_at"] is not None)

# ===== زر الإيقاف =====
check("kill switch initially disengaged", not kill_switch.engaged())
kill_switch.engage("manual stop")
check("kill switch engages", kill_switch.engaged())
kill_switch.disengage()
check("kill switch disengages", not kill_switch.engaged())

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
