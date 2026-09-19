"""JARVIS Deliveries — مخرجات (فيديو/صور/PDF/…) مع نسخ وإصدارات."""
from __future__ import annotations
import os, time
import storage

DELIVERY_TYPES = [
    "video","image","image_set","pdf","docx","pptx","xlsx","zip","audio",
    "subtitle","transcript","script","prompt","caption","markdown","code","json","report","project_package",
]


def create_delivery(task_id, user_id, filename, dtype, content=None, size=None, version=1,
                     workspace_id="PERSONAL") -> dict:
    if dtype not in DELIVERY_TYPES:
        return {"ok": False, "error": "bad_delivery_type"}
    storage.ensure_dirs()
    delivery_id = storage.new_id()
    ddir = os.path.join(storage.DELIVERIES_DIR, delivery_id)
    os.makedirs(ddir, exist_ok=True)
    storage_ref = os.path.join(ddir, filename)
    if content is not None:
        if isinstance(content, bytes):
            with open(storage_ref, "wb") as f:
                f.write(content)
        else:
            with open(storage_ref, "w", encoding="utf-8") as f:
                f.write(content)
        size = os.path.getsize(storage_ref)
    rec = {
        "delivery_id": delivery_id, "task_id": task_id, "user_id": user_id,
        "workspace_id": workspace_id,
        "filename": filename, "type": dtype, "size": size, "version": version,
        "storage_ref": storage_ref, "preview_ref": None, "status": "ready",
        "created_at": time.time(),
    }
    deliveries = storage.load_deliveries()
    deliveries[delivery_id] = rec
    storage.save_deliveries(deliveries)
    return {"ok": True, "delivery": rec}


def get_delivery(delivery_id: str, user_id: str = None, workspace_id: str = None) -> dict | None:
    """ownership + workspace isolation: يُرجع التسليم فقط لصاحبه في مساحته."""
    d = storage.load_deliveries().get(delivery_id)
    if not d:
        return None
    if user_id and d.get("user_id") != user_id:
        return None
    if workspace_id is not None and d.get("workspace_id") != workspace_id:
        return None
    return d


def list_deliveries(user_id=None, workspace_id=None) -> list:
    deliveries = storage.load_deliveries()
    out = list(deliveries.values())
    if user_id:
        out = [d for d in out if d.get("user_id") == user_id]
    if workspace_id is not None:
        out = [d for d in out if d.get("workspace_id") == workspace_id]
    return out
