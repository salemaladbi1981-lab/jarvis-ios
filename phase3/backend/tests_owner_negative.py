"""اختبارات P6 — wrong-owner / wrong-workspace negative (HTTP).

مسار الفتح العميق/الإشعار يجب أن يُرفض fail-closed لمالك آخر أو workspace آخر:
GET /tasks/{id} و /deliveries/{id} و /conversations/{id} ترجع 404 لغير المالك.
"""
import sys, os, shutil

os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-owner-neg-storage"
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-owner-neg-sessions.json"
os.environ["JARVIS_APPROVAL_PATH"] = "/tmp/jarvis-owner-neg-approvals.json"
shutil.rmtree("/tmp/jarvis-owner-neg-storage", ignore_errors=True)
for f in ("/tmp/jarvis-owner-neg-sessions.json", "/tmp/jarvis-owner-neg-approvals.json"):
    if os.path.exists(f):
        os.remove(f)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth, storage, tasks, deliveries
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)
PASS = FAIL = 0
def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name + ("  " + detail if detail else ""))
    if cond: PASS += 1
    else: FAIL += 1

# A ينشئ مهمة + تسليم (module-level حقيقي)
storage.ensure_dirs()
t = tasks.create_task("salem-aladbi", "sess-a", "conv-a", "owner-negative-test")
task_id = t["task_id"]
d = deliveries.create_delivery(task_id, "salem-aladbi", "out.md", "markdown", content="OWNER-SECRET")
delivery_id = d["delivery"]["delivery_id"]

# B (مالك مختلف، نفس workspace)
tokB = auth.create_session("other-user", workspace_id="PERSONAL")
HB = {"X-Jarvis-Session": tokB, "X-Jarvis-Workspace": "PERSONAL"}

# === wrong-owner (مالك مختلف) ===
r = client.get(f"/tasks/{task_id}", headers=HB)
check("wrong-owner GET /tasks/{id} → 404", r.status_code == 404, f"status={r.status_code}")
r = client.get(f"/deliveries/{delivery_id}", headers=HB)
check("wrong-owner GET /deliveries/{id} → 404", r.status_code == 404, f"status={r.status_code}")
r = client.get(f"/deliveries/{delivery_id}/download", headers=HB)
check("wrong-owner GET /deliveries/{id}/download → 404", r.status_code == 404, f"status={r.status_code}")
r = client.get("/tasks", headers=HB)
check("wrong-owner list /tasks excludes A task", r.status_code == 200 and all(x.get("task_id") != task_id for x in r.json()))
r = client.get("/deliveries", headers=HB)
check("wrong-owner list /deliveries excludes A delivery", r.status_code == 200 and all(x.get("delivery_id") != delivery_id for x in r.json()))

# === wrong-workspace (نفس المالك، workspace مختلف) ===
tokA_v = auth.create_session("salem-aladbi", workspace_id="VENTURES")
HA_v = {"X-Jarvis-Session": tokA_v, "X-Jarvis-Workspace": "VENTURES"}
r = client.get(f"/tasks/{task_id}", headers=HA_v)
check("wrong-workspace GET /tasks/{id} → 404", r.status_code == 404, f"status={r.status_code}")
r = client.get(f"/deliveries/{delivery_id}", headers=HA_v)
check("wrong-workspace GET /deliveries/{id} → 404", r.status_code == 404, f"status={r.status_code}")

# === المالك الصحيح يصل ===
tokA = auth.create_session("salem-aladbi", workspace_id="PERSONAL")
HA = {"X-Jarvis-Session": tokA, "X-Jarvis-Workspace": "PERSONAL"}
r = client.get(f"/tasks/{task_id}", headers=HA)
check("owner GET /tasks/{id} → 200", r.status_code == 200, f"status={r.status_code}")
r = client.get(f"/deliveries/{delivery_id}", headers=HA)
check("owner GET /deliveries/{id} → 200", r.status_code == 200, f"status={r.status_code}")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
