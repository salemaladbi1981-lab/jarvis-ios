"""Telegram inbound — secure webhook handling + inline/background routing.

flow: secret → update_id dedup → extract → user mapping (allowlist) → rate-limit
→ conversation mapping (same chat) → client-msg dedup → classify → route → reply.
"""
from __future__ import annotations
import json, os, time
import config, audit, conversation, messages, tasks as tasks_mod
import classifier, tg_mapping, deeplink
import brain_tools
import worker

LAST_UPDATE_PATH = os.environ.get("JARVIS_TG_LAST_UPDATE", "/opt/data/logs/jarvis-tg-last-update.json")
RATE_PATH = os.environ.get("JARVIS_TG_RATE", "/opt/data/logs/jarvis-tg-rate.json")


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


def verify_secret(token: str) -> bool:
    expected = config.JARVIS_TG_WEBHOOK_SECRET
    return bool(expected) and token == expected


def _dedup_update(update_id: int) -> bool:
    """True = معالجة، False = replay (update_id مكرر)."""
    last = _load(LAST_UPDATE_PATH, {}).get("last_update_id", 0)
    if update_id <= last:
        return False
    _save(LAST_UPDATE_PATH, {"last_update_id": update_id, "ts": time.time()})
    return True


def _rate_limited(telegram_user_id) -> bool:
    limit = config.JARVIS_TG_RATE_LIMIT
    if limit <= 0:
        return False
    now = time.time()
    d = _load(RATE_PATH, {})
    u = str(telegram_user_id)
    hits = [t for t in d.get(u, []) if now - t < 60]
    if len(hits) >= limit:
        return True
    hits.append(now)
    d[u] = hits
    _save(RATE_PATH, d)
    return False


def _extract_message(update: dict) -> dict | None:
    msg = update.get("message") or update.get("edited_message") or update.get("channel_post")
    if not msg:
        return None
    attachments = []
    if msg.get("photo"):
        attachments.append("image")
    if msg.get("document"):
        attachments.append("document")
    if msg.get("video"):
        attachments.append("video")
    return {
        "message_id": str(msg.get("message_id")),
        "chat_id": str(msg.get("chat", {}).get("id")),
        "from_id": str(msg.get("from", {}).get("id")),
        "text": msg.get("text") or msg.get("caption") or "",
        "attachments": attachments,
    }


def _inline(conv, msg, ident, client_msg_id, cls, send_message, respond):
    if respond is not None:
        answer = respond(msg["text"], ident)
    else:
        r = brain_tools.execute_brain_tool("jarvis_brain", {"query": msg["text"], **ident})
        answer = r.get("answer", "") if r.get("ok") else ""
    messages.MessageStore().add(conv["conversation_id"], "user", msg["text"],
                                user_id=ident["user_id"], workspace_id=ident["workspace_id"],
                                client_msg_id=client_msg_id)
    messages.MessageStore().add(conv["conversation_id"], "assistant", answer,
                                user_id=ident["user_id"], workspace_id=ident["workspace_id"])
    conversation.ConversationStore().touch(conv["conversation_id"])
    if send_message:
        send_message(msg["chat_id"], answer or "تم")
    audit.log("tg_inline_response", conversation_id=conv["conversation_id"])
    return {"ok": True, "classification": "INLINE_RESPONSE", "conversation_id": conv["conversation_id"],
            "replied": bool(send_message)}


def _background(conv, msg, ident, client_msg_id, cls, send_message):
    task = tasks_mod.create_task(ident["user_id"], conv.get("session_id") or "", conv["conversation_id"],
                                 msg["text"], workspace_id=ident["workspace_id"])
    worker.enqueue(task["task_id"])
    conversation.ConversationStore().add_ref(conv["conversation_id"], "task_ids", task["task_id"])
    messages.MessageStore().add(conv["conversation_id"], "user", msg["text"],
                                user_id=ident["user_id"], workspace_id=ident["workspace_id"],
                                client_msg_id=client_msg_id, task_refs=[task["task_id"]])
    conversation.ConversationStore().touch(conv["conversation_id"])
    link = deeplink.task_link(task["task_id"])
    reply = f"المهمة انتقلت إلى JARVIS.\n{link}"
    if send_message:
        send_message(msg["chat_id"], reply)
    audit.log("tg_task_handoff", conversation_id=conv["conversation_id"], task_id=task["task_id"])
    return {"ok": True, "classification": "BACKGROUND_TASK", "task_id": task["task_id"],
            "conversation_id": conv["conversation_id"], "deep_link": link, "replied": bool(send_message)}


def handle_update(secret_token, update, send_message=None, respond=None) -> dict:
    """المسار الكامل. send_message(chat_id, text) + respond(text, ident) للحقن/الاختبار."""
    if not verify_secret(secret_token):
        return {"ok": False, "error": "invalid_secret"}
    update_id = update.get("update_id")
    if not isinstance(update_id, int):
        return {"ok": False, "error": "missing_update_id"}
    if not _dedup_update(update_id):
        return {"ok": True, "deduped": True, "reason": "replay"}
    msg = _extract_message(update)
    if not msg:
        return {"ok": True, "skipped": True, "reason": "no_message"}
    jarvis_user = tg_mapping.map_telegram_user(msg["from_id"])
    if not jarvis_user:
        audit.log("tg_unauthorized", from_id=msg["from_id"])
        return {"ok": False, "error": "unauthorized"}
    if _rate_limited(msg["from_id"]):
        audit.log("tg_rate_limited", from_id=msg["from_id"])
        return {"ok": False, "error": "rate_limited"}

    workspace_id = "PERSONAL"
    conv_store = conversation.ConversationStore()
    existing_cid = tg_mapping.get_chat_conversation(msg["chat_id"])
    conv, created = conv_store.get_or_create(jarvis_user, workspace_id, source="telegram",
                                             conversation_id=existing_cid)
    tg_mapping.set_chat_conversation(msg["chat_id"], conv["conversation_id"])

    client_msg_id = f"tg:{msg['chat_id']}:{msg['message_id']}"
    if messages.MessageStore().find_by_client_msg_id(client_msg_id):
        return {"ok": True, "deduped": True, "reason": "duplicate_message"}

    cls = classifier.classify(msg["text"], attachment_count=len(msg["attachments"]),
                              media_kinds=msg["attachments"])
    ident = {"user_id": jarvis_user, "workspace_id": workspace_id,
             "conversation_id": conv["conversation_id"]}
    if cls["classification"] == "INLINE_RESPONSE":
        return _inline(conv, msg, ident, client_msg_id, cls, send_message, respond)
    return _background(conv, msg, ident, client_msg_id, cls, send_message)
