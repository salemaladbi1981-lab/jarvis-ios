"""Telegram Personal Account auth — phone + OTP → .session (server-side, لا token يُعرض).

التدفق: API ID/Hash (مرة واحدة) → رقم الهاتف → OTP → جلسة محفوظة.
كل شيء عبر نموذج ويب آمن، لا يمر أي credential عبر المحادثة.
"""
import os, asyncio, json, secrets, time
from telegram_provider import TG_API_ID, TG_API_HASH, TG_SESSION_PATH, _run

CRED_PATH = os.environ.get("TG_CRED_PATH", "/opt/data/telegram_credentials.json")
OTP_PATH = "/opt/data/tg_otp_state.json"


def _creds():
    cid = TG_API_ID
    chash = TG_API_HASH
    if (not cid or not chash) and os.path.exists(CRED_PATH):
        d = json.load(open(CRED_PATH))
        cid = int(d.get("api_id", 0) or 0)
        chash = d.get("api_hash", "")
    return cid, chash


def is_configured():
    cid, chash = _creds()
    return bool(cid and chash)


def store_credentials(api_id, api_hash):
    with open(CRED_PATH, "w", encoding="utf-8") as f:
        json.dump({"api_id": api_id, "api_hash": api_hash}, f, indent=2)
    os.chmod(CRED_PATH, 0o600)


def start_login(phone):
    """يرسل كود OTP إلى الهاتف ويعيد phone_code_hash."""
    cid, chash = _creds()
    async def _s():
        from telethon import TelegramClient
        client = TelegramClient(TG_SESSION_PATH, cid, chash)
        await client.connect()
        sent = await client.send_code_request(phone)
        ph = sent.phone_code_hash
        await client.disconnect()
        return ph
    ph = _run(_s())
    with open(OTP_PATH, "w", encoding="utf-8") as f:
        json.dump({"phone": phone, "phone_code_hash": ph, "ts": time.time()}, f)
    os.chmod(OTP_PATH, 0o600)
    return {"sent": True}


def complete_login(phone, code):
    """يوقّع الدخول بالـ OTP وينشئ الجلسة."""
    cid, chash = _creds()
    ph = ""
    if os.path.exists(OTP_PATH):
        st = json.load(open(OTP_PATH))
        if st.get("phone") == phone:
            ph = st.get("phone_code_hash", "")
    async def _s():
        from telethon import TelegramClient
        client = TelegramClient(TG_SESSION_PATH, cid, chash)
        await client.connect()
        me = await client.sign_in(phone, code, phone_code_hash=ph)
        await client.disconnect()
        return me
    me = _run(_s())
    return {"user_id": str(me.id), "username": me.username or "",
            "first_name": me.first_name or "", "phone": me.phone or phone}


def is_logged_in():
    if not os.path.exists(TG_SESSION_PATH + ".session"):
        return False
    cid, chash = _creds()
    async def _s():
        from telethon import TelegramClient
        client = TelegramClient(TG_SESSION_PATH, cid, chash)
        await client.connect()
        auth = await client.is_user_authorized()
        await client.disconnect()
        return auth
    try:
        return _run(_s())
    except Exception:
        return False
