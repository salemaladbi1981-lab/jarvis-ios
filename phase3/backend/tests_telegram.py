"""Telegram tools — deterministic tests (grounded contract + confirmation gate)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from telegram_tools import TELEGRAM_TOOLS, execute_telegram_tool

PASS = FAIL = 0
def check(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")


class FakeTG:
    def __init__(self):
        self.sent = []
        self.fail = False
    def summary(self, limit=10):
        if self.fail: raise Exception("tg_down")
        return [{"chat_id": "111", "title": "Salem", "preview": "hi", "unread": 2, "last_message_id": "5"}]
    def search(self, q, limit=20):
        return [{"chat_id": "111", "message_id": "5", "text": "hello"}]
    def read_message(self, chat_id, message_id):
        if chat_id == "111" and message_id == "5":
            return {"chat_id": "111", "message_id": "5", "text": "hello there"}
        return None
    def message_headers(self, chat_id, message_id):
        return {"title": "Salem"}
    def send(self, chat_id, text):
        if self.fail: raise Exception("send_down")
        sid = "m" + str(len(self.sent) + 1)
        self.sent.append({"chat_id": chat_id, "text": text})
        return {"id": sid, "chat_id": chat_id}


# A) الأدوات الخمس
names = [t["name"] for t in TELEGRAM_TOOLS]
for n in ["telegram_summary", "telegram_search", "telegram_read", "telegram_draft_reply", "telegram_send"]:
    check(f"tool defined: {n}", n in names)

# B) send يتطلب confirmed + read يتطلب chat_id/message_id
send_tool = [t for t in TELEGRAM_TOOLS if t["name"] == "telegram_send"][0]
check("telegram_send requires 'confirmed'", "confirmed" in send_tool["parameters"]["required"])
read_tool = [t for t in TELEGRAM_TOOLS if t["name"] == "telegram_read"][0]
check("telegram_read requires chat_id", "chat_id" in read_tool["parameters"]["required"])
check("telegram_read requires message_id", "message_id" in read_tool["parameters"]["required"])

prov = FakeTG()

# C) send بدون تأكيد → confirmation_required
r = execute_telegram_tool("telegram_send", {"confirmed": False}, {}, prov)
check("send without confirmation → confirmation_required", r.get("ok") is False and r.get("error") == "confirmation_required")

# D) send بدون مسودة → no_pending_draft
r = execute_telegram_tool("telegram_send", {"confirmed": True}, {}, prov)
check("send with no pending → no_pending_draft", r.get("ok") is False and r.get("error") == "no_pending_draft")

# E) draft يخزّن pending (لا إرسال)
p = {}
r = execute_telegram_tool("telegram_draft_reply", {"chat_id": "111", "text": "ردي"}, p, prov)
check("draft_reply stores chat_id", p.get("draft", {}).get("chat_id") == "111")
check("draft_reply returns draft (no send)", r.get("ok") is True and "draft" in r)

# F) read رسالة
r = execute_telegram_tool("telegram_read", {"chat_id": "111", "message_id": "5"}, {}, prov)
check("read returns message text", r.get("ok") and r["message"]["text"] == "hello there")

# G) success → sent_message_id + مسح pending
p = {"draft": {"chat_id": "111", "text": "ok"}}
r = execute_telegram_tool("telegram_send", {"confirmed": True}, p, prov)
check("success → sent_message_id حقيقي", r.get("ok") and r.get("sent_message_id") == "m1")
check("success → pending cleared", "draft" not in p)

# H) provider failure → لا success
prov.fail = True
p = {"draft": {"chat_id": "111", "text": "ok"}}
r = execute_telegram_tool("telegram_send", {"confirmed": True}, p, prov)
check("provider failure → no success", r.get("ok") is False)
check("provider failure → pending NOT cleared", "draft" in p)
prov.fail = False

# I) أداة مجهولة
r = execute_telegram_tool("not_a_tool", {}, {}, prov)
check("unknown tool → unknown_tool", r.get("ok") is False and r.get("error") == "unknown_tool")

# J) realtime.py wiring (telegram مسجلة + separate pending)
rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "realtime.py"), encoding="utf-8").read()
check("realtime.py registers telegram tools", "TELEGRAM_TOOLS" in rt)
check("realtime.py routes telegram_* calls", 'name.startswith("telegram_")' in rt)
check("realtime.py separate pending (email + tg)", "pending_tg" in rt and "pending_email" in rt)

# K) _creds يقرأ من الملف (مصدر معتمد) + env fallback
import telegram_provider, tempfile, json as _json
_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
_tmp.write(_json.dumps({"api_id": "12345", "api_hash": "abc"}).encode())
_tmp.close()
_old_path = telegram_provider.TG_CRED_PATH
_old_id = telegram_provider.TG_API_ID
_old_hash = telegram_provider.TG_API_HASH
telegram_provider.TG_CRED_PATH = _tmp.name
telegram_provider.TG_API_ID = 0
telegram_provider.TG_API_HASH = ""
_cid, _chash = telegram_provider._creds()
check("_creds reads from file (primary)", _cid == 12345 and _chash == "abc")
os.unlink(_tmp.name)
telegram_provider.TG_CRED_PATH = _old_path
telegram_provider.TG_API_ID = _old_id
telegram_provider.TG_API_HASH = _old_hash

# L) _peer_chat_id — آمن لأنواع peer الثلاثة (PeerUser / PeerChannel / PeerChat)
from telegram_provider import _peer_chat_id
class _PeerUser: user_id = 111
class _PeerChannel: channel_id = 222
class _PeerChat: chat_id = 333
check("PeerUser → user_id", _peer_chat_id(_PeerUser()) == 111)
check("PeerChannel → channel_id", _peer_chat_id(_PeerChannel()) == 222)
check("PeerChat → chat_id", _peer_chat_id(_PeerChat()) == 333)
# peer بدون أي id → None (لا crash)
class _PeerEmpty: pass
check("empty peer → None (no crash)", _peer_chat_id(_PeerEmpty()) is None)

print(f"\n== RESULT: {PASS} PASS / {FAIL} FAIL ==")
sys.exit(0 if FAIL == 0 else 1)
