"""YouTube OAuth — ربط حساب Google/YouTube الحقيقي (channel + personalization).

Desktop-app flow (loopback) بنفس Google client المستخدم للـ Gmail.
token في /opt/data/youtube_token.json (خارج الـ repo). لا token يُعرض للمالك.
"""
import json, os, time, urllib.request, urllib.parse

CLIENT_SECRET_PATH = os.environ.get("GOOGLE_CLIENT_SECRET_PATH", "/opt/data/google_client_secret.json")
YT_TOKEN_PATH = os.environ.get("YT_TOKEN_PATH", "/opt/data/youtube_token.json")
REDIRECT_URI = "http://localhost"

YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
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
        "scope": " ".join(YT_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return c.get("auth_uri", "https://accounts.google.com/o/oauth2/auth") + "?" + urllib.parse.urlencode(params)


def exchange_code(code):
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


def _token():
    """يعيد access token لليوتيوب (مع refresh)."""
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


def complete(code):
    """يستبدل الكود، يتحقق من الحساب، ويخزّن token."""
    c = _client()
    tokens = exchange_code(code)
    # verify: profile
    req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo",
                                 headers={"Authorization": "Bearer " + tokens["access_token"]})
    prof = json.loads(urllib.request.urlopen(req, timeout=25).read())
    email = prof.get("email", "")
    doc = {
        "token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_uri": c.get("token_uri", "https://oauth2.googleapis.com/token"),
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
