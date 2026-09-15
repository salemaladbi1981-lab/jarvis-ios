"""Typed Tool Gateway — every tool: id, schema, risk, approval, timeout, retry."""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

@dataclass
class Tool:
    id: str
    name: str
    owners: list[str]
    description: str
    input_schema: dict
    output_schema: dict
    risk: str              # low | medium | high
    approval_rule: str     # none | always | action-specific
    timeout_s: float = 10.0
    retries: int = 1
    idempotent: bool = True
    audit_category: str = "tool"

class ToolGateway:
    def __init__(self, registry_path="AGENT-REGISTRY.json"):
        self.tools: dict[str, Tool] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, tool: Tool, handler: Callable):
        self.tools[tool.id] = tool
        self._handlers[tool.id] = handler

    def schema(self, tool_id) -> dict:
        t = self.tools.get(tool_id)
        return {"id": t.id, "name": t.name, "input": t.input_schema,
                "output": t.output_schema, "risk": t.risk, "approval": t.approval_rule} if t else {}

    def execute(self, tool_id, params) -> dict:
        t = self.tools.get(tool_id)
        if not t:
            return {"ok": False, "error": "tool_unavailable"}
        if t.risk == "high" and t.approval_rule != "none":
            return {"ok": False, "error": "approval_required", "approval_rule": t.approval_rule}
        try:
            result = self._handlers[tool_id](params)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}
