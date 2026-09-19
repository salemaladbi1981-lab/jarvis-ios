"""UPG-2 workspace isolation — المساحات الأربع + منع cross-workspace + QREC_LOCKED."""
import sys, os, shutil, hashlib

os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-ws-test-storage"
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-ws-test-sessions.json"
shutil.rmtree("/tmp/jarvis-ws-test-storage", ignore_errors=True)
if os.path.exists("/tmp/jarvis-ws-test-sessions.json"):
    os.remove("/tmp/jarvis-ws-test-sessions.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace, tasks, files_api, deliveries, auth

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

U = "salem-aladbi"

# A) تعاريف المساحات
check("4 workspaces defined", workspace.WORKSPACES == ["PERSONAL", "SALEM_AI_STUDIO", "VENTURES", "QREC_LOCKED"])
check("is_valid ok", workspace.is_valid("VENTURES") and not workspace.is_valid("HACK"))

# B) authorize — لا قيمة افتراضية تمنح وصولًا
check("authorize rejects missing workspace", workspace.authorize("PERSONAL", None) is None)
check("authorize rejects invalid workspace", workspace.authorize("PERSONAL", "EVIL") is None)
check("authorize allows normal workspace", workspace.authorize("PERSONAL", "VENTURES") == "VENTURES")

# C) QREC_LOCKED gate
check("normal session cannot open QREC_LOCKED", workspace.authorize("PERSONAL", "QREC_LOCKED") is None)
check("locked session opens QREC_LOCKED", workspace.authorize("QREC_LOCKED", "QREC_LOCKED") == "QREC_LOCKED")

# D) عزل المهام
t_personal = tasks.create_task(U, "s1", "c1", "personal task", workspace_id="PERSONAL")
t_ventures = tasks.create_task(U, "s1", "c1", "ventures task", workspace_id="VENTURES")
check("task carries workspace_id", t_personal["workspace_id"] == "PERSONAL")
check("list_tasks(PERSONAL) excludes VENTURES", all(t["workspace_id"] == "PERSONAL" for t in tasks.list_tasks(user_id=U, workspace_id="PERSONAL")))
check("get_task cross-workspace denied", tasks.get_task(t_ventures["task_id"], user_id=U, workspace_id="PERSONAL") is None)
check("get_task same-workspace ok", tasks.get_task(t_ventures["task_id"], user_id=U, workspace_id="VENTURES") is not None)

# E) عزل الملفات
data = b"hello workspace"
chk = hashlib.sha256(data).hexdigest()
m = files_api.init_upload(U, "a.txt", "text/plain", len(data), chk, "c1", "s1", workspace_id="PERSONAL")
files_api.upload_part(m["upload_id"], 0, data, "", U)
files_api.complete_upload(m["upload_id"], U)
check("file carries workspace_id", files_api.get_file(m["file_id"], U, "PERSONAL") is not None)
check("file cross-workspace denied", files_api.get_file(m["file_id"], U, "VENTURES") is None)
check("list_files(PERSONAL) excludes others", all(f.get("workspace_id") == "PERSONAL" for f in files_api.list_files(U, "PERSONAL")))

# F) عزل التسليم
d = deliveries.create_delivery(t_personal["task_id"], U, "out.txt", "markdown", content="hi", workspace_id="PERSONAL")
check("delivery cross-workspace denied", deliveries.get_delivery(d["delivery"]["delivery_id"], U, "VENTURES") is None)
check("delivery same-workspace ok", deliveries.get_delivery(d["delivery"]["delivery_id"], U, "PERSONAL") is not None)

# G) عزل QREC_LOCKED على مستوى السجلات
t_locked = tasks.create_task(U, "s2", "c2", "locked task", workspace_id="QREC_LOCKED")
check("locked task not visible in PERSONAL", tasks.get_task(t_locked["task_id"], U, "PERSONAL") is None)
check("locked task visible in QREC_LOCKED", tasks.get_task(t_locked["task_id"], U, "QREC_LOCKED") is not None)

# H) الجلسة تحمل workspace_id
tok = auth.create_session(U, workspace_id="VENTURES")
s = auth.resolve_session(tok)
check("session carries workspace_id", s["workspace_id"] == "VENTURES")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
