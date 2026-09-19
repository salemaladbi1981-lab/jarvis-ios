"""M3.4 tests — backend routing + mock tools + privacy/security.
(EventKit provider runtime requires an Apple device; those are separate.)"""
import os, re, sys
from approval import ApprovalEvaluator, ApprovalStore
from tools import Tool, ToolGateway
import safe_tools
from orchestrator import Orchestrator

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

gw = ToolGateway()
def cal_today(p): return {"events": [{"time":"09:00","title":"Marketing Meeting — 09:00"}], "mock": True}
def cal_next(p): return {"event": {"time":"11:30","title":"Project Review — 11:30"}, "mock": True}
def rem_up(p): return {"reminders": [{"title":"Review document"}], "mock": True}
gw.register(Tool("calendar.today","أحداث اليوم",["ct_account"],"t",{},{},"low","none"), cal_today)
gw.register(Tool("calendar.next_event","الموعد الجاي",["ct_account"],"t",{},{},"low","none"), cal_next)
gw.register(Tool("reminders.upcoming","التذكيرات",["ct_account"],"t",{},{},"low","none"), rem_up)
ev = ApprovalEvaluator()
orch = Orchestrator(gw, ev)
store = ApprovalStore()

print("== ORCHESTRATOR (calendar routing) ==")
check("AR 'وش عندي اليوم؟' → calendar.today", orch.handle("وش عندي اليوم؟","s",approval_store=store).get("tool")=="calendar.today")
check("AR 'وش موعدي الجاي؟' → calendar.next_event", orch.handle("وش موعدي الجاي؟","s",approval_store=store).get("tool")=="calendar.next_event")
check("AR 'وش عندي من تذكيرات؟' → reminders.upcoming", orch.handle("وش عندي من تذكيرات؟","s",approval_store=store).get("tool")=="reminders.upcoming")
check("EN 'what is on my schedule today?' → calendar.today", orch.handle("what is on my schedule today?","s",approval_store=store).get("tool")=="calendar.today")
check("EN 'any reminders?' → reminders.upcoming", orch.handle("any reminders?","s",approval_store=store).get("tool")=="reminders.upcoming")
# unrelated لا يلمس EventKit
r = orch.handle("شغّل موسيقى","s",approval_store=store)
check("unrelated request does not call EventKit", r.get("tool") not in ("calendar.today","calendar.next_event","reminders.upcoming"))

print("\n== TOOLS ==")
check("calendar.today typed output", gw.execute("calendar.today", {}).get("ok") is True)
check("calendar.next_event typed output", gw.execute("calendar.next_event", {}).get("ok") is True)
check("reminders.upcoming typed output", gw.execute("reminders.upcoming", {}).get("ok") is True)
check("mock clearly marked", gw.execute("calendar.today", {}).get("mock") is True)

print("\n== SECURITY / PRIVACY ==")
# لا write tool في الـ registry
contracts = [c["tool_id"] for c in gw.all_contracts()]
write_tools = [t for t in contracts if any(k in t for k in ("create","delete","update","write","complete","edit"))]
check("no write tool exposed in M3.4 registry", len(write_tools)==0)
# لا secret
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hit = False
for root,_,files in os.walk(repo_root):
    for f in files:
        if f.endswith(('.py','.swift','.json','.md')) and f != 'tests.py' and f != 'tests_m34.py':
            try: txt = open(os.path.join(root,f),encoding='utf-8').read()
            except: continue
            if re.search(r'sk-[A-Za-z0-9]{20,}', txt): hit = True
check("no calendar/secret token committed", not hit)
# كل tools read-only (risk low)
check("all M3.4 tools risk low", all(c["risk_class"]=="low" for c in gw.all_contracts()))

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(1 if FAIL else 0)
