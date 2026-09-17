"""JARVIS trusted control plane — FastAPI."""
import uuid, json, os
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import config, audit
from approval import ApprovalEvaluator, ApprovalStore
from tools import Tool, ToolGateway
from orchestrator import Orchestrator
import realtime
import ms_oauth

app = FastAPI(title="JARVIS Control Plane")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

approval_eval = ApprovalEvaluator()
approval_store = ApprovalStore()
gateway = ToolGateway()
orchestrator = Orchestrator(gateway, approval_eval)

# --- demo safe tools (read-only) ---
def read_temperature(params): return {"reading": "22°", "unit": "celsius"}
def read_light_state(params): return {"device": params.get("device", "all"), "level": "35%"}
def get_today_events(params): return {"events": [{"time": "09:00", "title": "موعد"}]}

gateway.register(Tool("read-temperature", "read-temperature", ["core_home"], "read room temperature",
                      {"type": "object", "properties": {}}, {"type": "object"}, "low", "none"), read_temperature)
gateway.register(Tool("read-light-state", "read-light-state", ["core_home"], "read light state",
                      {"type": "object", "properties": {"device": {"type": "string"}}}, {"type": "object"}, "low", "none"), read_light_state)
gateway.register(Tool("get-today-events", "get-today-events", ["ct_account"], "read today's calendar events",
                      {"type": "object", "properties": {}}, {"type": "object"}, "low", "none"), get_today_events)

class SessionReq(BaseModel):
    client: str = "unknown"
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
    return {"ok": True, "provider": config.REALTIME_PROVIDER}

@app.get("/ms/oauth/callback")
def ms_oauth_callback(code: str = "", state: str = "", error: str = ""):
    """Redirect تلقائي بعد موافقة المالك — يربط حساب Microsoft ويحقق منه."""
    if error:
        return HTMLResponse(f"<h3>Authorization cancelled</h3><p>{error}</p>")
    if not code:
        return HTMLResponse("<h3>Missing code</h3>")
    try:
        parts = state.split(":", 1)
        account_id = parts[0] if parts and parts[0] else "microsoft"
        display_name = parts[1] if len(parts) > 1 else account_id
        result = ms_oauth.complete(account_id, display_name, code)
        body = "<h3>✓ Linked</h3><pre>" + json.dumps(result, indent=2, ensure_ascii=False) + "</pre>"
        return HTMLResponse(body)
    except Exception as e:
        return HTMLResponse(f"<h3>Link failed</h3><pre>{e}</pre>")

@app.post("/session")
def create_session(req: SessionReq):
    sid = uuid.uuid4().hex
    audit.log("session_created", session_id=sid, client=req.client)
    return {"session_id": sid, "ttl": config.SESSION_TTL_SECONDS}

@app.post("/orchestrate")
def orchestrate(req: OrchestrateReq):
    agent_id = orchestrator.route(req.text)
    # for M3.2 demo: treat any text as a direct-answer route unless keywords match a tool
    if agent_id == "general":
        audit.log("orchestrate", session_id=req.session_id, agent="general", result="direct_answer")
        return {"ok": True, "agent": "general", "kind": "direct_answer",
                "text": "أنا جارفس. كيف أقدر أساعدك؟"}
    audit.log("orchestrate", session_id=req.session_id, agent=agent_id)
    return {"ok": True, "agent": agent_id, "kind": "routed"}

@app.post("/approve")
def approve(req: ApproveReq):
    r = approval_store.resolve(req.approval_id, req.decision, req.agent_id, req.action, req.params)
    audit.log("approval", approval_id=req.approval_id, approval_result=r.get("status"), error=r.get("reason"))
    if not r["ok"]:
        raise HTTPException(403, r["reason"])
    return r

@app.websocket("/realtime")
async def realtime_ws(ws: WebSocket):
    await ws.accept()
    await realtime.openai_realtime_proxy(ws, {})
