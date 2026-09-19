"""Central Orchestrator: intent → agent → tool → approval → result → audit."""
import json, os
from approval import ApprovalEvaluator

REGISTRY_PATH = os.environ.get("JARVIS_REGISTRY_PATH", "AGENT-REGISTRY.json")

# keyword routing (deterministic; ambiguity handled conservatively)
ROUTES = [
    # (agent_id, keywords)
    ("core_home", ["درجة", "حرارة", "temperature", "إضاءة", "light", "باب", "door", "unlock", "lock", "قفل", "فتح", "كamera", "كاميرا", "alarm", "إنذار"]),
    ("ct_account", ["جدول", "موعد", "calendar", "schedule", "event", "اجتماع", "تذكير", "reminder", "اليوم", "today"]),
    ("ct_director", ["فيديو", "video", "ريل", "reel", "محتوى", "content", "سكريبت"]),
    ("sys_server", ["صحة", "health", "خدمة", "service", "status", "حالة النظام"]),
]

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
        for agent_id, kws in ROUTES:
            if any(k in t for k in kws):
                return agent_id
        return "general"  # direct answer, no tool

    def classify(self, text: str) -> str:
        """Classify the request kind for structured handling."""
        t = text.lower()
        if any(k in t for k in ["افتح", "unlock", "قفل", "open"]):
            return "sensitive_action"
        if any(k in t for k in ["درجة", "temperature", "إضاءة", "light", "صحة", "health", "status"]):
            return "safe_read"
        if any(k in t for k in ["تذكير", "reminder"]):
            return "reminders"
        if any(k in t for k in ["الجاي", "next", "بعد", "التالي"]):
            return "calendar_next"
        if any(k in t for k in ["اليوم", "today", "جدول", "calendar", "موعد"]):
            return "calendar_today"
        if any(k in t for k in ["فيديو", "video", "محتوى"]):
            return "content_request"
        return "direct"

    def handle(self, text: str, session_id: str, approval_store=None, audit=None):
        agent_id = self.route(text)
        kind = self.classify(text)
        if agent_id == "general":
            return {"ok": True, "agent": "general", "kind": "direct_answer",
                    "text": "أنا جارفس. كيف أقدر أساعدك؟"}
        agent = self.agent(agent_id)
        if agent is None:
            return {"ok": False, "error": "capability_unavailable", "agent": agent_id}
        # map to a concrete tool by kind
        tool_id = self._tool_for(kind, text)
        if tool_id is None:
            # direct conversational answer
            return {"ok": True, "agent": agent_id, "kind": "direct_answer",
                    "text": "أنا جارفس. كيف أقدر أساعدك؟"}

        contract = self.gateway.contract(tool_id)
        params = {"source": "demo"}

        # approval evaluation
        needs = self.approval.requires_approval(agent_id, tool_id)
        if needs:
            if approval_store is None:
                return {"ok": False, "error": "approval_required", "agent": agent_id,
                        "tool": tool_id, "approval": True}
            aid = approval_store.request(agent_id, tool_id, params)
            return {"ok": False, "error": "approval_required", "agent": agent_id,
                    "tool": tool_id, "approval_id": aid, "approval": True}

        result = self.gateway.execute(tool_id, params)
        result.update({"agent": agent_id, "tool": tool_id, "kind": kind})
        return result

    def _tool_for(self, kind, text):
        t = text.lower()
        if kind == "safe_read":
            if any(k in t for k in ["درجة", "temperature", "حرارة"]): return "read-temperature"
            if any(k in t for k in ["إضاءة", "light"]): return "read-light-state"
            if any(k in t for k in ["صحة", "health", "status", "خدمة"]): return "get-service-health"
            return "read-temperature"
        if kind == "sensitive_action":
            if any(k in t for k in ["باب", "door", "unlock", "فتح", "open"]): return "unlock-door"
            return "unlock-door"
        if kind == "calendar_today":
            return "calendar.today"
        if kind == "calendar_next":
            return "calendar.next_event"
        if kind == "reminders":
            return "reminders.upcoming"
        if kind == "content_request":
            return None  # content requests route to agent, no home tool
        return None
