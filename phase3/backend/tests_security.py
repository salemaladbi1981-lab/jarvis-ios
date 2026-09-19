"""اختبارات PHASE D security: user ownership (cross-user access denied)."""
import sys, os, shutil, hashlib
os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-d-sec-test"
shutil.rmtree("/tmp/jarvis-d-sec-test", ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storage, files_api, tasks, deliveries

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

A, B = "salem-aladbi", "other-user"

# A يرفع ملف + مهمة + تسليم
data = b"SECRET-DOCUMENT-BYTES"
chk = hashlib.sha256(data).hexdigest()
meta = files_api.init_upload(A, "secret.txt", "text/plain", len(data), chk, "conv-a", "sess-a")
files_api.upload_part(meta["upload_id"], 0, data)
r = files_api.complete_upload(meta["upload_id"])
file_id = r["file"]["file_id"]
t = tasks.create_task(A, "sess-a", "conv-a", "task secret")
task_id = t["task_id"]
d = deliveries.create_delivery(task_id, A, "out.md", "markdown", content="DELIVERY-SECRET")
delivery_id = d["delivery"]["delivery_id"]

# === user مختلف (B) لا يستطيع الوصول ===
check("B_cannot_read_file_metadata", files_api.get_file(file_id, B) is None, "")
check("B_cannot_download_file", files_api.get_file(file_id, B) is None, "")
check("B_cannot_delete_file", files_api.delete_file(file_id, B)["ok"] is False, "")
check("B_cannot_read_task", tasks.get_task(task_id, B) is None, "")
check("B_cannot_read_delivery", deliveries.get_delivery(delivery_id, B) is None, "")
check("B_list_files_excludes_A", all(f["user_id"] != A for f in files_api.list_files(B)), "")
check("B_list_tasks_excludes_A", all(x["user_id"] != A for x in tasks.list_tasks(B)), "")
check("B_list_deliveries_excludes_A", all(x["user_id"] != A for x in deliveries.list_deliveries(B)), "")

# === A يصل لممتلكاته ===
check("A_can_access_own_file", files_api.get_file(file_id, A) is not None, "")
check("A_can_access_own_task", tasks.get_task(task_id, A) is not None, "")
check("A_can_access_own_delivery", deliveries.get_delivery(delivery_id, A) is not None, "")

# === derivatives صادقة (P7: مولّدة للأنواع المدعومة + الأصل محفوظ) ===
f = files_api.get_file(file_id, A)
ds = f["derivatives"]
check("document_preview_generated", ds["preview"]["status"] == "GENERATED" and ds["preview"]["ref"] is not None,
      f"preview={ds['preview']}")
check("original_preserved", os.path.exists(f.get("storage_ref", "")), f.get("storage_ref", ""))

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
