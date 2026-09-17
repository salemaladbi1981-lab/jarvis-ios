"""OAuth flow لربط حساب Gmail إضافي — server-side only (لا token يُعرض للمستخدم).

الهدف: أسهل ربط ممكن للمالك — يفتح رابطاً واحداً، يوافق، يلصق الكود، وتتم البقية تلقائياً.
لا كلمة مرور Google، لا تعديل JSON يدوي، لا Terminal للمالك.
"""
import json, os, time, urllib.request, urllib.parse

CLIENT_SECRET_PATH = os.environ.get("GOOGLE_CLIENT_SECRET_PATH", "/opt/data/google_client_secret.json")
REGISTRY_PATH = os.environ.get("JARVIS_ACCOUNT_REGISTRY", "/opt/data/email_accounts.json")
REDIRECT_URI = "http://localhost"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _client():
    d = json.load(open(CLIENT_SECRET_PATH))
    return d.get("installed") or d.get("web") or {}


def build_auth_url(state=""):
    c = _client()
    params = {
        "client_id": c["client_id"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return c.get("auth_uri", "https://accounts.google.com/o/oauth2/auth") + "?" + urllib.parse.urlencode(params)


def exchange_code(code):
    """يستبدل كود التفويض بـ tokens (client_id + client_secret سيرفر فقط)."""
    c = _client()
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(c.get("token_uri", "https://oauth2.googleapis.com/token"),
                                 data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def _profile(access_token):
    req = urllib.request.Request("https://www.googleapis.com/gmail/v1/users/me/profile",
                                 headers={"Authorization": "Bearer " + access_token})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def complete(account_id, display_name, code):
    """يستبدل الكود، يتحقق من الحساب الحقيقي، يخزّن token، ويضيفه للـ registry."""
    tokens = exchange_code(code)
    email = _profile(tokens["access_token"])["emailAddress"]

    c = _client()
    token_path = f"/opt/data/google_token_{account_id}.json"
    token_doc = {
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_uri": c.get("token_uri", "https://oauth2.googleapis.com/token"),
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "scopes": SCOPES,
        "account": email,
        "expiry": time.time() + tokens.get("expires_in", 3600),
        "type": "authorized_user",
    }
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(token_doc, f, indent=2)
    os.chmod(token_path, 0o600)

    _add_to_registry(account_id, display_name, email, token_path)
    return {
        "account_id": account_id,
        "display_name": display_name,
        "email": email,
        "provider": "gmail",
        "scopes": SCOPES,
        "status": "connected",
    }


def _add_to_registry(account_id, display_name, email, token_path):
    reg = {"accounts": []}
    if os.path.exists(REGISTRY_PATH):
        reg = json.load(open(REGISTRY_PATH, encoding="utf-8"))
    # استبدال إذا وُجد نفس account_id
    reg["accounts"] = [a for a in reg.get("accounts", []) if a.get("account_id") != account_id]
    reg["accounts"].append({
        "account_id": account_id,
        "display_name": display_name,
        "provider": "gmail",
        "email": email,
        "token_path": token_path,
        "scopes": SCOPES,
    })
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
