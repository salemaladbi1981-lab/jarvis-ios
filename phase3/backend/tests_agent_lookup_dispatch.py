"""Exercise the actual voice dispatcher and registry lookup without provider calls."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import types

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
# Specialist execution is a stub; this test verifies routing, not agent health.
sys.modules["agent_profiles"] = types.ModuleType("agent_profiles")
runner = types.ModuleType("agent_runner")
runner.run_agent = lambda agent_id, task, identity, **kwargs: {
    "ok": True, "agent_id": agent_id, "test_execution_stub": True}
sys.modules["agent_runner"] = runner
spec = importlib.util.spec_from_file_location("agent_tools_under_test", ROOT / "agent_tools.py")
agent_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_tools)

tree = ast.parse((ROOT / "realtime.py").read_text())
dispatch = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "dispatch_tool")
scope = [node for node in tree.body if isinstance(node, ast.FunctionDef)
         and node.name == "scoped_tool_arguments"]
namespace = {
    "AGENT_TOOLS": agent_tools.AGENT_TOOLS,
    "execute_agent_tool": agent_tools.execute_agent_tool,
    "pending_email": {}, "pending_tg": {},
    "trusted_identity": {key: "diagnostic" for key in (
        "user_id", "workspace_id", "session_id", "conversation_id", "memory_namespace")},
    "execute_email_tool": lambda *args: {"ok": False, "error": "unknown_tool"},
}
exec(compile(ast.Module(body=scope + [dispatch], type_ignores=[]),
             str(ROOT / "realtime.py"), "exec"), namespace)
invoke = namespace["dispatch_tool"]
total = len(json.loads((ROOT / "AGENT-REGISTRY.json").read_text())["agents"])
checks = 0

for query in ("معمار", "المعمار", "sys_architect"):
    result = invoke("jarvis_agent_lookup", {"query": query})
    assert result.get("ok"), ("lookup dispatch failed", query, result)
    assert "sys_architect" in [agent["id"] for agent in result["matches"]], result
    checks += 1
for args in ({}, {"query": ""}, {"query": "كل الوكلاء"}, {"query": "all agents"}):
    result = invoke("jarvis_agent_lookup", args)
    assert result["ok"] and result["count"] == total, result
    assert result["total_registered"] == total, result
    assert result["execution_status"] == "not_checked", result
    checks += 1
result = invoke("jarvis_agent_lookup", {"query": "zznonexistentagentzz"})
assert result["count"] == 0 and result["total_registered"] == total, result
assert len(result["registered_agents"]) == total, result
checks += 1
result = invoke("jarvis_agent", {"agent_id": "sys_architect", "task": "routing test"})
assert result["test_execution_stub"] and result["agent_id"] == "sys_architect", result
checks += 1
assert invoke("unregistered_tool", {})["error"] == "unknown_tool"
checks += 1
lookup = next(tool for tool in agent_tools.AGENT_TOOLS if tool["name"] == "jarvis_agent_lookup")
assert lookup["parameters"]["required"] == []
checks += 1
print(f"PASS {checks}/{checks}: voice dispatcher + registered roster; execution health not tested")
