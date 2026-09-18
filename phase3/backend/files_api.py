"""Chunked/resumable file upload + file metadata. Preserves original (no auto quality loss)."""
from __future__ import annotations
import os, json, time
from pathlib import Path
import storage

ALLOWED_IMAGE = {"png","jpg","jpeg","gif","webp","heic"}
ALLOWED_VIDEO = {"mp4","mov","m4v","webm"}


def _upload_dir(upload_id: str) -> str:
    return os.path.join(storage.UPLOADS, upload_id)


def _upload_meta_path(upload_id: str) -> str:
    return os.path.join(_upload_dir(upload_id), "meta.json")


def _part_path(upload_id: str, n: int) -> str:
    return os.path.join(_upload_dir(upload_id), f"part_{n:05d}")


def _load_meta(upload_id: str) -> dict:
    try:
        with open(_upload_meta_path(upload_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_meta(upload_id: str, meta: dict) -> None:
    os.makedirs(_upload_dir(upload_id), exist_ok=True)
    with open(_upload_meta_path(upload_id), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)


def init_upload(user_id, filename, mime_type, size, checksum, conversation_id, session_id="") -> dict:
    storage.ensure_dirs()
    upload_id = storage.new_id()
    file_id = storage.new_id()
    total_parts = max(1, (size + storage.PART_SIZE - 1) // storage.PART_SIZE)
    meta = {
        "upload_id": upload_id, "file_id": file_id,
        "user_id": user_id, "session_id": session_id, "conversation_id": conversation_id,
        "filename": filename, "mime_type": mime_type, "size": size, "checksum": checksum,
        "total_parts": total_parts, "part_size": storage.PART_SIZE, "uploaded_parts": [],
        "created_at": time.time(), "status": "uploading",
    }
    _save_meta(upload_id, meta)
    return meta


def upload_part(upload_id: str, part_number: int, data: bytes, part_checksum: str = "") -> dict:
    meta = _load_meta(upload_id)
    if not meta:
        return {"ok": False, "error": "unknown_upload"}
    if part_number < 0 or part_number >= meta["total_parts"]:
        return {"ok": False, "error": "bad_part_number"}
    if part_checksum and storage.sha256_bytes(data) != part_checksum:
        return {"ok": False, "error": "part_checksum_mismatch"}
    p = _part_path(upload_id, part_number)
    os.makedirs(_upload_dir(upload_id), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    if part_number not in meta["uploaded_parts"]:
        meta["uploaded_parts"].append(part_number)
        meta["uploaded_parts"].sort()
    _save_meta(upload_id, meta)
    return {"ok": True, "uploaded_parts": meta["uploaded_parts"], "total_parts": meta["total_parts"]}


def upload_status(upload_id: str) -> dict:
    meta = _load_meta(upload_id)
    if not meta:
        return {"ok": False, "error": "unknown_upload"}
    missing = [n for n in range(meta["total_parts"]) if n not in meta["uploaded_parts"]]
    return {
        "ok": True, "upload_id": upload_id, "file_id": meta["file_id"],
        "uploaded_parts": meta["uploaded_parts"], "missing_parts": missing,
        "total_parts": meta["total_parts"], "status": meta["status"],
    }


def complete_upload(upload_id: str) -> dict:
    meta = _load_meta(upload_id)
    if not meta:
        return {"ok": False, "error": "unknown_upload"}
    missing = [n for n in range(meta["total_parts"]) if n not in meta["uploaded_parts"]]
    if missing:
        return {"ok": False, "error": "incomplete_upload", "missing_parts": missing}

    # تجميع الأجزاء بالترتيب
    ext = Path(meta["filename"]).suffix.lower() or ""
    orig_dir = os.path.join(storage.FILES_DIR, meta["file_id"])
    os.makedirs(orig_dir, exist_ok=True)
    orig_path = os.path.join(orig_dir, "original" + ext)
    with open(orig_path, "wb") as out:
        for n in range(meta["total_parts"]):
            with open(_part_path(upload_id, n), "rb") as p:
                out.write(p.read())

    # verify checksum
    actual = storage.sha256_file(orig_path)
    if meta["checksum"] and actual != meta["checksum"]:
        return {"ok": False, "error": "checksum_mismatch", "expected": meta["checksum"], "actual": actual}

    # media kind → preview/thumbnail/proxy placeholders (بدون تقليل الأصل)
    ext_l = ext.lstrip(".")
    media_kind = "image" if ext_l in storage.__dict__.get("ALLOWED_IMAGE", ALLOWED_IMAGE) else                  ("video" if ext_l in ALLOWED_VIDEO else "file")

    file_rec = {
        "file_id": meta["file_id"], "user_id": meta["user_id"],
        "session_id": meta["session_id"], "conversation_id": meta["conversation_id"],
        "task_id": None, "filename": meta["filename"], "mime_type": meta["mime_type"],
        "size": meta["size"], "checksum": actual, "media_kind": media_kind,
        "storage_ref": orig_path,
        "derivatives": {
            "preview": {"status": "NOT_GENERATED", "ref": None},
            "thumbnail": {"status": "NOT_GENERATED", "ref": None},
            "proxy": {"status": "NOT_GENERATED", "ref": None},
            "transcript": {"status": "NOT_GENERATED", "ref": None},
            "scene_index": {"status": "NOT_GENERATED", "ref": None},
        },
        "created_at": meta["created_at"], "processing_status": "stored",
    }
    files = storage.load_files()
    files[meta["file_id"]] = file_rec
    storage.save_files(files)

    meta["status"] = "complete"
    _save_meta(upload_id, meta)
    return {"ok": True, "file_id": meta["file_id"], "file": file_rec}


def list_files(user_id=None) -> list:
    files = storage.load_files()
    out = list(files.values())
    if user_id:
        out = [f for f in out if f.get("user_id") == user_id]
    return out


def get_file(file_id: str, user_id: str = None) -> dict | None:
    """ownership: يُرجع الملف فقط لصاحبه (user_id مطلوب للقراءة من عميل)."""
    rec = storage.load_files().get(file_id)
    if not rec:
        return None
    if user_id and rec.get("user_id") != user_id:
        return None
    return rec


def delete_file(file_id: str, user_id=None) -> dict:
    files = storage.load_files()
    rec = files.get(file_id)
    if not rec:
        return {"ok": False, "error": "not_found"}
    if user_id and rec.get("user_id") != user_id:
        return {"ok": False, "error": "forbidden"}
    if rec.get("storage_ref") and os.path.exists(rec["storage_ref"]):
        os.remove(rec["storage_ref"])
    del files[file_id]
    storage.save_files(files)
    return {"ok": True, "file_id": file_id}
