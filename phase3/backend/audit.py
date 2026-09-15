"""Minimal audit log — records real actions, never long-lived secrets."""
import json, time, uuid, os

AUDIT_PATH = os.environ.get("JARVIS_AUDIT_PATH", "audit.jsonl")

def log(event: str, **fields):
    entry = {
        "ts": time.time(),
        "event": event,
        "session_id": fields.pop("session_id", None),
        "agent": fields.pop("agent", None),
        "tool": fields.pop("tool", None),
        "action": fields.pop("action", None),
        "risk": fields.pop("risk", None),
        "approval_required": fields.pop("approval_required", None),
        "approval_result": fields.pop("approval_result", None),
        "result": fields.pop("result", None),
        "error": fields.pop("error", None),
        **fields,
    }
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
