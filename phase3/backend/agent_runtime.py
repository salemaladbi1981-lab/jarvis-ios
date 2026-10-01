"""Registry-driven agent runtime for JARVIS."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).with_name("AGENT-REGISTRY.json")

TOOL_OWNERS = {
    "email_draft_reply": "core_writer",
    "email_send": "core_writer",
}
TOOL_PREFIX_OWNERS = (
    ("email_", "core_coordinator"),
    ("telegram_", "sys_circle"),
    ("youtube_", "core_producer"),
    ("instagram_", "ct_mkt"),
    ("maps_", "core_coordinator"),
)

class AgentRuntime:
    def __init__(self, registry_path: str | Path = REGISTRY_PATH):
        self.registry_path = Path(registry_path)
        with self.registry_path.open(encoding="utf-8") as f:
            self.registry = json.load(f)
        agents = self.registry.get("agents", [])
        ids = [a.get("id") for a in agents]
        if len(agents) != 21 or len(set(ids)) != 21 or None in ids:
            raise ValueError("agent_registry_must_contain_21_unique_ids")
        self._agents = {a["id"]: a for a in agents}

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(self._agents)

    def get(self, agent_id: str) -> dict[str, Any] | None:
        return self._agents.get(agent_id)

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(text.lower().replace("_", " ").replace("-", " ").split())

    def route(self, text: str) -> str:
        q = self._norm(text)
        if not q:
            return "core_coordinator"

        best_id = "core_coordinator"
        best_score = 0
        for agent_id, agent in self._agents.items():
            fields = [
                agent_id,
                agent.get("name", ""),
                agent.get("role", ""),
                *agent.get("capabilities", []),
                *agent.get("tools", []),
            ]
            score = 0
            for raw in fields:
                term = self._norm(str(raw))
                if not term:
                    continue
                if term in q:
                    score += 4
                    continue
                for token in term.split():
                    if len(token) >= 3 and token in q:
                        score += 1
            if score > best_score:
                best_id, best_score = agent_id, score
        return best_id if best_score else "core_coordinator"

    def agent_for_tool(self, tool_name: str, args: dict | None = None) -> str:
        if tool_name == "jarvis_agent":
            requested = (args or {}).get("agent_id")
            return requested if requested in self._agents else "core_coordinator"
        if tool_name in TOOL_OWNERS:
            return TOOL_OWNERS[tool_name]
        for prefix, agent_id in TOOL_PREFIX_OWNERS:
            if tool_name.startswith(prefix):
                return agent_id
        return "core_coordinator"

    def event_payload(self, phase: str, agent_id: str, **extra: Any) -> dict[str, Any]:
        if agent_id not in self._agents:
            raise ValueError(f"unknown_agent_id:{agent_id}")
        return {"type": "agent_runtime", "phase": phase, "agent_id": agent_id, **extra}
