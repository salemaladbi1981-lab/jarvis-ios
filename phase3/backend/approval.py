"""Action-specific approval — binds to exact action + params + workspace + task, expires, one-time."""
import json, time, uuid, os

REGISTRY_PATH = os.environ.get("JARVIS_REGISTRY_PATH", "AGENT-REGISTRY.json")
APPROVAL_PATH = os.environ.get("JARVIS_APPROVAL_PATH", "/opt/data/logs/jarvis-approvals.json")

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
    """موافقات ملزمة: مرتبطة بـ workspace + task + action + params، تُستهلك مرة واحدة، تنتهي.

    تغيير المعاملات بعد الطلب يبطل الموافقة (parameter_mismatch).
    """
    def __init__(self):
        self._pending = self._load()

    def _load(self):
        try:
            with open(APPROVAL_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(APPROVAL_PATH), exist_ok=True)
        tmp = APPROVAL_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._pending, f, ensure_ascii=False)
        os.replace(tmp, APPROVAL_PATH)

    def request(self, agent_id, action, params, ttl=120, workspace_id=None, task_id=None) -> str:
        aid = uuid.uuid4().hex
        self._pending[aid] = {
            "agent": agent_id, "action": action, "params": params,
            "workspace_id": workspace_id, "task_id": task_id,
            "expires": time.time() + ttl, "status": "pending", "used": False,
        }
        self._save()
        return aid

    def resolve(self, approval_id, decision: bool, agent_id=None, action=None, params=None, workspace_id=None):
        p = self._pending.get(approval_id)
        if not p or time.time() > p["expires"]:
            return {"ok": False, "reason": "expired_or_unknown"}
        if p.get("used"):
            return {"ok": False, "reason": "already_used"}  # تُستهلك مرة واحدة
        if decision:
            if agent_id is not None and (agent_id != p["agent"] or action != p["action"] or params != p["params"]):
                return {"ok": False, "reason": "parameter_mismatch"}
            if workspace_id is not None and workspace_id != p.get("workspace_id"):
                return {"ok": False, "reason": "workspace_mismatch"}
        p["status"] = "approved" if decision else "rejected"
        p["used"] = True
        self._save()
        return {"ok": True, "status": p["status"]}

    def is_approved(self, approval_id, agent_id, action, params, workspace_id) -> bool:
        """يتحقق أن موافقة صالحة (غير مستهلكة، غير منتهية، مطابقة) تغطي الفعل الحالي."""
        p = self._pending.get(approval_id)
        if not p or time.time() > p["expires"] or p.get("used") or p.get("status") != "approved":
            return False
        return (p["agent"] == agent_id and p["action"] == action
                and p["params"] == params and p.get("workspace_id") == workspace_id)
