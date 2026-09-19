"""JARVIS trusted control plane — FastAPI."""
import uuid, json, os
from urllib.parse import parse_qs
from fastapi import FastAPI, WebSocket, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

import config, audit
from approval import ApprovalEvaluator, ApprovalStore
from tools import Tool, ToolGateway
from orchestrator import Orchestrator
import realtime
import capabilities
import files_api
import tasks as tasks_mod
import deliveries
import auth
import workspace
import kill_switch
import conversation, messages
import tg_inbound, deeplink
import worker
import chat
import ms_oauth
import telegram_auth
import youtube_provider
import yt_oauth

app = FastAPI(title="JARVIS Control Plane")

@app.middleware("http")
async def no_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

approval_eval = ApprovalEvaluator()
approval_store = ApprovalStore()
gateway = ToolGateway()
orchestrator = Orchestrator(gateway, approval_eval)


def get_user_id(x_jarvis_session: str = Header(default="")):
    """هوية server-side من session موثّق — لا نثق بـ user_id من العميل."""
    uid = auth.resolve_user(x_jarvis_session)
    if not uid:
        raise HTTPException(status_code=401, detail="unauthorized")
    return uid


def get_workspace(x_jarvis_session: str = Header(default=""), x_jarvis_workspace: str = Header(default="")):
    """مساحة العمل server-side من session موثّق + المساحة المصرحة. لا قيمة افتراضية تمنح وصولًا."""
    session = auth.resolve_session(x_jarvis_session)
    if not session:
        raise HTTPException(status_code=401, detail="unauthorized")
    ws = workspace.authorize(session["workspace_id"], x_jarvis_workspace or None)
    if ws is None:
        raise HTTPException(status_code=403, detail="workspace_denied")
    return ws


def get_session(x_jarvis_session: str = Header(default="")):
    """session كامل {user_id, workspace_id, conversation_id} + الـtoken للربط."""
    s = auth.resolve_session(x_jarvis_session)
    if not s:
        raise HTTPException(status_code=401, detail="unauthorized")
    s["_token"] = x_jarvis_session
    return s


class BootstrapReq(BaseModel):
    proof: str


@app.post("/auth/bootstrap")
def auth_bootstrap(req: BootstrapReq):
    """App authentication/bootstrap: السيرفر يتحقق من سرّ enrollment ويصدر session token.

    العميل لا يختار user_id — الهوية يحددها السيرفر (المستخدم الأساسي).
    """
    token = auth.bootstrap(req.proof)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"session_token": token}


class EnrollReq(BaseModel):
    code: str


@app.post("/auth/enroll")
def auth_enroll(req: EnrollReq):
    """Secure pairing: يستبدل رمز enrollment (مرة واحدة، قصير الصلاحية) بـ session_token.

    الرمز يولّده السيرفر ويُسلَّم للمالك out-of-band (ليس داخل التطبيق).
    """
    token = auth.redeem_enrollment(req.code)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"session_token": token}


@app.post("/auth/enroll/code")
def auth_enroll_code(user_id: str = Depends(get_user_id)):
    """يولّد رمز pairing جديد لجهاز آخر — يتطلب session موثّقًا (المالك فقط)."""
    code = auth.create_enrollment_code()
    return {"enrollment_code": code, "expires_in": 600}

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


@app.get("/capabilities")
def list_capabilities():
    """قائمة القدرات المنظمة (بدل raw skills)."""
    return capabilities.list_capabilities(summary=True)


@app.get("/capabilities/overlaps")
def list_overlaps():
    return capabilities.overlap_groups()


@app.get("/capabilities/{capability_id}")
def get_capability(capability_id: str):
    c = capabilities.get_capability(capability_id)
    if not c:
        raise HTTPException(status_code=404, detail="unknown_capability")
    return c

# ================= FILES / TASKS / DELIVERIES (Phase D) =================

class UploadInitReq(BaseModel):
    filename: str
    mime_type: str = ""
    size: int
    checksum: str = ""
    conversation_id: str = ""
    session_id: str = ""

class UploadCompleteReq(BaseModel):
    upload_id: str

class TaskReq(BaseModel):
    session_id: str = ""
    conversation_id: str = ""
    prompt: str
    attachment_ids: list = []
    selected_agent: str = None
    selected_capability: str = None

class DeliveryReq(BaseModel):
    task_id: str
    filename: str
    type: str
    content: str = None

@app.post("/files/upload/init")
def upload_init(req: UploadInitReq, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    return files_api.init_upload(user_id, req.filename, req.mime_type, req.size,
                                 req.checksum, req.conversation_id, req.session_id, workspace_id)

@app.post("/files/upload/part")
async def upload_part(upload_id: str, part_number: int, checksum: str = "", request: Request = None, user_id: str = Depends(get_user_id)):
    data = await request.body()
    return files_api.upload_part(upload_id, part_number, data, checksum, user_id)

@app.get("/files/upload/{upload_id}/status")
def upload_status(upload_id: str, user_id: str = Depends(get_user_id)):
    return files_api.upload_status(upload_id, user_id)

@app.post("/files/upload/complete")
def upload_complete(req: UploadCompleteReq, user_id: str = Depends(get_user_id)):
    return files_api.complete_upload(req.upload_id, user_id)

@app.get("/files")
def list_files(user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    return files_api.list_files(user_id, workspace_id)

@app.get("/files/{file_id}")
def get_file(file_id: str, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    f = files_api.get_file(file_id, user_id, workspace_id)
    if not f:
        raise HTTPException(status_code=404, detail="not_found")
    return f

@app.get("/files/{file_id}/download")
def download_file(file_id: str, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    f = files_api.get_file(file_id, user_id, workspace_id)
    if not f or not os.path.exists(f.get("storage_ref", "")):
        raise HTTPException(status_code=404, detail="not_found")
    return FileResponse(f["storage_ref"], filename=f["filename"])

@app.delete("/files/{file_id}")
def delete_file(file_id: str, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    return files_api.delete_file(file_id, user_id, workspace_id)

@app.post("/tasks")
def create_task(req: TaskReq, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    if kill_switch.engaged():
        raise HTTPException(status_code=503, detail="kill_switch_engaged")
    t = tasks_mod.create_task(user_id, req.session_id, req.conversation_id, req.prompt,
                              req.attachment_ids, req.selected_agent, req.selected_capability, workspace_id)
    worker.enqueue(t["task_id"])
    return t

def _with_job_state(t):
    if isinstance(t, dict):
        j = worker.job_state_for(t.get("task_id"))
        if j:
            t["job_state"] = j["state"]
            t["attempts"] = j.get("attempts")
            t["last_error"] = j.get("last_error")
    return t

@app.get("/tasks")
def list_tasks(user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    return [_with_job_state(t) for t in tasks_mod.list_tasks(user_id, workspace_id)]

@app.get("/tasks/{task_id}")
def get_task(task_id: str, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    t = tasks_mod.get_task(task_id, user_id, workspace_id)
    if not t:
        raise HTTPException(status_code=404, detail="not_found")
    return _with_job_state(t)

@app.get("/deliveries")
def list_deliveries(user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    return deliveries.list_deliveries(user_id, workspace_id)

@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: str, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    d = deliveries.get_delivery(delivery_id, user_id, workspace_id)
    if not d:
        raise HTTPException(status_code=404, detail="not_found")
    return d

@app.get("/deliveries/{delivery_id}/download")
def download_delivery(delivery_id: str, user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    d = deliveries.get_delivery(delivery_id, user_id, workspace_id)
    if not d or not os.path.exists(d.get("storage_ref", "")):
        raise HTTPException(status_code=404, detail="not_found")
    return FileResponse(d["storage_ref"], filename=d["filename"])

@app.get("/inbox")
def get_inbox(user_id: str = Depends(get_user_id), workspace_id: str = Depends(get_workspace)):
    """Inbox موحّد: موافقات معلّقة + مهام فاشلة/مكتملة + تسليمات جاهزة."""
    items = []
    # 1) موافقات معلّقة → action required
    for a in approval_store.list_pending(workspace_id):
        items.append({"type": "approval", "title": (a.get("action") or "إجراء") + " — " + (a.get("agent") or ""),
                      "approval_id": a["approval_id"], "task_id": a.get("task_id"),
                      "conversation_id": None, "delivery_id": None, "ts": a.get("expires")})
    # 2) مهام (job_state من الـworker)
    for t in tasks_mod.list_tasks(user_id, workspace_id):
        js = worker.job_state_for(t.get("task_id"))
        state = js["state"] if js else t.get("status")
        if state == "FAILED":
            items.append({"type": "task_failed", "title": t.get("prompt") or "مهمة",
                          "approval_id": None, "task_id": t["task_id"],
                          "conversation_id": t.get("conversation_id"), "delivery_id": None,
                          "ts": t.get("completed_at") or t.get("created_at")})
        elif state == "SUCCEEDED":
            items.append({"type": "task_completed", "title": t.get("prompt") or "مهمة",
                          "approval_id": None, "task_id": t["task_id"],
                          "conversation_id": t.get("conversation_id"), "delivery_id": None,
                          "ts": t.get("completed_at") or t.get("created_at")})
    # 3) تسليمات جاهزة
    for d in deliveries.list_deliveries(user_id, workspace_id):
        if d.get("status") == "ready":
            items.append({"type": "delivery", "title": d.get("filename") or "تسليم",
                          "approval_id": None, "task_id": d.get("task_id"),
                          "conversation_id": None, "delivery_id": d.get("delivery_id"),
                          "ts": d.get("created_at")})
    items.sort(key=lambda x: x.get("ts") or 0, reverse=True)
    return items


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
<p>Client ID (ينتهي بـ .apps.googleusercontent.com):<br><input name="client_id" size="52" placeholder="مثال: 123456789-xxxx.apps.googleusercontent.com" required></p>
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
    """Redirect تلقائي بعد موافقة Google — يعالج الـ code مرة واحدة فقط (idempotent)."""
    if error:
        return HTMLResponse(f"<h3>Authorization cancelled</h3><p>{error}</p>")
    if not code:
        return HTMLResponse("<h3>Missing code</h3>")
    if yt_oauth.is_processed(code):
        return HTMLResponse("<h3>Already processed</h3><p>هذا الكود عولج مسبقاً — لا إعادة exchange.</p>")
    try:
        result = yt_oauth.complete(code)
        yt_oauth.mark_processed(code)
        return RedirectResponse(f"/yt/oauth/done?email={result['email']}", status_code=302)
    except Exception as e:
        yt_oauth.mark_processed(code)
        return HTMLResponse(f"<h3>Link failed</h3><pre>{e}</pre>")

@app.get("/yt/oauth/done")
def yt_oauth_done(email: str = ""):
    """صفحة نجاح نظيفة (بدون code في الـ URL — آمنة للـ refresh)."""
    return HTMLResponse(f"<h3>✓ Connected</h3><p>{email}</p>")

@app.post("/session")
def create_session(req: SessionReq):
    sid = uuid.uuid4().hex
    audit.log("session_created", session_id=sid, client=req.client)
    return {"session_id": sid, "ttl": config.SESSION_TTL_SECONDS}


class ConversationReq(BaseModel):
    source: str = "app"
    conversation_id: str = ""
    session_id: str = ""
    title: str = ""

class MessageReq(BaseModel):
    role: str = "user"
    content: str = ""
    client_msg_id: str = ""
    citations: list = []
    tool_calls: list = []
    attachment_refs: list = []
    task_refs: list = []
    delivery_refs: list = []
    execution_state: dict = None

@app.post("/conversations")
def conversations_get_or_create(req: ConversationReq, session: dict = Depends(get_session)):
    """متابعة محادثة قائمة (لا توليد جديد) أو إنشاء جديدة — source-agnostic."""
    conv, created = conversation.ConversationStore().get_or_create(
        session["user_id"], session["workspace_id"],
        source=req.source, conversation_id=req.conversation_id or session.get("conversation_id"),
        session_id=req.session_id, title=req.title)
    # ربط session بالمحادثة لاستعادتها بعد reconnect/restart
    if session.get("_token"):
        auth.set_session_conversation(session["_token"], conv["conversation_id"])
    audit.log("conversation", session_id=session["_token"], conversation_id=conv["conversation_id"],
              event="created" if created else "resumed")
    return {"ok": True, "created": created, "conversation": conv}

@app.get("/conversations")
def conversations_list(session: dict = Depends(get_session)):
    return conversation.ConversationStore().list(session["user_id"], session["workspace_id"])

@app.get("/conversations/{conversation_id}")
def conversations_get(conversation_id: str, session: dict = Depends(get_session)):
    conv = conversation.ConversationStore().get(conversation_id, session["user_id"], session["workspace_id"])
    if not conv:
        raise HTTPException(status_code=404, detail="not_found")
    msgs = messages.MessageStore().list(conversation_id)
    return {"conversation": conv, "messages": msgs}

@app.post("/conversations/{conversation_id}/messages")
def messages_add(conversation_id: str, req: MessageReq, session: dict = Depends(get_session)):
    conv = conversation.ConversationStore().get(conversation_id, session["user_id"], session["workspace_id"])
    if not conv:
        raise HTTPException(status_code=404, detail="not_found")
    r = messages.MessageStore().add(
        conversation_id, req.role, req.content,
        user_id=session["user_id"], workspace_id=session["workspace_id"],
        citations=req.citations, tool_calls=req.tool_calls,
        attachment_refs=req.attachment_refs, task_refs=req.task_refs,
        delivery_refs=req.delivery_refs, execution_state=req.execution_state,
        client_msg_id=req.client_msg_id or None)
    if not r["ok"]:
        raise HTTPException(status_code=400, detail=r["error"])
    conversation.ConversationStore().add_ref(conversation_id, "message_ids", r["message"]["message_id"])
    conversation.ConversationStore().touch(conversation_id)
    return {"ok": True, "duplicate": r.get("duplicate", False), "message": r["message"]}


class DeeplinkReq(BaseModel):
    uri: str

class ChatReq(BaseModel):
    text: str
    attachments: list = []

@app.post("/conversations/{conversation_id}/chat")
def chat_stream(conversation_id: str, req: ChatReq, session: dict = Depends(get_session)):
    """Chat streaming (SSE) — نفس المحادثة، citations/tool_calls مثبّتة."""
    ident = {"user_id": session["user_id"], "workspace_id": session["workspace_id"]}
    def gen():
        for evt in chat.stream_chat(conversation_id, req.text, ident, attachments=req.attachments):
            yield chat._sse_frame(evt["event"], evt["data"])
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.post("/tg/webhook")
def tg_webhook(update: dict, x_telegram_bot_api_secret_token: str = Header(default="")):
    """Telegram inbound — سرّ webhook يُتحقق منه، وupdate_id يُخصم ضد replay."""
    r = tg_inbound.handle_update(x_telegram_bot_api_secret_token, update)
    if not r["ok"]:
        code = {"invalid_secret": 401, "unauthorized": 403, "rate_limited": 403}.get(r["error"], 400)
        raise HTTPException(status_code=code, detail=r["error"])
    return r

@app.post("/deeplink/resolve")
def deeplink_resolve(req: DeeplinkReq, session: dict = Depends(get_session)):
    """يحل deep-link مع التحقق من الملكية server-side (لا وصول لمستخدم آخر)."""
    target = deeplink.resolve_target(req.uri, session["user_id"], session["workspace_id"])
    if not target:
        raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True, "target": target}

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
