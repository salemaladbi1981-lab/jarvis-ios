"""استرجاع من الذاكرة الدائمة — بلا تخمين.

يقرأ من: (1) persisted conversation log، (2) persistent memory store، (3) user memory.
إذا لا يوجد دليل صريح، يرجع no_stored_context (لا يخترع).
"""
from __future__ import annotations
import os
from pathlib import Path

MEMORY_DIR = os.environ.get("JARVIS_MEMORY_DIR", "/opt/data/memories")
USER_MEMORY = os.environ.get("JARVIS_USER_MEMORY", "/opt/data/USER.md")


def _list_memory_files() -> list[str]:
    out = []
    for root, _dirs, files in os.walk(MEMORY_DIR):
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return out


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def recall(query: str, limit: int = 5) -> dict:
    """يبحث في مخازن الذاكرة عن أدلة صريحة لـ query. بلا اختراع."""
    q = (query or "").lower()
    if not q:
        return {"found": False, "reason": "empty_query", "evidence": []}

    evidence = []
    # 1) user memory
    um = _read(USER_MEMORY)
    if q in um.lower():
        evidence.append({"source": "user_memory", "path": USER_MEMORY})

    # 2) memory store files
    for path in _list_memory_files():
        txt = _read(path)
        if q in txt.lower():
            evidence.append({"source": "memory_store", "path": path})

    # 3) persisted conversation log (state.db) — لا نفتحه هنا؛ يُحقن عبر Hermes
    #    سجلّات الجلسات تُقرأ داخل Hermes عبر session continuity header.

    found = len(evidence) > 0
    return {
        "found": found,
        "reason": "" if found else "no_stored_context",
        "evidence": evidence[:limit],
    }
