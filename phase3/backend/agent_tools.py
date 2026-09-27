"""jarvis_agent — أداة تشغيل وكيل متخصص عبر Hermes (execution trace كامل)."""
from __future__ import annotations
import json, re
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
            "capabilities or tools. Omit query to list all registered agents. "
            "Registration does not prove successful execution. Never answer agent-inventory questions from model memory."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "optional agent name, id, role, capability, or tool; omit for the full roster"}
        }, "required": []},
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


def _normalise_lookup(text):
    text = re.sub(r"[\u064b-\u065f\u0670]", "", str(text).lower())
    for source, target in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي")):
        text = text.replace(source, target)
    tokens = re.sub(r"[_\-?؟,،]", " ", text).split()
    return " ".join(t[2:] if t.startswith("ال") and len(t) > 3 else t for t in tokens)


def _agent_summary(agent):
    return {key: agent.get(key, [] if key in ("capabilities", "tools") else "")
            for key in ("id", "name", "group", "role", "capabilities", "tools")}


def execute_agent_tool(name, args):
    if name == "jarvis_agent_lookup":
        q = _normalise_lookup(args.get("query") or "")
        agents = _load_registry().get("agents", [])
        inventory_queries = {"", "all", "agents", "all agents", "list agents",
                             "وكلاء", "كل وكلاء", "قائمة وكلاء", "جميع وكلاء"}
        if q in inventory_queries:
            matches = [_agent_summary(agent) for agent in agents]
        else:
            matches = []
            for agent in agents:
                fields = [agent.get("id", ""), agent.get("name", ""), agent.get("role", ""),
                          *agent.get("capabilities", []), *agent.get("tools", [])]
                hay = _normalise_lookup(" ".join(str(field) for field in fields))
                agent_name = _normalise_lookup(agent.get("name", ""))
                if q in hay or (agent_name and agent_name in q) or any(
                        len(token) >= 2 and token in hay for token in q.split()):
                    matches.append(_agent_summary(agent))
        result = {"ok": True, "source": "AGENT-REGISTRY.json",
                  "execution_status": "not_checked", "total_registered": len(agents),
                  "count": len(matches), "matches": matches}
        if not matches:
            result["registered_agents"] = [
                {"id": agent.get("id"), "name": agent.get("name")} for agent in agents]
            result["note"] = ("No agent matched this query. The registry is not empty. "
                              "Use the registered names to clarify; do not say no agents exist.")
        return result

    if name != "jarvis_agent":
        return {"ok": False, "error": "unknown_tool"}
    agent_id = (args.get("agent_id") or "").strip()
    task = (args.get("task") or "").strip()
    requested_tools = args.get("requested_tools") or []
    requested_capabilities = args.get("requested_capabilities") or []
    return agent_runner.run_agent(agent_id, task, args,
                                  requested_tools=requested_tools,
                                  requested_capabilities=requested_capabilities)
