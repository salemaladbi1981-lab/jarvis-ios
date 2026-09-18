"""Identity + session/conversation management for JARVIS requests.

user_id = salem-aladbi (المالك الأساسي). كل طلب يحمل:
  user_id, session_id, conversation_id, memory_namespace.
"""
from __future__ import annotations
import uuid

DEFAULT_USER_ID = "salem-aladbi"
MEMORY_NAMESPACE_PREFIX = "jarvis"

class Identity:
    """هوية طلب قادم من JARVIS App."""
    def __init__(self, user_id: str, session_id: str, conversation_id: str,
                 memory_namespace: str | None = None):
        self.user_id = user_id or DEFAULT_USER_ID
        self.session_id = session_id or new_session_id()
        self.conversation_id = conversation_id or new_conversation_id(self.user_id)
        self.memory_namespace = memory_namespace or f"{MEMORY_NAMESPACE_PREFIX}:{self.user_id}:{self.conversation_id}"

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "memory_namespace": self.memory_namespace,
        }

    def to_headers(self) -> dict:
        """headers لإرسالها إلى Hermes API (استمرارية الجلسة + نطاق الذاكرة)."""
        return {
            "X-Hermes-Session-Id": self.session_id,
            "X-Hermes-Session-Key": self.memory_namespace,
        }


def new_session_id() -> str:
    return uuid.uuid4().hex[:16]


def new_conversation_id(user_id: str) -> str:
    return f"{user_id}-{uuid.uuid4().hex[:12]}"


def from_args(args: dict) -> Identity:
    """يبني هوية من معاملات function call (مع قيم افتراضية آمنة)."""
    return Identity(
        user_id=args.get("user_id", "") or DEFAULT_USER_ID,
        session_id=args.get("session_id", "") or "",
        conversation_id=args.get("conversation_id", "") or "",
        memory_namespace=args.get("memory_namespace", "") or None,
    )
