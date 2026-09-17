"""YouTube OAuth — Web flow (بدون localhost): Google → Allow → HTTPS callback → token سيرفر.

يتطلب OAuth client نوع "Web application" بـ redirect URI:
  https://jarvis-api.qeyas.app/yt/oauth/callback
بيانات الـ client في /opt/data/yt_web_client.json (خارج الـ repo).
"""
import json, os, secrets, time, urllib.request, urllib.parse

YT_WEB_CLIENT_PATH = os.environ.get("YT_WEB_CLIENT_PATH", "/opt/data/yt_web_client.json")
YT_TOKEN_PATH = os.environ.get("YT_TOKEN_PATH", "/opt/data/youtube_token.json")
REDIRECT_URI = os.environ.get("YT_REDIRECT_URI", "https://jarvis-api.qeyas.app/yt/oauth/callback")

YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

YT_INPUT_CODE_PATH = "/opt/data/yt_web_code.json"


def _client():
    if not os.path.exists(YT_WEB_CLIENT_PATH):
        raise Exception("youtube_web_client_missing")
    return json.load(open(YT_WEB_CLIENT_PATH))


def is_configured():
    return os.path.exists(YT_WEB_CLIENT_PATH)


def build_auth_url(state=""):
    c = _client()
    params = {
        "client_id": c["client_id"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(YT_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


def exchange_code(code):
    c = _client()
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token",
                                 data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def complete(code):
    """يستبدل الكود، يتحقق من الحساب، ويخزّن token."""
    c = _client()
    tokens = exchange_code(code)
    req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo",
                                 headers={"Authorization": "Bearer " + tokens["access_token"]})
    prof = json.loads(urllib.request.urlopen(req, timeout=25).read())
    email = prof.get("email", "")
    doc = {
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "scopes": YT_SCOPES,
        "email": email,
        "expiry": time.time() + tokens.get("expires_in", 3600),
        "type": "authorized_user",
    }
    with open(YT_TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    os.chmod(YT_TOKEN_PATH, 0o600)
    return {"email": email, "scopes": YT_SCOPES}


def _token():
    if not os.path.exists(YT_TOKEN_PATH):
        return ""
    d = json.load(open(YT_TOKEN_PATH))
    exp = d.get("expiry", 0)
    if isinstance(exp, (int, float)) and exp > time.time() + 60:
        return d["token"]
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token", "client_id": d["client_id"],
        "client_secret": d["client_secret"], "refresh_token": d["refresh_token"],
    }).encode()
    req = urllib.request.Request(d.get("token_uri", "https://oauth2.googleapis.com/token"),
                                 data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    nd = json.loads(urllib.request.urlopen(req, timeout=20).read())
    d["token"] = nd["access_token"]
    d["expiry"] = time.time() + nd.get("expires_in", 3600)
    json.dump(d, open(YT_TOKEN_PATH, "w"))
    return d["token"]


# --- إدخال web client آمن ---
def generate_client_code(ttl=1800):
    code = secrets.token_urlsafe(24)
    with open(YT_INPUT_CODE_PATH, "w", encoding="utf-8") as f:
        json.dump({"code": code, "expires_at": time.time() + ttl}, f)
    os.chmod(YT_INPUT_CODE_PATH, 0o600)
    return code


def consume_client_code(code):
    if not os.path.exists(YT_INPUT_CODE_PATH):
        return False
    d = json.load(open(YT_INPUT_CODE_PATH))
    if not code or d.get("code") != code:
        return False
    if time.time() > d.get("expires_at", 0):
        return False
    json.dump({"code": "", "expires_at": 0}, open(YT_INPUT_CODE_PATH, "w"))
    return True


def store_web_client(client_id, client_secret):
    with open(YT_WEB_CLIENT_PATH, "w", encoding="utf-8") as f:
        json.dump({"client_id": client_id.strip(), "client_secret": client_secret.strip()}, f, indent=2)
    os.chmod(YT_WEB_CLIENT_PATH, 0o600)
