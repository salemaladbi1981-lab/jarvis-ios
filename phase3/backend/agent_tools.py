"""jarvis_agent — أداة تشغيل وكيل متخصص عبر Hermes (execution trace كامل)."""
from __future__ import annotations
import agent_profiles, agent_runner

AGENT_TOOLS = [
    {
        "type": "function",
        "name": "jarvis_agent",
        "description": (
            "Run one JARVIS specialist agent on a task. The agent executes with its own "
            "system_prompt, allowed capabilities, and memory scope; returns the result plus "
            "a full audit trail (started/finished). Use when a task needs a specialist role."
        ),
        "parameters": {"type": "object", "properties": {
            "agent_id": {"type": "string", "description": "one of the 21 agent ids (e.g. ct_scriptwriter, core_writer)"},
            "task": {"type": "string", "description": "the task to run"},
            "requested_tools": {"type": "array", "items": {"type": "string"}, "description": "tools the agent may use (enforced against allowlist)"},
            "requested_capabilities": {"type": "array", "items": {"type": "string"}, "description": "capabilities the agent may use (enforced against allowlist)"},
            "user_id": {"type": "string"},
            "session_id": {"type": "string"},
            "conversation_id": {"type": "string"},
            "memory_namespace": {"type": "string"},
        }, "required": ["agent_id", "task"]},
    },
]


def execute_agent_tool(name, args):
    if name != "jarvis_agent":
        return {"ok": False, "error": "unknown_tool"}
    agent_id = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    requested_tools = args.get("requested_tools") or []
    requested_capabilities = args.get("requested_capabilities") or []
    return agent_runner.run_agent(agent_id, task, args,
                                  requested_tools=requested_tools,
                                  requested_capabilities=requested_capabilities)
