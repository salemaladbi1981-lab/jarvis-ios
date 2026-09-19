"""Structured audit trail. Never logs secrets or raw mic audio."""
import json, time, os

AUDIT_PATH = os.environ.get("JARVIS_AUDIT_PATH", "audit.jsonl")

def log(event: str, **fields):
    entry = {"ts": time.time(), "event": event}
    entry.update(fields)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def request_received(session_id, text): log("request_received", session_id=session_id, text=text[:200])
def route_selected(session_id, agent, kind): log("route_selected", session_id=session_id, agent=agent, kind=kind)
def tool_selected(session_id, tool): log("tool_selected", session_id=session_id, tool=tool)
def approval_requested(session_id, approval_id, agent, action): log("approval_requested", session_id=session_id, approval_id=approval_id, agent=agent, action=action)
def approval_result(approval_id, result, reason=None): log("approval_result", approval_id=approval_id, result=result, reason=reason)
def tool_completed(session_id, tool, ok, error=None): log("tool_completed", session_id=session_id, tool=tool, ok=ok, error=error)
def response_produced(session_id, kind): log("response_produced", session_id=session_id, kind=kind)
