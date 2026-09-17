"""JARVIS trusted control plane — FastAPI."""
import uuid, json, os
from urllib.parse import parse_qs
from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

import config, audit
from approval import ApprovalEvaluator, ApprovalStore
from tools import Tool, ToolGateway
from orchestrator import Orchestrator
import realtime
import ms_oauth
import telegram_auth
import youtube_provider
import yt_oauth

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

@app.get("/ms/secret")
def ms_secret_form(code: str = "", account_id: str = "hotmail", name: str = "Hotmail"):
    """نموذج إدخال client_id + client_secret بشكل آمن (لا يمر عبر المحادثة)."""
    html = f"""<!doctype html><html dir="ltr"><head><meta charset="utf-8">
<title>JARVIS — Microsoft App Credentials</title></head><body style="font-family:sans-serif;max-width:520px;margin:40px auto">
<h3>JARVIS — Microsoft App Credentials</h3>
<p>ألصق بيانات الـ App Registration هنا. تُخزَّن سيرفراً فقط ولا تظهر لأي أحد.</p>
<form method="POST" action="/ms/secret">
<input type="hidden" name="code" value="{code}">
<input type="hidden" name="account_id" value="{account_id}">
<input type="hidden" name="name" value="{name}">
<p>Application (client) ID:<br><input name="client_id" size="52" required></p>
<p>Client Secret (Value):<br><input name="client_secret" type="password" size="52" required></p>
<button type="submit">حفظ وبدء الربط</button>
</form></body></html>"""
    return HTMLResponse(html)

@app.post("/ms/secret")
async def ms_secret_post(request: Request):
    """يحفظ السرّ ثم يحوّلك مباشرة لشاشة موافقة Microsoft."""
    data = parse_qs((await request.body()).decode())
    code = (data.get("code") or [""])[0]
    account_id = (data.get("account_id") or ["hotmail"])[0]
    name = (data.get("name") or ["Hotmail"])[0]
    client_id = (data.get("client_id") or [""])[0].strip()
    client_secret = (data.get("client_secret") or [""])[0].strip()
    if not ms_oauth.consume_code(code):
        return HTMLResponse("<h3>Invalid or expired code</h3><p>اطلب رابط إدخال جديداً.</p>")
    if not client_id or not client_secret:
        return HTMLResponse("<h3>Missing client_id / client_secret</h3>")
    ms_oauth.store_credentials(client_id, client_secret)
    url = ms_oauth.build_auth_url(f"{account_id}:{name}")
    return RedirectResponse(url, status_code=302)

@app.get("/tg/setup")
def tg_setup_form(code: str = ""):
    """نموذج إدخال API ID/Hash + رقم الهاتف لربط حساب تيليقرام الشخصي."""
    html = f"""<!doctype html><html dir="ltr"><head><meta charset="utf-8"><title>JARVIS — Telegram Setup</title></head>
<body style="font-family:sans-serif;max-width:520px;margin:40px auto">
<h3>JARVIS — Telegram Personal Account</h3>
<p>بيانات من <b>my.telegram.org</b> → API development tools.</p>
<form method="POST" action="/tg/setup">
<input type="hidden" name="code" value="{code}">
<p>API ID:<br><input name="api_id" size="52" required></p>
<p>API Hash:<br><input name="api_hash" size="52" required></p>
<p>رقم الهاتف (بصيغة دولية +):<br><input name="phone" size="52" placeholder="+974..." required></p>
<button type="submit">إرسال كود التحقق</button>
</form></body></html>"""
    return HTMLResponse(html)

@app.post("/tg/setup")
async def tg_setup_post(request: Request):
    data = parse_qs((await request.body()).decode())
    code = (data.get("code") or [""])[0]
    api_id = (data.get("api_id") or [""])[0].strip()
    api_hash = (data.get("api_hash") or [""])[0].strip()
    phone = (data.get("phone") or [""])[0].strip()
    if not telegram_auth.consume_setup_code(code):
        return HTMLResponse("<h3>Invalid or expired code</h3>")
    if not api_id or not api_hash or not phone:
        return HTMLResponse("<h3>Missing fields</h3>")
    telegram_auth.store_credentials(api_id, api_hash)
    try:
        await telegram_auth.start_login_async(phone)
    except Exception as e:
        return HTMLResponse(f"<h3>Failed to send OTP</h3><pre>{e}</pre>")
    html = f"""<!doctype html><html dir="ltr"><head><meta charset="utf-8"><title>JARVIS — OTP</title></head>
<body style="font-family:sans-serif;max-width:520px;margin:40px auto">
<h3>كود التحقق أُرسل إلى هاتفك</h3>
<form method="POST" action="/tg/verify">
<input type="hidden" name="phone" value="{phone}">
<p>أدخل الكود:<br><input name="otp" size="52" required></p>
<p>كلمة مرور التحقق بخطوتين (2FA) إن كانت مفعّلة:<br><input name="password" type="password" size="52"></p>
<button type="submit">تسجيل الدخول</button>
</form></body></html>"""
    return HTMLResponse(html)

@app.post("/tg/verify")
async def tg_verify_post(request: Request):
    data = parse_qs((await request.body()).decode())
    phone = (data.get("phone") or [""])[0].strip()
    otp = (data.get("otp") or [""])[0].strip()
    password = (data.get("password") or [""])[0].strip() or None
    if not phone or not otp:
        return HTMLResponse("<h3>Missing phone/otp</h3>")
    try:
        me = await telegram_auth.complete_login_async(phone, otp, password=password)
        return HTMLResponse("<h3>✓ Connected</h3><pre>" + json.dumps(me, indent=2, ensure_ascii=False) + "</pre>")
    except Exception as e:
        return HTMLResponse(f"<h3>Sign in failed</h3><pre>{e}</pre>")

@app.get("/yt/key")
def yt_key_form(code: str = ""):
    """نموذج إدخال YouTube Data API Key بشكل آمن."""
    html = f"""<!doctype html><html dir="ltr"><head><meta charset="utf-8"><title>JARVIS — YouTube API Key</title></head>
<body style="font-family:sans-serif;max-width:520px;margin:40px auto">
<h3>JARVIS — YouTube Data API Key</h3>
<p>ألصق مفتاح الـ API هنا. يُخزَّن سيرفراً فقط ولا يظهر لأي أحد.</p>
<form method="POST" action="/yt/key">
<input type="hidden" name="code" value="{code}">
<p>API Key:<br><input name="api_key" type="password" size="52" required></p>
<button type="submit">حفظ</button>
</form></body></html>"""
    return HTMLResponse(html)

@app.post("/yt/key")
async def yt_key_post(request: Request):
    data = parse_qs((await request.body()).decode())
    code = (data.get("code") or [""])[0]
    api_key = (data.get("api_key") or [""])[0].strip()
    if not youtube_provider.consume_key_code(code):
        return HTMLResponse("<h3>Invalid or expired code</h3>")
    if not api_key:
        return HTMLResponse("<h3>Missing API key</h3>")
    youtube_provider.store_api_key(api_key)
    return HTMLResponse("<h3>✓ Stored</h3><p>YouTube search + details جاهزان.</p>")

@app.get("/yt/oauth")
def yt_oauth_client_form(code: str = ""):
    """نموذج إدخال OAuth Web Client (client_id + secret) — مرة واحدة."""
    html = f"""<!doctype html><html dir="ltr"><head><meta charset="utf-8"><title>JARVIS — YouTube OAuth Client</title></head>
<body style="font-family:sans-serif;max-width:520px;margin:40px auto">
<h3>JARVIS — YouTube OAuth Web Client</h3>
<p>ألصق بيانات الـ OAuth Client (نوع Web application). تُخزَّن سيرفراً فقط.</p>
<form method="POST" action="/yt/oauth">
<input type="hidden" name="code" value="{code}">
<p>Client ID:<br><input name="client_id" size="52" required></p>
<p>Client Secret:<br><input name="client_secret" type="password" size="52" required></p>
<button type="submit">حفظ</button>
</form></body></html>"""
    return HTMLResponse(html)

@app.post("/yt/oauth")
async def yt_oauth_client_post(request: Request):
    data = parse_qs((await request.body()).decode())
    code = (data.get("code") or [""])[0]
    client_id = (data.get("client_id") or [""])[0].strip()
    client_secret = (data.get("client_secret") or [""])[0].strip()
    if not yt_oauth.consume_client_code(code):
        return HTMLResponse("<h3>Invalid or expired code</h3>")
    if not client_id or not client_secret:
        return HTMLResponse("<h3>Missing client_id/secret</h3>")
    yt_oauth.store_web_client(client_id, client_secret)
    return HTMLResponse("<h3>✓ Stored</h3><p>الآن اطلب رابط التفويض.</p>")

@app.get("/yt/oauth/callback")
def yt_oauth_callback(code: str = "", state: str = "", error: str = ""):
    """Redirect تلقائي بعد موافقة Google — يربط حساب YouTube."""
    if error:
        return HTMLResponse(f"<h3>Authorization cancelled</h3><p>{error}</p>")
    if not code:
        return HTMLResponse("<h3>Missing code</h3>")
    try:
        result = yt_oauth.complete(code)
        return HTMLResponse("<h3>✓ Connected</h3><pre>" + json.dumps(result, indent=2, ensure_ascii=False) + "</pre>")
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
