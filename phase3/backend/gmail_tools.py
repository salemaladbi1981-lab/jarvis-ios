"""Gmail tools — server-side only. Token lives in /opt/data/google_token.json (never in repo)."""
import json, base64, urllib.request, urllib.parse, os, time, datetime
from email.mime.text import MIMEText

TOKEN_PATH = os.environ.get("GOOGLE_TOKEN_PATH", "/opt/data/google_token.json")


def _token():
    d = json.load(open(TOKEN_PATH))
    exp = d.get("expiry", 0)
    need_refresh = True
    if isinstance(exp, (int, float)):
        need_refresh = float(exp) < time.time() + 60
    elif isinstance(exp, str):
        try:
            ts = datetime.datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
            need_refresh = ts < time.time() + 60
        except Exception:
            need_refresh = True
    if need_refresh:
        body = urllib.parse.urlencode({
            "grant_type": "refresh_token", "client_id": d["client_id"],
            "client_secret": d["client_secret"], "refresh_token": d["refresh_token"],
        }).encode()
        req = urllib.request.Request(d.get("token_uri", "https://oauth2.googleapis.com/token"),
                                     data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        nd = json.loads(urllib.request.urlopen(req, timeout=20).read())
        d["token"] = nd["access_token"]
        d["expiry"] = time.time() + nd.get("expires_in", 3600)
        json.dump(d, open(TOKEN_PATH, "w"))
    return d["token"]


def _gmail(path, params=None, method="GET", body=None):
    token = _token()
    url = "https://www.googleapis.com/gmail/v1/users/me/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Authorization": "Bearer " + token})
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def summary(limit=10, q=None):
    q = q or "in:inbox newer_than:2d"
    d = _gmail("messages", {"maxResults": min(limit, 20), "q": q})
    out = []
    for m in d.get("messages", []):
        meta = _gmail("messages/" + m["id"], {"format": "metadata"})
        headers = {h["name"].lower(): h["value"] for h in meta.get("payload", {}).get("headers", [])}
        out.append({
            "id": m["id"],
            "from": headers.get("from", ""),
            "subject": headers.get("subject", "(بدون موضوع)"),
            "date": headers.get("date", ""),
            "snippet": meta.get("snippet", ""),
            "unread": "UNREAD" in meta.get("labelIds", []),
        })
    return out


def search(q, limit=20):
    return summary(limit=limit, q=q)


def read_message(mid):
    m = _gmail("messages/" + mid, {"format": "full"})
    payload = m.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    return {"id": mid, "from": headers.get("from", ""), "subject": headers.get("subject", ""),
            "date": headers.get("date", ""), "body": _extract_body(payload)}


def _extract_body(payload):
    def walk(p):
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            return p["body"]["data"]
        for part in p.get("parts", []):
            r = walk(part)
            if r:
                return r
        if p.get("body", {}).get("data"):
            return p["body"]["data"]
        return None
    data = walk(payload)
    if not data:
        return ""
    return base64.urlsafe_b64decode(data).decode("utf-8", "replace")


def send(to, subject, body):
    token = _token()
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    req = urllib.request.Request(
        "https://www.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def message_headers(mid):
    """خلفيات خفيفة (from/subject) لرسالة — لبناء draft الرد دون جلب الجسم كاملاً."""
    meta = _gmail("messages/" + mid, {"format": "metadata"})
    headers = {h["name"].lower(): h["value"] for h in meta.get("payload", {}).get("headers", [])}
    return {"from": headers.get("from", ""), "subject": headers.get("subject", "")}
