"""Message record — role/content/timestamps/citations/tool_calls/refs/state + idempotency."""
from __future__ import annotations
import time, uuid
import storage

MESSAGE_PREFIX = "msg"
VALID_ROLES = ("user", "assistant", "tool", "system")


def new_message_id() -> str:
    return f"{MESSAGE_PREFIX}-{uuid.uuid4().hex[:16]}"


class MessageStore:
    def _load(self) -> dict:
        return storage.load_messages()

    def _save(self, d: dict) -> None:
        storage.save_messages(d)

    def add(self, conversation_id, role, content, *, user_id=None, workspace_id=None,
            citations=None, tool_calls=None, attachment_refs=None, task_refs=None,
            delivery_refs=None, execution_state=None, client_msg_id=None) -> dict:
        if role not in VALID_ROLES:
            return {"ok": False, "error": "bad_role"}
        # idempotency: نفس client_msg_id في نفس المحادثة → لا تكرار (webhook/retry-safe)
        if client_msg_id:
            for m in self._load().values():
                if m.get("conversation_id") == conversation_id and m.get("client_msg_id") == client_msg_id:
                    return {"ok": True, "message": m, "duplicate": True}
        mid = new_message_id()
        msg = {
            "message_id": mid,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "role": role,
            "content": content,
            "citations": citations or [],
            "tool_calls": tool_calls or [],
            "attachment_refs": attachment_refs or [],
            "task_refs": task_refs or [],
            "delivery_refs": delivery_refs or [],
            "execution_state": execution_state,
            "client_msg_id": client_msg_id,
            "created_at": time.time(),
        }
        d = self._load()
        d[mid] = msg
        self._save(d)
        return {"ok": True, "message": msg, "duplicate": False}

    def get(self, message_id):
        return self._load().get(message_id)

    def list(self, conversation_id):
        out = [m for m in self._load().values() if m.get("conversation_id") == conversation_id]
        return sorted(out, key=lambda m: m.get("created_at", 0))

    def count(self, conversation_id) -> int:
        return sum(1 for m in self._load().values() if m.get("conversation_id") == conversation_id)
