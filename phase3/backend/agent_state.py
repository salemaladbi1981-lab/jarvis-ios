"""Persistent agent verification state (JSON file) — يبقى بعد إعادة التشغيل."""
from __future__ import annotations
import json, os, time

STATE_PATH = os.environ.get("JARVIS_AGENT_STATE", "/opt/data/logs/jarvis-agent-state.json")


def _load() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"agents": {}}


def _save(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def mark_verified(agent_id: str, test_evidence: str, result_status: str, result_len: int) -> dict:
    state = _load()
    rec = {
        "execution_status": "verified",
        "last_tested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_evidence": test_evidence,
        "last_result": result_status,
        "result_len": result_len,
    }
    state["agents"][agent_id] = rec
    _save(state)
    return rec


def get_agent_state(agent_id: str) -> dict | None:
    return _load()["agents"].get(agent_id)
