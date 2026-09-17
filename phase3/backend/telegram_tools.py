"""Telegram tools — نفس Grounded Tool Contract + confirmation (account الشخصي).

قابل لإعادة الاستخدام: نفس دورة Realtime Function Calling المثبتة مع البريد.
كل رسالة تحمل chat_id + message_id (لا اعتماد على message_id وحده).
"""
from telegram_provider import TelegramProvider


TELEGRAM_TOOLS = [
    {
        "type": "function",
        "name": "telegram_summary",
        "description": "List the user's recent Telegram chats (dialogs) with their last message and unread count. Each result carries chat_id + title + preview + unread + last_message_id. Use when the user asks about their Telegram messages/chats.",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "max chats (1-30, default 10)"},
        }, "required": []},
    },
    {
        "type": "function",
        "name": "telegram_search",
        "description": "Search the user's Telegram messages by keyword. Each result carries chat_id + message_id + text. Never invent a message.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        }, "required": ["query"]},
    },
    {
        "type": "function",
        "name": "telegram_read",
        "description": "Read the full text of ONE Telegram message by chat_id + message_id (both from summary/search results). Both required — never guess.",
        "parameters": {"type": "object", "properties": {
            "chat_id": {"type": "string"},
            "message_id": {"type": "string"},
        }, "required": ["chat_id", "message_id"]},
    },
    {
        "type": "function",
        "name": "telegram_draft_reply",
        "description": "Prepare a draft message to a Telegram chat (chat_id). Returns the draft WITHOUT sending. Then show the draft and ask the user to confirm.",
        "parameters": {"type": "object", "properties": {
            "chat_id": {"type": "string"},
            "text": {"type": "string"},
        }, "required": ["chat_id", "text"]},
    },
    {
        "type": "function",
        "name": "telegram_send",
        "description": "Send the pending draft Telegram message. MUST ONLY be called after the user explicitly confirms ('أرسل').",
        "parameters": {"type": "object", "properties": {
            "confirmed": {"type": "boolean"},
        }, "required": ["confirmed"]},
    },
]


def get_telegram_provider():
    return TelegramProvider()


def execute_telegram_tool(name, args, pending, provider=None):
    provider = provider or get_telegram_provider()
    try:
        if name == "telegram_summary":
            return {"ok": True, "dialogs": provider.summary(limit=args.get("limit", 10))}

        if name == "telegram_search":
            return {"ok": True, "messages": provider.search(args.get("query", ""), args.get("limit", 20))}

        if name == "telegram_read":
            chat_id = args.get("chat_id", "")
            mid = args.get("message_id", "")
            if not chat_id:
                return {"ok": False, "error": "chat_id_required"}
            if not mid:
                return {"ok": False, "error": "message_id_required"}
            m = provider.read_message(chat_id, mid)
            if not m:
                return {"ok": False, "error": "message_not_found"}
            return {"ok": True, "message": m}

        if name == "telegram_draft_reply":
            chat_id = args.get("chat_id", "")
            if not chat_id:
                return {"ok": False, "error": "chat_id_required"}
            text = args.get("text", "")
            pending["draft"] = {"chat_id": chat_id, "text": text}
            return {"ok": True, "draft": {"chat_id": chat_id, "text": text},
                    "note": "اعرض المسودة واطلب تأكيداً صريحاً قبل الإرسال"}

        if name == "telegram_send":
            if not args.get("confirmed"):
                return {"ok": False, "error": "confirmation_required"}
            draft = pending.get("draft")
            if not draft:
                return {"ok": False, "error": "no_pending_draft"}
            r = provider.send(draft["chat_id"], draft["text"])
            pending.pop("draft", None)
            return {"ok": True, "chat_id": draft["chat_id"], "sent_message_id": r.get("id")}

        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
