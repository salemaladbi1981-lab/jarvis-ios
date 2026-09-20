"""استرجاع من الذاكرة — بلا تخمين.

المصادر الفعلية:
  1) user memory (USER.md)
  2) memory store files (/opt/data/memories/*.md)
  3) persisted conversation log (state.db messages) — retrieval حقيقي

النتيجة إما evidence صريحة أو no_stored_context.
"""
from __future__ import annotations
import os, sqlite3
from pathlib import Path
import memory_store
import workspace
import messages

MEMORY_DIR = os.environ.get("JARVIS_MEMORY_DIR", "/opt/data/memories")
USER_MEMORY = os.environ.get("JARVIS_USER_MEMORY", "/opt/data/USER.md")
STATE_DB = os.environ.get("JARVIS_STATE_DB", "/opt/data/state.db")

PRIMARY_USER_ID = "salem-aladbi"

RECALL_PHRASES = (
    "وش كنا", "كنا نتكلم", "وش قلت", "قلت لك", "تذكر", "وش سوينا",
    "وش كانت", "ماذا كنا", "what were we", "what did i", "what did you tell",
    "remember what", "recall",
)


_WORKSPACE_DIRS = ("PERSONAL", "SALEM_AI_STUDIO", "VENTURES", "QREC_LOCKED")


def _list_memory_files(workspace_id: str = "PERSONAL") -> list[str]:
    """ملفات الذاكرة الخاصة بمساحة العمل فقط (مجلد منفصل لكل مساحة).

    PERSONAL يبحث أيضًا في المجلد المسطح القديم (legacy) عدا مجلدات المساحات الأخرى — توافق رجعي.
    """
    out = []
    if workspace_id == "PERSONAL":
        for root, dirs, files in os.walk(MEMORY_DIR):
            dirs[:] = [d for d in dirs if d not in _WORKSPACE_DIRS]  # لا ننزل لمجلدات المساحات
            for f in files:
                if f.endswith(".md"):
                    out.append(os.path.join(root, f))
    ws_dir = os.path.join(MEMORY_DIR, workspace_id)
    for root, _dirs, files in os.walk(ws_dir):
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return out


def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""


def _recall_memory_files(query: str, workspace_id: str = "PERSONAL") -> list[dict]:
    q = query.lower()
    out = []
    # user memory العام (لا يُبحث في QREC_LOCKED)
    if workspace_id == "PERSONAL":
        um = _read(USER_MEMORY)
        if q in um.lower():
            start = max(0, um.lower().find(q) - 100)
            out.append({"source": "user_memory", "path": USER_MEMORY, "workspace_id": workspace_id,
                        "snippet": um[start:start + 500]})
    # ملفات الذاكرة الخاصة بالمساحة
    for path in _list_memory_files(workspace_id):
        content = _read(path)
        if q in content.lower():
            start = max(0, content.lower().find(q) - 100)
            out.append({"source": "memory_file", "path": path, "workspace_id": workspace_id,
                        "snippet": content[start:start + 500]})
    # memory store (index + metadata + دليل مصدر) الخاص بالمساحة
    for it in memory_store.retrieve(workspace_id, q):
        out.append({
            "source": "memory_store",
            "memory_id": it["memory_id"], "workspace_id": it["workspace_id"],
            "type": it.get("type"), "source_provenance": it.get("source"),
            "verification": it.get("verification"), "created_at": it.get("created_at"),
            "snippet": (it.get("content") or "")[:200],
        })
    return out


def _scoped_log(query: str, user_id: str, workspace_id: str, limit: int) -> list[dict]:
    """Only records with explicit user AND workspace provenance can answer recall.

    Legacy Hermes databases without workspace metadata are skipped. Their rows
    must be migrated with verified provenance before being exposed to recall.
    The current app message store already carries both fields.
    """
    out = []
    for item in messages.MessageStore()._load().values():
        if item.get("user_id") != user_id or item.get("workspace_id") != workspace_id:
            continue
        content = item.get("content") or ""
        if content and (not query or query.casefold() in content.casefold()):
            out.append({"source": "conversation_log", "workspace_id": workspace_id,
                        "message_id": item["message_id"], "conversation_id": item["conversation_id"],
                        "role": item.get("role"), "snippet": content[:500],
                        "timestamp": item.get("created_at", 0)})
    try:
        with sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
            if {"workspace_id", "user_id"}.issubset(columns):
                rows = conn.execute("""
                    SELECT m.content, m.role, m.timestamp, s.id AS session_id
                    FROM messages m JOIN sessions s ON m.session_id = s.id
                    WHERE m.active = 1 AND s.user_id = ? AND s.workspace_id = ?
                      AND (? = '' OR instr(lower(m.content), lower(?)) > 0)
                    ORDER BY m.timestamp DESC LIMIT ?
                """, (user_id, workspace_id, query, query, limit)).fetchall()
                for row in rows:
                    out.append({"source": "conversation_log", "workspace_id": workspace_id,
                                "session_id": row["session_id"], "role": row["role"],
                                "snippet": (row["content"] or "")[:500], "timestamp": row["timestamp"] or 0})
    except (sqlite3.Error, OSError):
        pass  # An unavailable source supplies no evidence; never invent a record.
    return sorted(out, key=lambda item: item.get("timestamp", 0), reverse=True)[:limit]


def _recall_conversation_log(query: str, user_id: str, limit: int, workspace_id: str = "PERSONAL") -> list[dict]:
    return _scoped_log(query.strip(), user_id, workspace_id, limit)


def _recall_recent(user_id: str, limit: int, workspace_id: str = "PERSONAL") -> list[dict]:
    return _scoped_log("", user_id, workspace_id, limit)


def _is_recall_query(query: str) -> bool:
    q = query.lower()
    return any(p in q for p in RECALL_PHRASES)


def recall(query: str, identity: dict, limit: int = 5) -> dict:
    """استرجاع موحد: ملفات memory + سجل المحادثات. بلا اختراع."""
    q = (query or "").strip()
    if not q:
        return {"found": False, "reason": "empty_query", "sources": [], "evidence": []}
    user_id = identity.get("user_id", "") or ""
    workspace_id = identity.get("workspace_id")
    if not user_id or not workspace.is_valid(workspace_id):
        return {"found": False, "reason": "identity_required", "sources": [], "evidence": []}
    evidence, sources = [], []

    if _is_recall_query(q):
        recent = _recall_recent(user_id, limit, workspace_id)
        evidence += recent
        if recent and not any("error" in e for e in recent):
            sources.append("conversation_log_recent")
    else:
        mf = _recall_memory_files(q, workspace_id) if user_id == PRIMARY_USER_ID else []
        evidence += mf
        if mf:
            sources.append("memory_file" if not any("memory_store" == e.get("source") for e in mf) else "memory_store")
        cl = _recall_conversation_log(q, user_id, limit, workspace_id)
        evidence += cl
        if cl and not any("error" in e for e in cl):
            sources.append("conversation_log")

    found = len(evidence) > 0 and not all("error" in e for e in evidence)
    return {
        "found": found,
        "reason": "" if found else "no_stored_context",
        "sources": sources,
        "evidence": evidence[:limit],
    }
