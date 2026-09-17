"""Telegram Personal Account provider — server-side (MTProto via telethon).

يقرأ/يرد على حساب تيليقرام الشخصي للمالك. الجلسة في /opt/data/telegram_session
(خارج الـ repo). لا token ولا secrets في repo أو Memory.
"""
import os, asyncio, json

TG_API_ID = int(os.environ.get("TG_API_ID", "0"))
TG_API_HASH = os.environ.get("TG_API_HASH", "")
TG_SESSION_PATH = os.environ.get("TG_SESSION_PATH", "/opt/data/telegram_session")
TG_CRED_PATH = os.environ.get("TG_CRED_PATH", "/opt/data/telegram_credentials.json")


def _creds():
    """يقرأ API ID/Hash من الملف كمصدر معتمد، وenv fallback فقط إذا لزم."""
    cid, chash = 0, ""
    if os.path.exists(TG_CRED_PATH):
        d = json.load(open(TG_CRED_PATH))
        cid = int(d.get("api_id", 0) or 0)
        chash = d.get("api_hash", "")
    if not cid or not chash:
        cid, chash = TG_API_ID, TG_API_HASH
    return cid, chash


def _run(coro):
    return asyncio.run(coro)


class TelegramProvider:
    provider_name = "telegram"

    def __init__(self, session_path=None):
        self.session_path = session_path or TG_SESSION_PATH

    def _client(self):
        from telethon import TelegramClient
        cid, chash = _creds()
        return TelegramClient(self.session_path, cid, chash)

    # --- القراءة ---
    def summary(self, limit=10):
        """آخر المحادثات (dialogs) مع آخر رسالة + عدد غير المقروء."""
        async def _s():
            from telethon import functions, types
            async with self._client() as c:
                dialogs = await c.get_dialogs(limit=min(limit, 30))
                out = []
                for d in dialogs:
                    last = d.message
                    out.append({
                        "chat_id": str(d.id),
                        "title": d.title or d.name or str(d.id),
                        "preview": (last.text or last.message or "")[:200] if last else "",
                        "unread": d.unread_count,
                        "last_message_id": str(last.id) if last else None,
                    })
                return out
        return _run(_s())

    def search(self, q, limit=20):
        """بحث عام في رسائل الحساب."""
        async def _s():
            from telethon import functions, types
            async with self._client() as c:
                r = await c(functions.messages.SearchGlobalRequest(
                    q=q, filter=types.InputMessagesFilterEmpty(),
                    min_date=None, max_date=None, offset_rate=0,
                    offset_peer=types.InputPeerEmpty(), offset_id=0, limit=limit))
                out = []
                for m in r.messages:
                    out.append({
                        "chat_id": str(m.peer_id.channel_id or m.peer_id.user_id or m.peer_id.chat_id),
                        "message_id": str(m.id),
                        "sender": str(getattr(m, "sender_id", "") or ""),
                        "text": (m.text or m.message or "")[:200],
                        "date": str(getattr(m, "date", "") or ""),
                    })
                return out
        return _run(_s())

    def read_message(self, chat_id, message_id):
        async def _s():
            async with self._client() as c:
                m = await c.get_messages(int(chat_id), ids=int(message_id))
                if not m:
                    return None
                return {"chat_id": str(chat_id), "message_id": str(message_id),
                        "text": m.text or m.message or "", "date": str(m.date or "")}
        return _run(_s())

    def message_headers(self, chat_id, message_id):
        """عنوان المحادثة + آخر نص — لبناء الرد (لا نص كامل)."""
        async def _s():
            async with self._client() as c:
                ent = await c.get_entity(int(chat_id))
                title = getattr(ent, "title", None) or getattr(ent, "first_name", None) or str(chat_id)
                return {"title": str(title)}
        return _run(_s())

    # --- الإرسال ---
    def send(self, chat_id, text):
        """يرسل رسالة إلى محادثة ويعيد message id حقيقي."""
        async def _s():
            async with self._client() as c:
                sent = await c.send_message(int(chat_id), text)
                return {"id": str(sent.id), "chat_id": str(chat_id)}
        return _run(_s())
