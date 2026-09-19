"""CI seed harness — يبذر بيانات حقيقية عبر الدوال الفعلية (لا Swift mock).

يُشغَّل قبل بدء الـbackend في الـCI: يكتب إلى نفس الـstores، ثم يبدأ uvicorn ويقرأها.
الإخراج: JSON يحتوي session_token + معرّفات العناصر (للـapp + deep links).
"""
import os, sys, json, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth, workspace, conversation, messages, tasks as tasks_mod, deliveries, files_api, worker, approval, storage

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _make_image() -> bytes:
    """صورة حقيقية (تدرّج لوني) لتوليد thumbnail واضح — fallback لـ1px إن غاب PIL."""
    try:
        from PIL import Image, ImageDraw
        import io
        img = Image.new("RGB", (360, 220), (14, 16, 24))
        dr = ImageDraw.Draw(img)
        for i in range(0, 360, 6):
            dr.rectangle([i, 0, i + 3, 220], fill=(24, 40 + (i * 80 // 360), 120))
        dr.ellipse([120, 50, 240, 170], outline=(212, 162, 78), width=4)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        return PNG_1PX

def seed():
    storage.ensure_dirs()
    uid = auth.PRIMARY_USER_ID
    ws = workspace.DEFAULT_WORKSPACE

    # 1) session (bootstrap → real session token)
    token = auth.bootstrap(os.environ.get("JARVIS_BOOTSTRAP_KEY", ""))

    # 2) conversation
    cs = conversation.ConversationStore()
    conv, _ = cs.get_or_create(uid, ws, source="app", title="تقرير الأداء الأسبوعي")
    cid = conv["conversation_id"]

    # 3) messages (user + assistant with citation)
    ms = messages.MessageStore()
    ms.add(cid, "user", "اعرض لي تقرير الأداء الأسبوعي", user_id=uid, workspace_id=ws)
    ms.add(cid, "assistant", "إليك ملخص الأداء مع مصدر موثوق.",
           user_id=uid, workspace_id=ws,
           citations=[{"citation_id": "cit-ci-1", "title": "تقرير السوق الأسبوعي",
                       "url": "https://example.com/weekly", "source": "web_search",
                       "snippet": "ملخص أداء الأسواق الخليجية", "order": 1}])

    # 4) task (background) → worker → delivery حقيقية
    t = tasks_mod.create_task(uid, "sess-ci-1", cid, "أنشئ تقرير أداء كاملًا",
                              None, "core_writer", None, ws)
    tid = t["task_id"]
    worker.enqueue(tid)
    def _fake_run(task, ctx, ident):
        return {"ok": True, "answer": "تقرير الأداء جاهز ✅ (نسخة CI حقيقية عبر pipeline الـworker)"}
    worker.process_task(tid, run_fn=_fake_run)

    # 5) ملف صورة (attachment) عبر الـupload API الفعلي + مشتق thumbnail
    img_bytes = _make_image()
    up = files_api.init_upload(uid, "chart.png", "image/png", len(img_bytes), "", cid, workspace_id=ws)
    files_api.upload_part(up["upload_id"], 0, img_bytes, "", uid)
    done = files_api.complete_upload(up["upload_id"], uid)
    fid = done["file_id"]
    ms.add(cid, "user", "هذا الرسم البياني للأداء", user_id=uid, workspace_id=ws, attachment_refs=[fid])

    # 5b) مستند → مشتق preview metadata
    doc_bytes = "JARVIS P7 document preview metadata — CI seed".encode("utf-8")
    up2 = files_api.init_upload(uid, "brief.txt", "text/plain", len(doc_bytes), "", cid, workspace_id=ws)
    files_api.upload_part(up2["upload_id"], 0, doc_bytes, "", uid)
    done2 = files_api.complete_upload(up2["upload_id"], uid)
    doc_fid = done2["file_id"]

    # 6) موافقة معلّقة (Inbox → action required)
    astore = approval.ApprovalStore()
    aid = astore.request("core_home", "unlock-door", {"device": "main"}, workspace_id=ws, task_id=tid)

    # delivery id من الـpipeline
    dels = deliveries.list_deliveries(uid, ws)
    did = dels[0]["delivery_id"] if dels else None

    out = {
        "session_token": token,
        "conversation_id": cid,
        "task_id": tid,
        "delivery_id": did,
        "file_id": fid,
        "document_file_id": doc_fid,
        "approval_id": aid,
        "user_id": uid,
        "workspace_id": ws,
    }
    print("CI_SEED_RESULT " + json.dumps(out, ensure_ascii=False))
    out_path = os.environ.get("CI_SEED_OUT", "/tmp/jarvis_ci_seed.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out

if __name__ == "__main__":
    seed()
