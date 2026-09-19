"""Unified conversation model — source-agnostic (app/telegram/future channels).

Conversation هو المرجع الأساسي للهوية المشتركة عبر كل الواجهات:
user_id + workspace_id + session_id + conversation_id + memory_namespace + refs.
"""
from __future__ import annotations
import time, uuid
import storage

CONVERSATION_PREFIX = "conv"
DEFAULT_SOURCE = "app"
VALID_SOURCES = ("app", "telegram", "web", "api")
REF_FIELDS = ("message_ids", "task_ids", "attachment_ids", "delivery_ids")


def new_conversation_id() -> str:
    return f"{CONVERSATION_PREFIX}-{uuid.uuid4().hex[:16]}"


def memory_namespace_for(user_id: str, workspace_id: str, conversation_id: str) -> str:
    """memory_namespace مربوط بالمستخدم + workspace + المحادثة — لا خلط بين المستخدمين/المساحات."""
    return f"jarvis:{user_id}:{workspace_id}:{conversation_id}"


class ConversationStore:
    def _load(self) -> dict:
        return storage.load_conversations()

    def _save(self, d: dict) -> None:
        storage.save_conversations(d)

    def create(self, user_id, workspace_id, source=DEFAULT_SOURCE, session_id=None, title=None) -> dict:
        storage.ensure_dirs()
        cid = new_conversation_id()
        now = time.time()
        conv = {
            "conversation_id": cid,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "source": source if source in VALID_SOURCES else DEFAULT_SOURCE,
            "session_id": session_id,
            "title": title or "",
            "memory_namespace": memory_namespace_for(user_id, workspace_id, cid),
            "created_at": now,
            "last_activity": now,
            "message_ids": [],
            "task_ids": [],
            "attachment_ids": [],
            "delivery_ids": [],
        }
        d = self._load()
        d[cid] = conv
        self._save(d)
        return conv

    def get_or_create(self, user_id, workspace_id, source=DEFAULT_SOURCE,
                      conversation_id=None, session_id=None, title=None):
        """استمرار محادثة قائمة: إذا ورد conversation_id صالح للمالك يُعاد استخدامه، لا توليد جديد."""
        if conversation_id:
            existing = self.get(conversation_id, user_id, workspace_id)
            if existing:
                if session_id and existing.get("session_id") != session_id:
                    existing["session_id"] = session_id
                    d = self._load()
                    d[existing["conversation_id"]] = existing
                    self._save(d)
                return existing, False
        conv = self.create(user_id, workspace_id, source, session_id, title)
        return conv, True

    def get(self, conversation_id, user_id=None, workspace_id=None):
        conv = self._load().get(conversation_id)
        if not conv:
            return None
        if user_id and conv.get("user_id") != user_id:
            return None
        if workspace_id is not None and conv.get("workspace_id") != workspace_id:
            return None
        return conv

    def list(self, user_id, workspace_id=None):
        out = [c for c in self._load().values() if c.get("user_id") == user_id]
        if workspace_id is not None:
            out = [c for c in out if c.get("workspace_id") == workspace_id]
        return sorted(out, key=lambda c: c.get("last_activity", 0), reverse=True)

    def touch(self, conversation_id):
        d = self._load()
        conv = d.get(conversation_id)
        if not conv:
            return None
        conv["last_activity"] = time.time()
        d[conversation_id] = conv
        self._save(d)
        return conv

    def add_ref(self, conversation_id, field, ref_id):
        """يربط message/task/attachment/delivery بالمحادثة (بدون تكرار)."""
        if field not in REF_FIELDS:
            return {"ok": False, "error": "bad_ref_field"}
        d = self._load()
        conv = d.get(conversation_id)
        if not conv:
            return {"ok": False, "error": "not_found"}
        if ref_id not in conv.get(field, []):
            conv.setdefault(field, []).append(ref_id)
        conv["last_activity"] = time.time()
        d[conversation_id] = conv
        self._save(d)
        return {"ok": True, "conversation": conv}
