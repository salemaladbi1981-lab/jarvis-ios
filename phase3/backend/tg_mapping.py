"""Telegram user/chat → JARVIS identity mapping (persistent, server-side).

لا ثقة في user_id من الـpayload — الربط داخلي عبر allowlist + map دائم.
"""
from __future__ import annotations
import json, os, time
import config

TG_USER_MAP_PATH = os.environ.get("JARVIS_TG_USER_MAP", "/opt/data/logs/jarvis-tg-users.json")
TG_CHAT_CONV_PATH = os.environ.get("JARVIS_TG_CHAT_CONV", "/opt/data/logs/jarvis-tg-chat-conv.json")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def allowed_telegram_users() -> set:
    return {u.strip() for u in config.JARVIS_TG_ALLOWED_USERS.split(",") if u.strip()}


def map_telegram_user(telegram_user_id) -> str | None:
    """يربط telegram user بـ jarvis user_id. None إذا غير مصرح."""
    tg_id = str(telegram_user_id)
    if tg_id not in allowed_telegram_users():
        return None
    d = _load(TG_USER_MAP_PATH, {})
    if tg_id not in d:
        d[tg_id] = "salem-aladbi"  # المالك الافتراضي
        _save(TG_USER_MAP_PATH, d)
    return d[tg_id]


def get_chat_conversation(telegram_chat_id) -> str | None:
    return _load(TG_CHAT_CONV_PATH, {}).get(str(telegram_chat_id))


def set_chat_conversation(telegram_chat_id, conversation_id) -> None:
    d = _load(TG_CHAT_CONV_PATH, {})
    d[str(telegram_chat_id)] = conversation_id
    _save(TG_CHAT_CONV_PATH, d)
