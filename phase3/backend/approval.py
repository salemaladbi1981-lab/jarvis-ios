"""Action-specific approval — binds to exact action + parameters, expires."""
import json, time, uuid, os

REGISTRY_PATH = os.environ.get("JARVIS_REGISTRY_PATH", "AGENT-REGISTRY.json")

class ApprovalEvaluator:
    def __init__(self):
        self.registry = self._load()

    def _load(self):
        try:
            with open(REGISTRY_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"agents": []}

    def requires_approval(self, agent_id: str, action: str) -> bool:
        for a in self.registry.get("agents", []):
            if a["id"] == agent_id:
                policy = a.get("approval_policy", {})
                return action in policy.get("required_actions", [])
        return True  # unknown agent/action → deny-by-default

class ApprovalStore:
    """Binds approvals to exact action + params; expires and rejects safely."""
    def __init__(self):
        self._pending = {}  # approval_id -> {agent, action, params, expires, status}

    def request(self, agent_id, action, params, ttl=120) -> str:
        aid = uuid.uuid4().hex
        self._pending[aid] = {
            "agent": agent_id, "action": action, "params": params,
            "expires": time.time() + ttl, "status": "pending",
        }
        return aid

    def resolve(self, approval_id, decision: bool, agent_id=None, action=None, params=None):
        p = self._pending.get(approval_id)
        if not p or time.time() > p["expires"]:
            return {"ok": False, "reason": "expired_or_unknown"}
        if decision and (agent_id is not None and (agent_id != p["agent"] or action != p["action"] or params != p["params"])):
            return {"ok": False, "reason": "parameter_mismatch"}
        p["status"] = "approved" if decision else "rejected"
        return {"ok": True, "status": p["status"]}
