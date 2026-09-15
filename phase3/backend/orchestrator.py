"""Central Orchestrator: User → Orchestrator → specialist agent → tool → result."""
import json, os
from approval import ApprovalEvaluator

REGISTRY_PATH = os.environ.get("JARVIS_REGISTRY_PATH", "AGENT-REGISTRY.json")

# intent keywords → agent group (simple deterministic routing for M3.2)
ROUTING = {
    "home": ["unlock", "door", "lock", "light", "ac", "temperature", "curtain", "tv", "camera", "alarm"],
    "calendar": ["schedule", "calendar", "event", "appointment", "موعد", "جدول"],
    "media": ["music", "play", "song", "track"],
    "general": [],
}

class Orchestrator:
    def __init__(self, gateway, approval: ApprovalEvaluator):
        self.gateway = gateway
        self.approval = approval
        self.registry = self._load()

    def _load(self):
        try:
            with open(REGISTRY_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"agents": []}

    def agent(self, agent_id):
        for a in self.registry.get("agents", []):
            if a["id"] == agent_id:
                return a
        return None

    def route(self, text: str) -> str:
        t = text.lower()
        for agent_id, keywords in ROUTING.items():
            if any(k in t for k in keywords):
                return agent_id
        return "general"

    def handle(self, agent_id: str, action: str, params: dict, approval_store=None):
        agent = self.agent(agent_id)
        if not agent:
            return {"ok": False, "error": "capability_unavailable"}
        # approval check
        needs = self.approval.requires_approval(agent_id, action)
        if needs:
            if approval_store is None:
                return {"ok": False, "error": "approval_required", "approval": True}
            aid = approval_store.request(agent_id, action, params)
            return {"ok": False, "error": "approval_required", "approval_id": aid, "approval": True}
        # execute tool
        result = self.gateway.execute(action, params)
        return result
