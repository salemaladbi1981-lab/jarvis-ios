"""اختبارات P7 — مشتقّات الوسائط: التوليد + العزل + الوسائط التالفة/غير المدعومة."""
import sys, os, shutil, hashlib

os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-deriv-tests"
os.environ["JARVIS_SESSIONS"] = "/tmp/jarvis-deriv-sessions.json"
shutil.rmtree("/tmp/jarvis-deriv-tests", ignore_errors=True)
if os.path.exists("/tmp/jarvis-deriv-sessions.json"):
    os.remove("/tmp/jarvis-deriv-sessions.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth, storage, files_api, derivatives
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)
PASS = FAIL = 0
def check(name, cond, detail=""):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name + ("  " + detail if detail else ""))
    if cond: PASS += 1
    else: FAIL += 1

storage.ensure_dirs()

def upload(user, fname, data, mime):
    chk = hashlib.sha256(data).hexdigest()
    m = files_api.init_upload(user, fname, mime, len(data), chk, "conv", "sess")
    files_api.upload_part(m["upload_id"], 0, data)
    return files_api.complete_upload(m["upload_id"])["file_id"]

# 1) صورة حقيقية → thumbnail
from PIL import Image
img = Image.new("RGB", (80, 48), (30, 120, 200))
img.save("/tmp/dv_img.png", "PNG")
fid_img = upload("salem-aladbi", "pic.png", open("/tmp/dv_img.png","rb").read(), "image/png")
f = files_api.get_file(fid_img, "salem-aladbi")
check("image thumbnail GENERATED", f["derivatives"]["thumbnail"]["status"] == "GENERATED", f["derivatives"]["thumbnail"]["status"])

# 2) مستند → metadata preview
fid_doc = upload("salem-aladbi", "note.txt", b"doc body", "text/plain")
f = files_api.get_file(fid_doc, "salem-aladbi")
check("document preview GENERATED", f["derivatives"]["preview"]["status"] == "GENERATED", f["derivatives"]["preview"]["status"])

# 3) صورة تالفة → لا انهيار + FAILED/UNSUPPORTED
fid_bad = upload("salem-aladbi", "bad.png", b"NOT-A-REAL-PNG", "image/png")
f = files_api.get_file(fid_bad, "salem-aladbi")
st = f["derivatives"]["thumbnail"]["status"]
check("corrupt image no crash + not GENERATED", st in ("FAILED", "UNSUPPORTED"), st)

# 4) نوع غير مدعوم → UNSUPPORTED
fid_x = upload("salem-aladbi", "bin.exe", b"\x00\x01\x02", "application/x-msdownload")
f = files_api.get_file(fid_x, "salem-aladbi")
st = f["derivatives"]["thumbnail"]["status"]
check("unsupported type UNSUPPORTED", st == "UNSUPPORTED", st)

# 5) endpoint: المالك يصل للمشتق
tokA = auth.create_session("salem-aladbi", workspace_id="PERSONAL")
HA = {"X-Jarvis-Session": tokA, "X-Jarvis-Workspace": "PERSONAL"}
r = client.get(f"/files/{fid_img}/derivative/thumbnail", headers=HA)
check("owner GET derivative → 200", r.status_code == 200, f"status={r.status_code}")

# 6) wrong-owner → 404
tokB = auth.create_session("other-user", workspace_id="PERSONAL")
HB = {"X-Jarvis-Session": tokB, "X-Jarvis-Workspace": "PERSONAL"}
r = client.get(f"/files/{fid_img}/derivative/thumbnail", headers=HB)
check("wrong-owner derivative → 404", r.status_code == 404, f"status={r.status_code}")

# 7) wrong-workspace → 404
tokV = auth.create_session("salem-aladbi", workspace_id="VENTURES")
HV = {"X-Jarvis-Session": tokV, "X-Jarvis-Workspace": "VENTURES"}
r = client.get(f"/files/{fid_img}/derivative/thumbnail", headers=HV)
check("wrong-workspace derivative → 404", r.status_code == 404, f"status={r.status_code}")

# 8) kind غير صالح → 404 (whitelist، بلا traversal)
r = client.get(f"/files/{fid_img}/derivative/../../etc/passwd", headers=HA)
check("path traversal kind → 404", r.status_code == 404, f"status={r.status_code}")

# 9) مشتق غير مولّد → 404
r = client.get(f"/files/{fid_doc}/derivative/thumbnail", headers=HA)
check("non-generated derivative → 404", r.status_code == 404, f"status={r.status_code}")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
