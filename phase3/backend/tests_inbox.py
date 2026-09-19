"""UPG-3 P5 — Inbox aggregation + approvals list_pending."""
import os, sys, time, tempfile
sys.path.insert(0, os.path.dirname(__file__))

# عزل مسار approvals في ملف مؤقت
_tmp = tempfile.mkdtemp(prefix="jarvis-inbox-test-")
os.environ["JARVIS_APPROVAL_PATH"] = os.path.join(_tmp, "approvals.json")

import approval
from approval import ApprovalStore

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")

def test_list_pending():
    s = ApprovalStore()
    s._pending.clear()
    aid = s.request("core_home", "unlock-door", {"k": "v"}, workspace_id="ws1", task_id="t1")
    pend = s.list_pending("ws1")
    check("pending returned", len(pend) == 1 and pend[0]["approval_id"] == aid)
    check("workspace isolation", s.list_pending("ws2") == [])
    # expired → excluded
    s._pending[aid]["expires"] = time.time() - 1
    check("expired excluded", s.list_pending("ws1") == [])
    # resolve → excluded
    s._pending[aid]["expires"] = time.time() + 100
    s._pending[aid]["used"] = True
    check("used excluded", s.list_pending("ws1") == [])

def test_inbox_endpoint_aggregation():
    from fastapi.testclient import TestClient
    import main
    client = TestClient(main.app)
    r = client.get("/inbox", headers={"X-Jarvis-Session": "invalid"})
    # بدون جلسة موثقة → مرفوض (لا user_id من payload)
    check("inbox rejects unauthenticated", r.status_code in (401, 403, 422))

if __name__ == "__main__":
    test_list_pending()
    try:
        test_inbox_endpoint_aggregation()
    except Exception as e:
        check(f"inbox endpoint (import error: {type(e).__name__})", False)
    print(f"== RESULT: {PASS} PASS / {FAIL} FAIL ==")
    sys.exit(1 if FAIL else 0)
