"""Audit log — append-only + tamper-evident (hash chain) + workspace-scoped. لا أسرار ولا محتوى حساس."""
import json, time, uuid, os, hashlib

AUDIT_PATH = os.environ.get("JARVIS_AUDIT_PATH", "/opt/data/logs/jarvis-audit.jsonl")


def _last_hash() -> str:
    try:
        with open(AUDIT_PATH, encoding="utf-8") as f:
            last = None
            for line in f:
                line = line.strip()
                if line:
                    last = line
            if last:
                return json.loads(last).get("entry_hash", "")
    except Exception:
        pass
    return ""


def log(event: str, **fields):
    entry = {
        "ts": time.time(),
        "event": event,
        "session_id": fields.pop("session_id", None),
        "workspace_id": fields.pop("workspace_id", None),
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
    entry["prev_hash"] = _last_hash()
    entry["entry_hash"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    os.makedirs(os.path.dirname(AUDIT_PATH), exist_ok=True)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry["entry_hash"]


def verify() -> dict:
    """يتحقق من سلامة سلسلة الـ hash. يُرجع {ok, entries, broken_at}."""
    entries = []
    try:
        with open(AUDIT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        return {"ok": True, "entries": 0, "broken_at": None}
    prev = ""
    for i, e in enumerate(entries):
        if e.get("prev_hash") != prev:
            return {"ok": False, "entries": len(entries), "broken_at": i}
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        if hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest() != e.get("entry_hash"):
            return {"ok": False, "entries": len(entries), "broken_at": i}
        prev = e.get("entry_hash", "")
    return {"ok": True, "entries": len(entries), "broken_at": None}

# --- helpers (مستعادة من live — تحافظ على API الحالي) ---
def request_received(session_id, text): log("request_received", session_id=session_id, text=text[:200])
def route_selected(session_id, agent, kind): log("route_selected", session_id=session_id, agent=agent, kind=kind)
def tool_selected(session_id, tool): log("tool_selected", session_id=session_id, tool=tool)
def approval_requested(session_id, approval_id, agent, action): log("approval_requested", session_id=session_id, approval_id=approval_id, agent=agent, action=action)
def approval_result(approval_id, result, reason=None): log("approval_result", approval_id=approval_id, result=result, reason=reason)
def tool_completed(session_id, tool, ok, error=None): log("tool_completed", session_id=session_id, tool=tool, ok=ok, error=error)
def response_produced(session_id, kind): log("response_produced", session_id=session_id, kind=kind)

