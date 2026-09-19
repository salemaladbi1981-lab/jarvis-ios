"""اختبارات P2 — Telegram/App Handoff + Classification."""
import os, tempfile, sys

_tmp = tempfile.mkdtemp(prefix="jarvis-p2-")
os.environ["JARVIS_STORAGE_ROOT"] = os.path.join(_tmp, "storage")
os.environ["JARVIS_SESSIONS"] = os.path.join(_tmp, "sessions.json")
os.environ["JARVIS_TG_USER_MAP"] = os.path.join(_tmp, "tg-users.json")
os.environ["JARVIS_TG_CHAT_CONV"] = os.path.join(_tmp, "tg-chat-conv.json")
os.environ["JARVIS_TG_LAST_UPDATE"] = os.path.join(_tmp, "tg-last-update.json")
os.environ["JARVIS_TG_RATE"] = os.path.join(_tmp, "tg-rate.json")
os.environ["JARVIS_TG_WEBHOOK_SECRET"] = "test-secret-xyz"
os.environ["JARVIS_TG_ALLOWED_USERS"] = "111"
os.environ["JARVIS_TG_RATE_LIMIT"] = "1000"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conversation, messages, tasks as tasks_mod, tg_mapping, tg_inbound, classifier, deeplink

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

SECRET = "test-secret-xyz"
def upd(uid, from_id, chat_id, text, msg_id=None):
    return {"update_id": uid, "message": {"message_id": msg_id or uid,
        "chat": {"id": chat_id}, "from": {"id": from_id}, "text": text}}

replies = []
def send_message(chat_id, text): replies.append((chat_id, text))
def respond(text, ident): return f"جواب: {text}"

# 1) classifier ليس keyword-only
c_kw = classifier.classify("أنشئ فيديو")  # كلمة توليد وحدها، بلا وزن هيكلي
check("classifier_not_keyword_only_short", c_kw["classification"] == "INLINE_RESPONSE",
      f"score={c_kw['score']} reasons={c_kw['reasons']}")
c_vid = classifier.classify("اقرأ هذا الملف", media_kinds=["video"])
check("classifier_structural_video", c_vid["classification"] == "BACKGROUND_TASK",
      f"score={c_vid['score']} reasons={c_vid['reasons']}")
c_long = classifier.classify("اكتب تقريرًا مفصلاً عن السوق ثم حلل المنافسين وقدم خطة كاملة متكاملة تشمل التوصيات")
check("classifier_multi_step_heavy", c_long["classification"] == "BACKGROUND_TASK",
      f"score={c_long['score']} reasons={c_long['reasons']}")

# 2) invalid secret
r = tg_inbound.handle_update("wrong-secret", upd(999, "111", "c1", "مرحبا"))
check("invalid_secret_rejected", r.get("error") == "invalid_secret", str(r))

# 3) unauthorized user
r = tg_inbound.handle_update(SECRET, upd(1, "999", "c1", "مرحبا"))
check("unauthorized_user_rejected", r.get("error") == "unauthorized", str(r))

# 4) authorized inline
r = tg_inbound.handle_update(SECRET, upd(2, "111", "c1", "مرحبا كيف حالك"), send_message, respond)
check("inline_accepted", r.get("ok") and r.get("classification") == "INLINE_RESPONSE", str(r))
check("inline_replied", len(replies) == 1, str(replies))

# 5) same chat → same conversation
r2 = tg_inbound.handle_update(SECRET, upd(3, "111", "c1", "شكرا"), send_message, respond)
check("same_chat_same_conversation", r2.get("conversation_id") == r.get("conversation_id"),
      f"{r2.get('conversation_id')} vs {r.get('conversation_id')}")

# 6) heavy request → task
HEAVY = "أنشئ فيديو ترويجي كامل عن المطعم، ثم صمم الغلاف، وأرسل النتيجة للعميل مع تقرير شامل"
rh = tg_inbound.handle_update(SECRET, upd(4, "111", "c2", HEAVY), send_message, respond)
check("heavy_creates_task", rh.get("ok") and rh.get("classification") == "BACKGROUND_TASK" and bool(rh.get("task_id")), str(rh))
check("heavy_deeplink", rh.get("deep_link") == f"jarvis://task/{rh['task_id']}", rh.get("deep_link"))
check("heavy_replied_handoff", any("JARVIS" in t for _, t in replies), str(replies))

# 7) task linked to same conversation
conv = conversation.ConversationStore().get(rh["conversation_id"])
check("task_linked_to_conversation", rh["task_id"] in conv.get("task_ids", []), str(conv.get("task_ids")))

# 8) app reads same conversation + task refs
conv_app = conversation.ConversationStore().get(rh["conversation_id"], "salem-aladbi", "PERSONAL")
msgs = messages.MessageStore().list(rh["conversation_id"])
check("app_reads_same_conversation", conv_app is not None and conv_app["conversation_id"] == rh["conversation_id"], "")
check("app_sees_task_refs", any(m.get("task_refs") == [rh["task_id"]] for m in msgs), str([m.get("task_refs") for m in msgs]))

# 9) deep-link resolve correct + wrong user
dl = deeplink.resolve_target(rh["deep_link"], "salem-aladbi", "PERSONAL")
check("deeplink_resolve_owner", dl is not None and dl["id"] == rh["task_id"], str(dl and dl["id"]))
dl_bad = deeplink.resolve_target(rh["deep_link"], "someone-else", "PERSONAL")
check("deeplink_resolve_wrong_user", dl_bad is None, str(dl_bad))
dl_parse = deeplink.parse(rh["deep_link"])
check("deeplink_parse", dl_parse == {"kind": "task", "id": rh["task_id"]}, str(dl_parse))

# 10) duplicate webhook (same update_id) → replay dedup
n_tasks_before = len(tasks_mod.list_tasks("salem-aladbi"))
r_replay = tg_inbound.handle_update(SECRET, upd(4, "111", "c2", HEAVY), send_message, respond)
check("replay_deduped", r_replay.get("deduped") is True and r_replay.get("reason") == "replay", str(r_replay))

# 11) duplicate webhook (new update_id, same message_id) → no duplicate message/task
r_dup = tg_inbound.handle_update(SECRET, upd(5, "111", "c2", HEAVY, msg_id=4), send_message, respond)
check("duplicate_message_deduped", r_dup.get("deduped") is True and r_dup.get("reason") == "duplicate_message", str(r_dup))
n_tasks_after = len(tasks_mod.list_tasks("salem-aladbi"))
check("duplicate_webhook_no_dup_task", n_tasks_after == n_tasks_before, f"{n_tasks_before}->{n_tasks_after}")

# 12) no conversation duplication for same chat
n_conv_c2 = len([c for c in conversation.ConversationStore().list("salem-aladbi") if c.get("source") == "telegram"])
check("single_conversation_per_chat", n_conv_c2 <= 2, f"n={n_conv_c2}")  # c1 + c2

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
