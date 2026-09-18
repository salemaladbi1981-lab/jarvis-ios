"""سجل تدقيق — metadata آمنة فقط. لا نص query ولا secrets ولا محتوى ذاكرة حساس."""
from __future__ import annotations
import json, os, time, hashlib

AUDIT_PATH = os.environ.get("JARVIS_AUDIT_PATH", "/opt/data/logs/jarvis-memory-audit.jsonl")


def _s(v):
    return v if v is not None else ""


def log(event: str, identity: dict, query: str | None = None, query_type: str | None = None) -> None:
    """event + metadata. query يُحوَّل إلى hash فقط (لا يُسجَّل النص)."""
    rec = {
        "ts": time.time(),
        "event": event,
        "user_id": _s(identity.get("user_id")),
        "session_id": _s(identity.get("session_id")),
        "conversation_id": _s(identity.get("conversation_id")),
        "memory_namespace": _s(identity.get("memory_namespace")),
        "query_type": query_type,
    }
    if query is not None:
        rec["query_hash"] = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
    try:
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
