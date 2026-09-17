"""Microsoft OAuth flow لربط حساب Outlook/Hotmail — server-side only (لا token يُعرض).

الربط: رابط واحد → المالك يسجّل الدخول → يوافق → redirect تلقائي للـ backend → ربط + تحقق.
لا كلمة مرور، لا Terminal، لا تعديل JSON، لا نسخ token يدوي.

يتطلب app registration (client_id + client_secret + redirect_uri) — تُقرأ من env:
  MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT (default: consumers), MS_REDIRECT_URI
"""
import json, os, time, urllib.request, urllib.parse

MS_TENANT = os.environ.get("MS_TENANT", "consumers")
MS_REDIRECT_URI = os.environ.get("MS_REDIRECT_URI", "https://jarvis-api.qeyas.app/ms/oauth/callback")
MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET", "")

REGISTRY_PATH = os.environ.get("JARVIS_ACCOUNT_REGISTRY", "/opt/data/email_accounts.json")

AUTH_URI = f"https://login.microsoftonline.com/{MS_TENANT}/oauth2/v2.0/authorize"
TOKEN_URI = f"https://login.microsoftonline.com/{MS_TENANT}/oauth2/v2.0/token"

SCOPES = ["offline_access", "Mail.ReadWrite", "Mail.Send", "User.Read"]


def _creds():
    if not MS_CLIENT_ID or not MS_CLIENT_SECRET:
        # fallback: ملف app registration (مثل google_client_secret.json)
        p = os.environ.get("MS_CLIENT_SECRET_PATH", "/opt/data/ms_client_secret.json")
        if os.path.exists(p):
            d = json.load(open(p))
            return d.get("client_id", ""), d.get("client_secret", ""), d.get("tenant", MS_TENANT)
    return MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT


def is_configured():
    cid, sec, _ = _creds()
    return bool(cid and sec)


def build_auth_url(state=""):
    cid, _, tenant = _creds()
    params = {
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": MS_REDIRECT_URI,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return AUTH_URI + "?" + urllib.parse.urlencode(params)


def exchange_code(code):
    cid, sec, _ = _creds()
    body = urllib.parse.urlencode({
        "client_id": cid,
        "client_secret": sec,
        "code": code,
        "redirect_uri": MS_REDIRECT_URI,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES),
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def _profile(access_token):
    req = urllib.request.Request("https://graph.microsoft.com/v1.0/me",
                                 headers={"Authorization": "Bearer " + access_token})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def complete(account_id, display_name, code):
    """يستبدل الكود، يتحقق من الحساب الحقيقي، يخزّن token، ويضيفه للـ registry."""
    cid, sec, _ = _creds()
    tokens = exchange_code(code)
    prof = _profile(tokens["access_token"])
    email = prof.get("mail") or prof.get("userPrincipalName") or ""

    token_path = f"/opt/data/ms_token_{account_id}.json"
    token_doc = {
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "client_id": cid,
        "client_secret": sec,
        "scopes": SCOPES,
        "account": email,
        "expiry": time.time() + tokens.get("expires_in", 3600),
        "type": "microsoft",
    }
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(token_doc, f, indent=2)
    os.chmod(token_path, 0o600)

    _add_to_registry(account_id, display_name, email, token_path)
    return {
        "account_id": account_id,
        "display_name": display_name,
        "email": email,
        "provider": "microsoft",
        "scopes": SCOPES,
        "status": "connected",
    }


def _add_to_registry(account_id, display_name, email, token_path):
    reg = {"accounts": []}
    if os.path.exists(REGISTRY_PATH):
        reg = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    reg["accounts"] = [a for a in reg.get("accounts", []) if a.get("account_id") != account_id]
    reg["accounts"].append({
        "account_id": account_id,
        "display_name": display_name,
        "provider": "microsoft",
        "email": email,
        "token_path": token_path,
        "scopes": SCOPES,
    })
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
