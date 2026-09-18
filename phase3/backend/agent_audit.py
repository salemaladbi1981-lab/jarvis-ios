"""Persistent agent audit trail (JSONL) — يُقرأ بعد التنفيذ."""
from __future__ import annotations
import json, os

AUDIT_PATH = os.environ.get("JARVIS_AGENT_AUDIT", "/opt/data/logs/jarvis-agent-audit.jsonl")


def append(rec: dict) -> None:
    os.makedirs(os.path.dirname(AUDIT_PATH), exist_ok=True)
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read(agent_id: str | None = None, limit: int = 50) -> list[dict]:
    out = []
    try:
        with open(AUDIT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if agent_id is None or r.get("agent_id") == agent_id:
                    out.append(r)
    except Exception:
        pass
    return out[-limit:]
