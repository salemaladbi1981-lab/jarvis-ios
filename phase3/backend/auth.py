"""Server-side identity — لا نثق بـ user_id من العميل أبدًا.

الهوية تُستخرج من session موثّق (X-Jarvis-Session header) عبر مخزن server-side.
بدون session موثّق → تُرفض الطلبات (401).
"""
from __future__ import annotations
import json, os, time, uuid, secrets
import workspace

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


def create_session(user_id: str, session_id: str | None = None,
                    workspace_id: str = workspace.DEFAULT_WORKSPACE) -> str:
    """يصدر session token server-side (لا يثق بالعميل). يحمل مساحة العمل."""
    d = _load()
    sid = session_id or uuid.uuid4().hex[:24]
    d[sid] = {"user_id": user_id, "workspace_id": workspace_id, "created_at": time.time()}
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


def resolve_session(session_token: str | None) -> dict | None:
    """يستخرج {user_id, workspace_id} من session موثّق. None إذا لا session صالح."""
    if not session_token:
        return None
    s = _load().get(session_token)
    if not s:
        return None
    return {"user_id": s.get("user_id"),
            "workspace_id": s.get("workspace_id", workspace.DEFAULT_WORKSPACE)}


def revoke_session(session_token: str) -> None:
    d = _load()
    d.pop(session_token, None)
    _save(d)


ENROLL_PATH = os.environ.get("JARVIS_ENROLL", "/opt/data/logs/jarvis-enroll.json")


def _load_enroll() -> dict:
    try:
        with open(ENROLL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_enroll(d: dict) -> None:
    os.makedirs(os.path.dirname(ENROLL_PATH), exist_ok=True)
    tmp = ENROLL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, ENROLL_PATH)


def create_enrollment_code(ttl_seconds: int = 600) -> str:
    """يولّد رمز pairing لمرة واحدة (server-side)، يُسلَّم للمالك out-of-band."""
    code = secrets.token_urlsafe(24)
    d = _load_enroll()
    d[code] = {"created_at": time.time(), "expires_at": time.time() + ttl_seconds, "used": False}
    _save_enroll(d)
    return code


def redeem_enrollment(code: str) -> str | None:
    """يستبدل رمز pairing (مرة واحدة، تنتهي صلاحيته) بـ session_token."""
    d = _load_enroll()
    rec = d.get(code)
    if not rec or rec.get("used") or time.time() > rec.get("expires_at", 0):
        return None
    rec["used"] = True
    d[code] = rec
    _save_enroll(d)
    return create_session(PRIMARY_USER_ID)


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
