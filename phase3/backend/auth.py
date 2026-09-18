"""Server-side identity — لا نثق بـ user_id من العميل أبدًا.

الهوية تُستخرج من session موثّق (X-Jarvis-Session header) عبر مخزن server-side.
بدون session موثّق → تُرفض الطلبات (401).
"""
from __future__ import annotations
import json, os, time, uuid

SESSION_PATH = os.environ.get("JARVIS_SESSIONS", "/opt/data/logs/jarvis-sessions.json")


def _load() -> dict:
    try:
        with open(SESSION_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d: dict) -> None:
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    tmp = SESSION_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, SESSION_PATH)


def create_session(user_id: str, session_id: str | None = None) -> str:
    """يصدر session token server-side (لا يثق بالعميل)."""
    d = _load()
    sid = session_id or uuid.uuid4().hex[:24]
    d[sid] = {"user_id": user_id, "created_at": time.time()}
    _save(d)
    return sid


def resolve_user(session_token: str | None) -> str | None:
    """يستخرج user_id من session موثّق. يُرجع None إذا لا session صالح."""
    if not session_token:
        return None
    s = _load().get(session_token)
    if not s:
        return None
    return s.get("user_id")


def revoke_session(session_token: str) -> None:
    d = _load()
    d.pop(session_token, None)
    _save(d)


PRIMARY_USER_ID = "salem-aladbi"


def bootstrap(proof: str) -> str | None:
    """App authentication/bootstrap: server يتحقق من سرّ enrollment ويصدر session للمستخدم الأساسي.

    العميل لا يختار user_id — الهوية يحددها السيرفر.
    """
    import config
    expected = getattr(config, "JARVIS_BOOTSTRAP_KEY", "") or os.environ.get("JARVIS_BOOTSTRAP_KEY", "")
    if not expected or not proof or proof != expected:
        return None
    return create_session(PRIMARY_USER_ID)
