"""Microsoft Graph email tools (Outlook/Hotmail) — server-side only.

Token lives per-account خارج الـ repo (/opt/data/ms_token_<account_id>.json).
يوازي gmail_tools.py بالواجهة نفسها حتى ينسجم مع EmailProvider abstraction.
"""
import json, urllib.request, urllib.parse, os, time, datetime

GRAPH = "https://graph.microsoft.com/v1.0"
TOKEN_URI = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"


def _token(token_path):
    d = json.load(open(token_path))
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
            "grant_type": "refresh_token",
            "client_id": d["client_id"],
            "client_secret": d["client_secret"],
            "refresh_token": d["refresh_token"],
            "scope": " ".join(d.get("scopes", [])),
        }).encode()
        req = urllib.request.Request(TOKEN_URI, data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        nd = json.loads(urllib.request.urlopen(req, timeout=20).read())
        d["token"] = nd["access_token"]
        d["refresh_token"] = nd.get("refresh_token", d.get("refresh_token", ""))
        d["expiry"] = time.time() + nd.get("expires_in", 3600)
        json.dump(d, open(token_path, "w"))
    return d["token"]


def _graph(path, params=None, method="GET", body=None, token_path=None):
    token = _token(token_path)
    url = GRAPH + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Authorization": "Bearer " + token})
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        if not raw:
            return {}
        return json.loads(raw)


def _addr(m):
    f = m.get("from") or {}
    ea = (f.get("emailAddress") or {})
    return ea.get("address", ""), ea.get("name", "")


def summary(limit=10, q=None, token_path=None):
    top = min(limit, 20)
    if q:
        # بحث عبر $search (يتطلب Mail.Read) — نرجع نتائج تبدأ بكلمة البحث
        d = _graph("/me/messages", {"$top": top, "$search": f'"{q}"',
                                    "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead",
                                    "$orderby": "receivedDateTime desc"}, token_path=token_path)
    else:
        d = _graph("/me/mailFolders/inbox/messages", {"$top": top,
                    "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead",
                    "$orderby": "receivedDateTime desc"}, token_path=token_path)
    out = []
    for m in d.get("value", []):
        addr, name = _addr(m)
        out.append({
            "id": m["id"],
            "from": addr,
            "subject": m.get("subject", "(بدون موضوع)"),
            "date": m.get("receivedDateTime", ""),
            "snippet": m.get("bodyPreview", ""),
            "unread": not m.get("isRead", False),
        })
    return out


def search(q, limit=20, token_path=None):
    return summary(limit=limit, q=q, token_path=token_path)


def read_message(mid, token_path=None):
    m = _graph("/me/messages/" + mid, None, token_path=token_path)
    addr, name = _addr(m)
    body = (m.get("body") or {}).get("content", "")
    return {"id": mid, "from": addr, "subject": m.get("subject", ""),
            "date": m.get("receivedDateTime", ""), "body": body}


def message_headers(mid, token_path=None):
    m = _graph("/me/messages/" + mid, {"$select": "id,subject,from"}, token_path=token_path)
    addr, name = _addr(m)
    return {"from": addr, "subject": m.get("subject", "")}


def send(to, subject, body, token_path=None):
    """يرسل رسالة جديدة عبر sendMail ويعيد message id حقيقي من Sent Items."""
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    _graph("/me/sendMail", method="POST", body=payload, token_path=token_path)  # 202
    # نجلب id الرسالة المُرسلة فعلياً من مجلد المُرسَل
    d = _graph("/me/mailFolders/sentitems/messages",
               {"$top": 1, "$orderby": "sentDateTime desc", "$select": "id,sentDateTime,toRecipients"},
               token_path=token_path)
    for m in d.get("value", []):
        return {"id": m["id"]}
    return {"id": None}
