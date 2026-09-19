"""FastAPI integration — workspace isolation at the HTTP layer (real endpoints via TestClient).

يتطلب fastapi + httpx (بيئة اختبار منفصلة: /tmp/jarvis-testenv).
"""
import sys, os, shutil

os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-ws-http-storage"
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-ws-http-sessions.json"
shutil.rmtree("/tmp/jarvis-ws-http-storage", ignore_errors=True)
if os.path.exists("/tmp/jarvis-ws-http-sessions.json"):
    os.remove("/tmp/jarvis-ws-http-sessions.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

tok = auth.create_session("salem-aladbi", workspace_id="PERSONAL")
H = {"X-Jarvis-Session": tok}
BODY = {"session_id": "s", "conversation_id": "c", "prompt": "hello", "attachment_ids": []}

# 1) POST /tasks في PERSONAL
r = client.post("/tasks", json=BODY, headers={**H, "X-Jarvis-Workspace": "PERSONAL"})
check("POST /tasks PERSONAL → 200", r.status_code == 200)

# 2) GET /tasks في VENTURES → صفر (عزل)
r = client.get("/tasks", headers={**H, "X-Jarvis-Workspace": "VENTURES"})
check("GET /tasks VENTURES excludes PERSONAL task", r.status_code == 200 and len(r.json()) == 0)

# 3) GET /tasks في PERSONAL → واحدة
r = client.get("/tasks", headers={**H, "X-Jarvis-Workspace": "PERSONAL"})
check("GET /tasks PERSONAL sees its task", r.status_code == 200 and len(r.json()) == 1)

# 4) بلا workspace → 403
r = client.get("/tasks", headers=H)
check("no workspace header → 403", r.status_code == 403)

# 5) workspace غير صالح → 403
r = client.get("/tasks", headers={**H, "X-Jarvis-Workspace": "EVIL"})
check("invalid workspace → 403", r.status_code == 403)

# 6) QREC_LOCKED من جلسة عادية → 403
r = client.get("/tasks", headers={**H, "X-Jarvis-Workspace": "QREC_LOCKED"})
check("QREC_LOCKED from normal session → 403", r.status_code == 403)

# 7) بلا session → 401
r = client.get("/tasks", headers={"X-Jarvis-Workspace": "PERSONAL"})
check("no session → 401", r.status_code == 401)

# 8) جلسة مقفلة تفتح QREC_LOCKED
tok_locked = auth.create_session("salem-aladbi", workspace_id="QREC_LOCKED")
r = client.post("/tasks", json=BODY, headers={"X-Jarvis-Session": tok_locked, "X-Jarvis-Workspace": "QREC_LOCKED"})
check("locked session POST /tasks QREC_LOCKED → 200", r.status_code == 200)
r = client.get("/tasks", headers={"X-Jarvis-Session": tok_locked, "X-Jarvis-Workspace": "QREC_LOCKED"})
check("locked session GET /tasks QREC_LOCKED sees 1", r.status_code == 200 and len(r.json()) == 1)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
