"""jarvis_agent — أداة تشغيل وكيل متخصص عبر Hermes (execution trace كامل)."""
from __future__ import annotations
import json
from pathlib import Path
import agent_profiles, agent_runner

_REGISTRY_PATH = Path(__file__).with_name("AGENT-REGISTRY.json")

def _load_registry():
    with _REGISTRY_PATH.open(encoding="utf-8") as f:
        return json.load(f)

AGENT_TOOLS = [
    {
        "type": "function",
        "name": "jarvis_agent_lookup",
        "description": (
            "Grounded lookup against the authoritative JARVIS agent registry. "
            "Use this for questions about whether an agent exists, its exact name/id, role, group, "
            "capabilities or tools. Never answer agent-inventory questions from model memory."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "agent name, id, role, capability, or tool"}
        }, "required": ["query"]},
    },
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
    if name == "jarvis_agent_lookup":
        q = " ".join((args.get("query") or "").lower().replace("_", " ").replace("-", " ").split())
        agents = _load_registry().get("agents", [])
        if not q:
            # A lookup without a query used to fail closed (observed twice on hermes-new:
            # jarvis_agent_lookup ok=False, and JARVIS told the owner it had no details).
            # The roster is not sensitive and is the useful answer to "who do I have?".
            return {
                "ok": True,
                "count": len(agents),
                "query": "",
                "matches": [
                    {
                        "id": a.get("id"),
                        "name": a.get("name"),
                        "group": a.get("group"),
                        "role": a.get("role"),
                    }
                    for a in agents[:25]
                ],
            }
        matches = []
        for agent in agents:
            hay = " ".join([
                str(agent.get("id", "")),
                str(agent.get("name", "")),
                str(agent.get("role", "")),
                " ".join(agent.get("capabilities", [])),
                " ".join(agent.get("tools", [])),
            ]).lower().replace("_", " ").replace("-", " ")
            if q in hay or any(tok and tok in hay for tok in q.split()):
                matches.append({
                    "id": agent.get("id"),
                    "name": agent.get("name"),
                    "group": agent.get("group"),
                    "role": agent.get("role"),
                    "capabilities": agent.get("capabilities", []),
                    "tools": agent.get("tools", []),
                })
        return {"ok": True, "count": len(matches), "matches": matches[:10]}

    if name != "jarvis_agent":
        return {"ok": False, "error": "unknown_tool"}
    agent_id = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    requested_tools = args.get("requested_tools") or []
    requested_capabilities = args.get("requested_capabilities") or []
    return agent_runner.run_agent(agent_id, task, args,
                                  requested_tools=requested_tools,
                                  requested_capabilities=requested_capabilities)
