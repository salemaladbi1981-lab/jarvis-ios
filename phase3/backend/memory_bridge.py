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
    if workspace_id != "QREC_LOCKED":
        um = _read(USER_MEMORY)
        if q in um.lower():
            out.append({"source": "user_memory", "path": USER_MEMORY, "workspace_id": workspace_id})
    # ملفات الذاكرة الخاصة بالمساحة
    for path in _list_memory_files(workspace_id):
        if q in _read(path).lower():
            out.append({"source": "memory_file", "path": path, "workspace_id": workspace_id})
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


def _scope_user(user_id: str):
    """scoping: المستخدم الأساسي (salem-aladbi) = كل جلسات هذا الـ Hermes أحادي المستخدم
    (Hermes يخزّن user_id كـ None أو chat_id لهذا المستخدم). أي user_id آخر → فلترة دقيقة."""
    if user_id in ("", PRIMARY_USER_ID):
        return None
    return user_id


def _recall_conversation_log(query: str, user_id: str, limit: int) -> list[dict]:
    """بحث فعلي في state.db (messages) — سجل المحادثات الدائم."""
    q = (query or "").strip()
    out = []
    if not q:
        return out
    scoped = _scope_user(user_id)
    try:
        conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        like = f"%{q}%"
        rows = conn.execute("""
            SELECT m.content, m.role, m.timestamp, s.id AS session_id, s.title, s.user_id
            FROM messages m JOIN sessions s ON m.session_id = s.id
            WHERE m.content LIKE ? AND m.active = 1
              AND (? IS NULL OR s.user_id = ?)
            ORDER BY m.timestamp DESC LIMIT ?
        """, (like, scoped, scoped, limit)).fetchall()
        for r in rows:
            out.append({
                "source": "conversation_log",
                "session_id": r["session_id"],
                "title": r["title"],
                "role": r["role"],
                "snippet": (r["content"] or "")[:200],
            })
        conn.close()
    except Exception as e:
        out.append({"source": "conversation_log", "error": str(e)})
    return out


def _recall_recent(user_id: str, limit: int) -> list[dict]:
    """أحدث مواضيع المحادثات للمستخدم (سجل فعلي من state.db)."""
    out = []
    try:
        conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        scoped = _scope_user(user_id)
        rows = conn.execute("""
            SELECT s.id, s.title, s.started_at,
                   (SELECT content FROM messages m WHERE m.session_id = s.id
                     AND m.role = 'user' AND m.active = 1
                     ORDER BY m.timestamp DESC LIMIT 1) AS last_user_msg
            FROM sessions s
            WHERE s.title IS NOT NULL AND s.title != ''
              AND (? IS NULL OR s.user_id = ?)
            ORDER BY s.started_at DESC LIMIT ?
        """, (scoped, scoped, limit)).fetchall()
        for r in rows:
            out.append({
                "source": "conversation_log",
                "session_id": r["id"],
                "title": r["title"],
                "last_user_msg": (r["last_user_msg"] or "")[:200],
            })
        conn.close()
    except Exception as e:
        out.append({"source": "conversation_log", "error": str(e)})
    return out


def _is_recall_query(query: str) -> bool:
    q = query.lower()
    return any(p in q for p in RECALL_PHRASES)


def recall(query: str, identity: dict, limit: int = 5) -> dict:
    """استرجاع موحد: ملفات memory + سجل المحادثات. بلا اختراع."""
    q = (query or "").strip()
    if not q:
        return {"found": False, "reason": "empty_query", "sources": [], "evidence": []}
    user_id = identity.get("user_id", "") or ""
    workspace_id = identity.get("workspace_id", "PERSONAL")
    evidence, sources = [], []

    if _is_recall_query(q):
        recent = _recall_recent(user_id, limit)
        evidence += recent
        if recent and not any("error" in e for e in recent):
            sources.append("conversation_log_recent")
    else:
        mf = _recall_memory_files(q, workspace_id)
        evidence += mf
        if mf:
            sources.append("memory_file" if not any("memory_store" == e.get("source") for e in mf) else "memory_store")
        cl = _recall_conversation_log(q, user_id, limit)
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
