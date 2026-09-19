"""Memory store — تخزين فعلي معزول لكل مساحة عمل + دليل مصدر لكل memory item.

كل memory item يحمل: workspace_id, memory_id, type, source/provenance, created_at, verification.
كل مساحة لها مجلد + index.json مستقلان (لا مشاركة ملفات/indices/storage).
QREC_LOCKED: مجلد + فهرس مستقلان، لا يظهران في بحث/استرجاع المساحات الأخرى.
"""
from __future__ import annotations
import json, os, time, uuid
import workspace

MEMORY_ROOT = os.environ.get("JARVIS_MEMORY_ROOT", "/opt/data/memories")


def _ws_dir(workspace_id: str) -> str:
    return os.path.join(MEMORY_ROOT, workspace_id)


def _index_path(workspace_id: str) -> str:
    return os.path.join(_ws_dir(workspace_id), "index.json")


def _load_index(workspace_id: str) -> dict:
    try:
        with open(_index_path(workspace_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": {}}


def _save_index(workspace_id: str, idx: dict) -> None:
    os.makedirs(_ws_dir(workspace_id), exist_ok=True)
    tmp = _index_path(workspace_id) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    os.replace(tmp, _index_path(workspace_id))


def store(workspace_id: str, content: str, type: str = "fact", source: str = "user",
          verification: str = "unverified") -> dict:
    """يخزن memory item في مساحته فقط. لا cross-workspace."""
    if not workspace.is_valid(workspace_id):
        return {"ok": False, "error": "invalid_workspace"}
    memory_id = uuid.uuid4().hex[:16]
    item = {
        "memory_id": memory_id,
        "workspace_id": workspace_id,
        "type": type,
        "source": source,
        "content": content,
        "created_at": time.time(),
        "verification": verification,
    }
    idx = _load_index(workspace_id)
    idx["items"][memory_id] = item
    _save_index(workspace_id, idx)
    return {"ok": True, "item": item}


def retrieve(workspace_id: str, query: str, limit: int = 10) -> list[dict]:
    """بحث scoped في مساحة واحدة فقط. بلا workspace_id → لا شيء."""
    if not workspace.is_valid(workspace_id):
        return []
    idx = _load_index(workspace_id)
    q = (query or "").lower()
    out = []
    for it in idx["items"].values():
        if not q or q in (it.get("content") or "").lower():
            out.append(it)
    return out[-limit:]


def list_items(workspace_id: str) -> list[dict]:
    if not workspace.is_valid(workspace_id):
        return []
    return list(_load_index(workspace_id)["items"].values())


def get(workspace_id: str, memory_id: str) -> dict | None:
    if not workspace.is_valid(workspace_id):
        return None
    it = _load_index(workspace_id)["items"].get(memory_id)
    return it if it and it.get("workspace_id") == workspace_id else None
