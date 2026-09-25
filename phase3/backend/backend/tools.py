"""Typed Tool Gateway — full contract per tool, structured results only."""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
import time

@dataclass
class Tool:
    tool_id: str
    display_name: str
    owning_agent_ids: list[str]
    description: str
    input_schema: dict
    output_schema: dict
    risk_class: str          # low | medium | high
    approval_rule: str       # none | always | action-specific
    timeout_s: float = 10.0
    retry_policy: str = "none"   # none | once | bounded
    idempotent: bool = True
    cancellable: bool = True
    audit_category: str = "tool"

class ToolGateway:
    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, tool: Tool, handler: Callable):
        self.tools[tool.tool_id] = tool
        self._handlers[tool.tool_id] = handler

    def contract(self, tool_id) -> Optional[dict]:
        t = self.tools.get(tool_id)
        if not t:
            return None
        return {
            "tool_id": t.tool_id, "display_name": t.display_name,
            "owning_agent_ids": t.owning_agent_ids, "description": t.description,
            "input_schema": t.input_schema, "output_schema": t.output_schema,
            "risk_class": t.risk_class, "approval_rule": t.approval_rule,
            "timeout_s": t.timeout_s, "retry_policy": t.retry_policy,
            "idempotent": t.idempotent, "cancellable": t.cancellable,
            "audit_category": t.audit_category,
        }

    def all_contracts(self) -> list[dict]:
        return [self.contract(t) for t in self.tools]

    def execute(self, tool_id, params, *, bypass_approval: bool = False) -> dict:
        t = self.tools.get(tool_id)
        if not t:
            return {"ok": False, "error": "tool_unavailable", "mock": False}
        if t.risk_class in ("medium", "high") and not bypass_approval:
            # caller must have resolved approval; gateway enforces the gate
            return {"ok": False, "error": "approval_required", "approval_rule": t.approval_rule}
        try:
            result = self._handlers[tool_id](params)
            # A handler failure or fixture must never become production success.
            if result.get("ok") is False or result.get("mock", False):
                return {"ok": False, "error": result.get("error", "provider_unavailable"), "mock": False}
            return {"ok": True, "result": result, "mock": result.get("mock", False)}
        except Exception as e:
            return {"ok": False, "error": f"tool_error:{type(e).__name__}"}
