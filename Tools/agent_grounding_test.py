"""Grounded agent inventory regression.
Agent existence/name/role questions must be answered from AGENT-REGISTRY.json, never model memory."""
import json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if cond: PASS += 1
    else: FAIL += 1

tools = open(os.path.join(ROOT, 'phase3/backend/agent_tools.py'), encoding='utf-8').read()
cfg = open(os.path.join(ROOT, 'phase3/backend/config.py'), encoding='utf-8').read()
with open(os.path.join(ROOT, 'phase3/backend/AGENT-REGISTRY.json'), encoding='utf-8') as f:
    reg = json.load(f)

check("jarvis_agent_lookup tool exists", '"name": "jarvis_agent_lookup"' in tools)
check("lookup reads authoritative registry", '_REGISTRY_PATH' in tools and 'AGENT-REGISTRY.json' in tools)
check("lookup returns grounded fields", all(k in tools for k in ['"id"', '"name"', '"group"', '"role"', '"capabilities"', '"tools"']))
check("realtime instructions require lookup for inventory questions", 'استخدم jarvis_agent_lookup حصراً' in cfg)

agents = {a["id"]: a for a in reg["agents"]}
check("sys_architect exists", agents.get("sys_architect", {}).get("name") == "معمار")
check("sys_coach exists", agents.get("sys_coach", {}).get("name") == "المدرب")

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
