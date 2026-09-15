# JARVIS — Audit Event Schema

Events (structured, timestamped, JSONL):
- request_received {ts, event, session_id, text}
- route_selected {ts, event, session_id, agent, kind}
- tool_selected {ts, event, session_id, tool}
- approval_requested {ts, event, session_id, approval_id, agent, action}
- approval_result {ts, event, approval_id, result, reason}
- tool_completed {ts, event, session_id, tool, ok, error}
- response_produced {ts, event, session_id, kind}
- session_created {ts, event, session_id}

## Rules
- Never log long-lived secrets, raw mic audio, or excessive sensitive payloads.
- Risk class + approval requirement/result recorded for real actions.
