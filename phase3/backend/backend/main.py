"""JARVIS trusted control plane — FastAPI (M3.2/M3.3)."""
import uuid
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config, audit
from approval import ApprovalEvaluator, ApprovalStore
from tools import Tool, ToolGateway
import safe_tools
from orchestrator import Orchestrator
import realtime

app = FastAPI(title="JARVIS Control Plane")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

approval_eval = ApprovalEvaluator()
approval_store = ApprovalStore()
gateway = ToolGateway()
orchestrator = Orchestrator(gateway, approval_eval)

# register safe tools (low risk, read-only)
gateway.register(Tool("read-temperature", "قراءة الحرارة", ["core_home"],
    "read room temperature", {"type":"object","properties":{}}, {"type":"object"},
    "low", "none"), safe_tools.read_temperature)
gateway.register(Tool("read-light-state", "قراءة الإضاءة", ["core_home"],
    "read light state", {"type":"object","properties":{"device":{"type":"string"}}},
    {"type":"object"}, "low", "none"), safe_tools.read_light_state)
gateway.register(Tool("get-service-health", "صحة الخدمات", ["sys_server"],
    "read service health", {"type":"object","properties":{}}, {"type":"object"},
    "low", "none"), safe_tools.get_service_health)
gateway.register(Tool("capability-status", "حالة القدرات", ["sys_server"],
    "list available/unavailable capabilities", {"type":"object","properties":{}},
    {"type":"object"}, "low", "none"), safe_tools.capability_status)

# Calendar/Reminders read-only tools (mock in backend; EventKit runs client-side)
def cal_today(params): return {"events": [{"time":"09:00","title":"Marketing Meeting — 09:00"}], "mock": True}
def cal_next(params): return {"event": {"time":"11:30","title":"Project Review — 11:30"}, "mock": True}
def rem_upcoming(params): return {"reminders": [{"title":"Review document"}], "mock": True}
gateway.register(Tool("calendar.today", "أحداث اليوم", ["ct_account"],
    "read today's calendar events", {"type":"object","properties":{}}, {"type":"object"}, "low", "none"), cal_today)
gateway.register(Tool("calendar.next_event", "الموعد الجاي", ["ct_account"],
    "read next calendar event", {"type":"object","properties":{}}, {"type":"object"}, "low", "none"), cal_next)
gateway.register(Tool("reminders.upcoming", "التذكيرات القادمة", ["ct_account"],
    "read upcoming reminders", {"type":"object","properties":{}}, {"type":"object"}, "low", "none"), rem_upcoming)

# register a high-risk control tool (handler refuses without approval gate)
def unlock_door(params):
    return {"door": params.get("door", "front"), "state": "unlocked", "mock": True}
gateway.register(Tool("unlock-door", "فتح الباب", ["core_home"],
    "unlock a door (requires approval)", {"type":"object","properties":{"door":{"type":"string"}}},
    {"type":"object"}, "high", "action-specific"), unlock_door)

class OrchestrateReq(BaseModel):
    session_id: str
    text: str = ""

class ApproveReq(BaseModel):
    approval_id: str
    decision: bool
    agent_id: str = ""
    action: str = ""
    params: dict = {}

@app.get("/health")
def health():
    return {
        "ok": True,
        "provider": config.REALTIME_PROVIDER,
        "realtime": "available" if config.OPENAI_API_KEY else "unavailable",
    }

@app.post("/session")
def create_session():
    sid = uuid.uuid4().hex
    audit.log("session_created", session_id=sid)
    return {"session_id": sid}

@app.get("/tools")
def list_tools():
    return {"tools": gateway.all_contracts()}

@app.post("/orchestrate")
def orchestrate(req: OrchestrateReq):
    audit.request_received(req.session_id, req.text)
    result = orchestrator.handle(req.text, req.session_id, approval_store=approval_store)
    audit.route_selected(req.session_id, result.get("agent"), result.get("kind"))
    return result

@app.post("/approve")
def approve(req: ApproveReq):
    r = approval_store.resolve(req.approval_id, req.decision,
                               agent_id=req.agent_id or None, action=req.action or None, params=req.params or None)
    audit.approval_result(req.approval_id, r.get("status"), r.get("reason"))
    if not r["ok"]:
        raise HTTPException(403, r["reason"])
    # if approved, execute the exact bound tool
    if r.get("status") == "approved":
        exec_result = gateway.execute(r["action"], r["params"], bypass_approval=True)
        audit.tool_completed("approval", r["action"], exec_result.get("ok"), exec_result.get("error"))
        r["execution"] = exec_result
    return r

@app.websocket("/realtime")
async def realtime_ws(ws: WebSocket):
    await ws.accept()
    await realtime.openai_realtime_proxy(ws, {})
