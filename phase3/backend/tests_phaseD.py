"""اختبارات PHASE D: upload/resume/task/delivery (backend end-to-end)."""
import sys, os, shutil, hashlib
# تخزين نظيف للاختبار
os.environ["JARVIS_STORAGE_ROOT"] = "/tmp/jarvis-d-test-storage"
shutil.rmtree("/tmp/jarvis-d-test-storage", ignore_errors=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storage, files_api, tasks, deliveries

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

U = "salem-aladbi"; S = "sess-d"; C = "conv-d"

# --- ملفات اختبار ---
os.makedirs("/tmp/jarvis-d-files", exist_ok=True)
img = open("/tmp/jarvis-d-files/test.png","wb"); img.write(b"\x89PNG\r\n" + os.urandom(5000)); img.close()
pdf = open("/tmp/jarvis-d-files/test.pdf","wb"); pdf.write(b"%PDF-1.4 " + os.urandom(8000)); pdf.close()
big = open("/tmp/jarvis-d-files/large.mp4","wb"); big.write(os.urandom(10*1024*1024)); big.close()  # 10MB → 3 أجزاء

def full_upload(path, mime):
    data = open(path, "rb").read()
    chk = hashlib.sha256(data).hexdigest()
    meta = files_api.init_upload(U, os.path.basename(path), mime, len(data), chk, C, S)
    n = meta["total_parts"]
    for i in range(n):
        part = data[i*storage.PART_SIZE:(i+1)*storage.PART_SIZE]
        r = files_api.upload_part(meta["upload_id"], i, part)
        assert r["ok"], r
    return files_api.complete_upload(meta["upload_id"]), chk, len(data)

# 1) رفع صورة
r_img, chk_img, sz_img = full_upload("/tmp/jarvis-d-files/test.png", "image/png")
orig_img = open("/tmp/jarvis-d-files/test.png","rb").read()
stored_img = open(r_img["file"]["storage_ref"],"rb").read()
check("upload_image", r_img["ok"] and r_img["file"]["media_kind"] == "image",
      f"file_id={r_img['file']['file_id']}")
check("image_original_preserved", stored_img == orig_img and r_img["file"]["checksum"] == chk_img,
      f"size={sz_img}")

# 2) رفع PDF
r_pdf, chk_pdf, sz_pdf = full_upload("/tmp/jarvis-d-files/test.pdf", "application/pdf")
check("upload_pdf", r_pdf["ok"] and r_pdf["file"]["mime_type"] == "application/pdf",
      f"size={sz_pdf}")

# 3) رفع فيديو كبير (chunked 3 أجزاء)
r_vid, chk_vid, sz_vid = full_upload("/tmp/jarvis-d-files/large.mp4", "video/mp4")
check("upload_large_video_chunked", r_vid["ok"] and r_vid["file"]["media_kind"] == "video",
      f"size={sz_vid} parts={r_vid['file']['size']}")
check("large_video_original_preserved", r_vid["file"]["checksum"] == chk_vid and r_vid["file"]["size"] == sz_vid, "")

# 4) استئناف رفع بعد قطع (resume)
data = open("/tmp/jarvis-d-files/large.mp4","rb").read()
chk = hashlib.sha256(data).hexdigest()
meta = files_api.init_upload(U, "resume.mp4", "video/mp4", len(data), chk, C, S)
# نرفع جزء 0 فقط ثم "ينقطع"
files_api.upload_part(meta["upload_id"], 0, data[0:storage.PART_SIZE])
st = files_api.upload_status(meta["upload_id"])
check("resume_detects_missing_parts", st["uploaded_parts"] == [0] and st["missing_parts"] == [1,2],
      f"missing={st['missing_parts']}")
# استئناف: نرفع الباقي
for i in st["missing_parts"]:
    files_api.upload_part(meta["upload_id"], i, data[i*storage.PART_SIZE:(i+1)*storage.PART_SIZE])
done = files_api.complete_upload(meta["upload_id"])
check("resume_completes_successfully", done["ok"] and done["file"]["checksum"] == chk, "")

# 5) إنشاء Task + تقدم الحالة
t = tasks.create_task(U, S, C, "حوّل الفيديو إلى نسخة 60 ثانية",
                      attachment_ids=[r_vid["file"]["file_id"]],
                      selected_agent="core_producer", selected_capability="video")
check("create_task", t["task_id"] and t["status"] == "uploaded" and r_vid["file"]["file_id"] in t["attachment_ids"], "")
# تقدم الحالة عبر المراحل
seq = ["queued","ingesting","analyzing","processing","generating","rendering","ready"]
ok_seq = all(tasks.set_status(t["task_id"], s)["ok"] for s in seq)
final = tasks.get_task(t["task_id"])
check("task_state_transitions", ok_seq and final["status"] == "ready" and final["completed_at"],
      f"status={final['status']}")

# 6) إنشاء Delivery فعلي + استرجاعه
d = deliveries.create_delivery(t["task_id"], U, "video_60s.mp4", "video", content=b"FAKE-MP4-DELIVERY-BYTES")
check("create_delivery", d["ok"] and d["delivery"]["type"] == "video" and d["delivery"]["size"] == len(b"FAKE-MP4-DELIVERY-BYTES"), "")

# 7) استرجاع الملف من Deliveries
retrieved = open(d["delivery"]["storage_ref"], "rb").read()
check("retrieve_delivery", retrieved == b"FAKE-MP4-DELIVERY-BYTES", f"bytes={len(retrieved)}")

# ربط الـ delivery بالـ task
tasks.add_output(t["task_id"], d["delivery"]["delivery_id"])
ft = tasks.get_task(t["task_id"])
check("task_outputs_linked", d["delivery"]["delivery_id"] in ft["outputs"], "")

# identity binding
f = files_api.get_file(r_img["file"]["file_id"])
check("file_bound_to_user", f["user_id"] == U and f["conversation_id"] == C and f["session_id"] == S, "")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
