"""سجل تدقيق بسيط — لا يُسجّل secrets ولا محتوى ذاكرة حساس."""
from __future__ import annotations
import json, os, time

AUDIT_PATH = os.environ.get("JARVIS_AUDIT_PATH", "/opt/data/logs/jarvis-memory-audit.jsonl")

def log(event: str, identity: dict, **extra) -> None:
    """event: recall_hit / recall_miss / brain_delegate — بدون محتوى حساس."""
    try:
        rec = {
            "ts": time.time(),
            "event": event,
            "user_id": identity.get("user_id", ""),
            "session_id": identity.get("session_id", ""),
            "conversation_id": identity.get("conversation_id", ""),
            "namespace": identity.get("memory_namespace", ""),
            **{k: v for k, v in extra.items()},
        }
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
