"""M3.2/M3.3 automated tests — orchestrator, approval, tools, security."""
import os, sys, time, json, re
from approval import ApprovalEvaluator, ApprovalStore
from tools import Tool, ToolGateway
import safe_tools
from orchestrator import Orchestrator

PASS = 0
FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

gateway = ToolGateway()
gateway.register(Tool("read-temperature","قراءة الحرارة",["core_home"],"read temp",{} ,{}, "low","none"), safe_tools.read_temperature)
gateway.register(Tool("read-light-state","قراءة الإضاءة",["core_home"],"read light",{} ,{}, "low","none"), safe_tools.read_light_state)
gateway.register(Tool("get-service-health","صحة الخدمات",["sys_server"],"health",{} ,{}, "low","none"), safe_tools.get_service_health)
gateway.register(Tool("capability-status","حالة القدرات",["sys_server"],"caps",{} ,{}, "low","none"), safe_tools.capability_status)
def unlock(params): return {"state":"unlocked","mock":True}
gateway.register(Tool("unlock-door","فتح الباب",["core_home"],"unlock",{} ,{}, "high","action-specific"), unlock)

evaluator = ApprovalEvaluator()
store = ApprovalStore()
orch = Orchestrator(gateway, evaluator)

print("== ORCHESTRATOR ROUTING ==")
# A. direct response
r = orch.handle("كيف حالك يا جارفس؟", "s1", approval_store=store)
check("A direct response (no tool)", r.get("ok") and r.get("kind") == "direct_answer")
# B. safe read
r = orch.handle("وش درجة الحرارة؟", "s2", approval_store=store)
check("B safe read routes to read-temperature (no approval)", r.get("ok") and r.get("tool") == "read-temperature" and not r.get("approval"))
# C. sensitive → approval
r = orch.handle("افتح الباب", "s3", approval_store=store)
check("C unlock-door requires approval (blocked)", not r.get("ok") and r.get("approval") and r.get("tool") == "unlock-door")
# D. content routing
r = orch.handle("جهز لي سكريبت فيديو", "s4", approval_store=store)
check("D content request routes to content agent (no home tool)", r.get("agent") in ("ct_director",) or r.get("kind") in ("direct_answer","content_request"))
# E. unavailable capability
r = orch.handle("سوّي لي شي مو موجود", "s5", approval_store=store)
check("E unavailable capability handled", r.get("ok") is False or r.get("kind") == "direct_answer")
# F. ambiguity → conservative
r = orch.handle("شغّل", "s6", approval_store=store)
check("F ambiguous → no destructive guess", not (r.get("tool") in ("unlock-door",)))

print("\n== APPROVAL END-TO-END ==")
# 1. safe bypass
check("1 read-temperature no approval", not evaluator.requires_approval("core_home","read-temperature"))
# 2. sensitive
check("2 unlock-door approval required", evaluator.requires_approval("core_home","unlock-door"))
# 3. blocked before approval (gateway refuses high risk without bypass)
r = gateway.execute("unlock-door", {"door":"front"})
check("3 unlock-door blocked before approval", not r.get("ok") and r.get("error")=="approval_required")
# 4. reject → not executed
aid = store.request("core_home","unlock-door",{"door":"front"})
res = store.resolve(aid, False)
check("4 reject → not executed", res.get("status")=="rejected")
# 5. approve → exact params only
aid = store.request("core_home","unlock-door",{"door":"front"})
res = store.resolve(aid, True, agent_id="core_home", action="unlock-door", params={"door":"front"})
check("5 approve exact params", res.get("status")=="approved")
# 6. param change after approval
aid = store.request("core_home","unlock-door",{"door":"front"})
res = store.resolve(aid, True, agent_id="core_home", action="unlock-door", params={"door":"back"})
check("6 modified params → invalid", not res.get("ok") and res.get("reason")=="parameter_mismatch")
# 7. expired
aid = store.request("core_home","unlock-door",{"door":"front"})
store._pending[aid]["expires"] = time.time() - 10
res = store.resolve(aid, True)
check("7 expired → denied", not res.get("ok") and res.get("reason")=="expired")
# 8. reuse/replay
aid = store.request("core_home","unlock-door",{"door":"front"})
store.resolve(aid, True, agent_id="core_home", action="unlock-door", params={"door":"front"})
res = store.resolve(aid, True, agent_id="core_home", action="unlock-door", params={"door":"front"})
check("8 reuse approval → denied", not res.get("ok") and res.get("reason")=="reused_approval")
# 9. unknown destructive → deny
check("9 unknown action → deny", evaluator.requires_approval("core_home","format-drive"))
# 10/11/12 policies
check("10 financial-commitment approval", evaluator.requires_approval("core_dealmaker","financial-commitment"))
check("11 disable-camera approval", evaluator.requires_approval("core_guardian","disable-camera"))
check("12 destructive-config approval", evaluator.requires_approval("sys_server","destructive-config"))

print("\n== TOOLS ==")
check("unavailable tool → error", gateway.execute("nonexistent", {}) == {"ok":False,"error":"tool_unavailable","mock":True})
check("safe tool returns structured result", gateway.execute("read-temperature", {})["ok"] is True)
check("safe tool marked mock", gateway.execute("read-temperature", {}).get("mock") is True)

print("\n== SECURITY ==")
# privileged tool cannot bypass approval via gateway
check("privileged tool cannot bypass approval", gateway.execute("unlock-door", {}).get("error")=="approval_required")
# secrets absent from repo (scan source files)
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
secret_hit = False
for root,_,files in os.walk(repo_root):
    for f in files:
        if f.endswith(('.py','.swift','.json','.md')):
            try:
                txt = open(os.path.join(root,f), encoding='utf-8').read()
            except: continue
            if f == 'tests.py':
                continue
            if re.search(r'sk-[A-Za-z0-9]{20,}', txt):
                secret_hit = True
check("no provider secrets in repo source", not secret_hit)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
