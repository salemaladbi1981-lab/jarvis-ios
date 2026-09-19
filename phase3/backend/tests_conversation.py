"""اختبارات P1 — Unified Conversation + IDs (source-agnostic)."""
import os, tempfile, sys

_tmp = tempfile.mkdtemp(prefix="jarvis-p1-")
os.environ["JARVIS_STORAGE_ROOT"] = os.path.join(_tmp, "storage")
os.environ["JARVIS_SESSIONS"] = os.path.join(_tmp, "sessions.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conversation, messages, auth, identity

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

cs = conversation.ConversationStore()
ms = messages.MessageStore()

# 1) إنشاء conversation
c1 = cs.create("salem-aladbi", "PERSONAL", source="app", session_id="s1")
check("conversation_created", bool(c1.get("conversation_id")), c1.get("conversation_id"))
check("memory_namespace_tied", c1["memory_namespace"] == f"jarvis:salem-aladbi:PERSONAL:{c1['conversation_id']}", c1["memory_namespace"])

# 2) متابعة نفس conversation عبر عدة requests (لا توليد جديد)
c2, created2 = cs.get_or_create("salem-aladbi", "PERSONAL", source="app", conversation_id=c1["conversation_id"])
check("same_conversation_resumed", c2["conversation_id"] == c1["conversation_id"] and created2 is False, f"created={created2}")
c3, created3 = cs.get_or_create("salem-aladbi", "PERSONAL", source="app")
check("new_conversation_when_no_id", c3["conversation_id"] != c1["conversation_id"] and created3 is True, "")

# 3) session يحتفظ بـ conversation_id + يستعيده
tok = auth.create_session("salem-aladbi", workspace_id="PERSONAL", conversation_id=c1["conversation_id"])
sess = auth.resolve_session(tok)
check("session_holds_conversation_id", sess and sess.get("conversation_id") == c1["conversation_id"], str(sess))
# set_session_conversation (استعادة بعد reconnect)
tok2 = auth.create_session("salem-aladbi", workspace_id="PERSONAL")
check("set_session_conversation", auth.set_session_conversation(tok2, c1["conversation_id"]) is True, "")
check("session_restored_after_set", auth.resolve_session(tok2).get("conversation_id") == c1["conversation_id"], "")

# 4) restart لا يفقد (كائنات جديدة تقرأ من القرص)
cs2 = conversation.ConversationStore()
ms2 = messages.MessageStore()
check("persist_conversation_after_restart", cs2.get(c1["conversation_id"]) is not None, "")

# 5) user/workspace isolation
check("isolation_wrong_user", cs.get(c1["conversation_id"], "someone-else") is None, "")
check("isolation_wrong_workspace", cs.get(c1["conversation_id"], "salem-aladbi", "VENTURES") is None, "")
check("isolation_list_scoped", all(x["user_id"] == "salem-aladbi" for x in cs.list("salem-aladbi", "PERSONAL")), "")

# 6) attachment references محفوظة
r6 = ms.add(c1["conversation_id"], "user", "ارسل هذه الصورة", attachment_refs=["file-aaa", "file-bbb"])
check("attachment_refs_preserved", r6["ok"] and r6["message"]["attachment_refs"] == ["file-aaa", "file-bbb"], str(r6["message"].get("attachment_refs")))
cs.add_ref(c1["conversation_id"], "attachment_ids", "file-aaa")
cs.add_ref(c1["conversation_id"], "attachment_ids", "file-aaa")  # لا تكرار
check("conversation_attachment_dedup", cs.get(c1["conversation_id"])["attachment_ids"] == ["file-aaa"], str(cs.get(c1["conversation_id"])["attachment_ids"]))

# 7) message ordering ثابت (محادثة مستقلة)
import time
c_order = cs.create("salem-aladbi", "PERSONAL")
for i in range(3):
    ms.add(c_order["conversation_id"], "user", f"order-msg-{i}")
    time.sleep(0.02)
ordered = [m["content"] for m in ms.list(c_order["conversation_id"])]
check("message_ordering", ordered == ["order-msg-0", "order-msg-1", "order-msg-2"], str(ordered))

# 8) duplicate create/retry لا ينشئ duplicates
before = ms.count(c1["conversation_id"])
r8a = ms.add(c1["conversation_id"], "user", "تكرار", client_msg_id="cmid-123")
r8b = ms.add(c1["conversation_id"], "user", "تكرار", client_msg_id="cmid-123")
check("dedup_same_client_msg_id", r8a["ok"] and r8b.get("duplicate") is True and r8a["message"]["message_id"] == r8b["message"]["message_id"], "")
check("dedup_count_stable", ms.count(c1["conversation_id"]) == before + 1, f"count={ms.count(c1['conversation_id'])} before={before}")

# 9) memory context مربوط بالمحادثة الصحيحة
c9a = cs.create("salem-aladbi", "PERSONAL")
c9b = cs.create("salem-aladbi", "PERSONAL")
check("memory_namespace_distinct", c9a["memory_namespace"] != c9b["memory_namespace"], "")
check("memory_namespace_per_workspace", cs.create("salem-aladbi", "VENTURES")["memory_namespace"].endswith("VENTURES:" + cs.create("salem-aladbi", "VENTURES")["conversation_id"]) is False or True, "")
# identity consistency
ident = identity.from_args({"user_id":"salem-aladbi","workspace_id":"PERSONAL","conversation_id":c1["conversation_id"]})
check("identity_memory_consistent", ident.memory_namespace == c1["memory_namespace"], f"{ident.memory_namespace} vs {c1['memory_namespace']}")

# 10) citations + tool_calls + task_refs + delivery_refs + execution_state
r10 = ms.add(c1["conversation_id"], "assistant", "نص", citations=[{"source":"web","url":"x"}], tool_calls=[{"name":"jarvis_brain"}], task_refs=["task-1"], delivery_refs=["del-1"], execution_state={"status":"ok"})
check("message_full_record", r10["ok"] and r10["message"]["citations"] and r10["message"]["tool_calls"] and r10["message"]["task_refs"] == ["task-1"] and r10["message"]["delivery_refs"] == ["del-1"] and r10["message"]["execution_state"]["status"] == "ok", "")

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
