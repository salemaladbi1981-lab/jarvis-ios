"""Action-specific approval — full lifecycle (bind/expiry/param-change/reuse)."""
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

    DESTRUCTIVE_PATTERNS = ["unlock", "open", "disable", "delete", "format", "commit", "config", "install", "remove", "gate", "alarm"]

    def requires_approval(self, agent_id: str, action: str) -> bool:
        for a in self.registry.get("agents", []):
            if a["id"] == agent_id:
                policy = a.get("approval_policy", {})
                if action in policy.get("required_actions", []):
                    return True
                # unknown destructive action → deny-by-default
                if any(p in action for p in self.DESTRUCTIVE_PATTERNS):
                    return True
                return False
        return True  # unknown agent → deny-by-default

class ApprovalStore:
    """Binds approvals to exact action+params; expiry/reject/reuse enforced."""
    def __init__(self, ttl: int = 120):
        self.ttl = ttl
        self._pending = {}   # approval_id -> record
        self._consumed = set()

    def request(self, agent_id, action, params) -> str:
        aid = uuid.uuid4().hex
        self._pending[aid] = {
            "agent": agent_id, "action": action, "params": params,
            "expires": time.time() + self.ttl, "status": "pending",
        }
        return aid

    def resolve(self, approval_id, decision: bool, *, agent_id=None, action=None, params=None):
        p = self._pending.get(approval_id)
        if not p:
            return {"ok": False, "reason": "unknown_approval"}
        if approval_id in self._consumed:
            return {"ok": False, "reason": "reused_approval"}
        if time.time() > p["expires"]:
            p["status"] = "expired"
            return {"ok": False, "reason": "expired"}
        if not decision:
            p["status"] = "rejected"
            self._consumed.add(approval_id)
            return {"ok": True, "status": "rejected"}
        # approve: bind exact action + params
        if (agent_id is not None and (agent_id != p["agent"] or action != p["action"] or params != p["params"])):
            return {"ok": False, "reason": "parameter_mismatch"}
        p["status"] = "approved"
        self._consumed.add(approval_id)
        return {"ok": True, "status": "approved", "agent": p["agent"],
                "action": p["action"], "params": p["params"]}
