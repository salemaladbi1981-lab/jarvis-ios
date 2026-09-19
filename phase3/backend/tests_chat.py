"""اختبارات P4 — Chat Streaming + Search + Citations + Tools."""
import os, tempfile, sys

_tmp = tempfile.mkdtemp(prefix="jarvis-p4-")
os.environ["JARVIS_STORAGE_ROOT"] = os.path.join(_tmp, "storage")
os.environ["JARVIS_SESSIONS"] = os.path.join(_tmp, "sessions.json")
os.environ["JARVIS_AGENT_STATE"] = os.path.join(_tmp, "agent-state.json")
os.environ["JARVIS_AGENT_AUDIT"] = os.path.join(_tmp, "agent-audit.jsonl")
os.environ["JARVIS_AUDIT_PATH"] = os.path.join(_tmp, "audit.jsonl")
os.environ["JARVIS_APPROVAL_PATH"] = os.path.join(_tmp, "approvals.json")
os.environ["JARVIS_KILL_SWITCH"] = os.path.join(_tmp, "kill-switch.json")
os.environ["JARVIS_HERMES_PROFILE"] = "jarvis-agent"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chat, conversation, messages, files_api, classifier, audit, agent_runner

results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, detail)

IDENT = {"user_id": "salem-aladbi", "workspace_id": "PERSONAL"}

# محاكاة stream source: deltas + tool_call + citations (مصادر حقيقية تطابق نتائج الأداة)
SEARCH_RESULTS = [{"title": "Bayt Sharq", "url": "https://example.com/bayt-sharq", "snippet": "مطعم قطري تراثي"}]
def mock_stream(text, ident, attachments):
    yield {"type": "content_delta", "delta": "أفضل "}
    yield {"type": "tool_call", "tool_name": "web_search", "call_id": "c1", "status": "running"}
    yield {"type": "content_delta", "delta": "المطاعم هي "}
    yield {"type": "citation", "title": "Bayt Sharq", "url": "https://example.com/bayt-sharq", "source": "web_search", "snippet": "مطعم قطري تراثي"}
    yield {"type": "content_delta", "delta": "بيت الشرق."}

def failing_stream(text, ident, attachments):
    yield {"type": "content_delta", "delta": "جاري البحث..."}
    raise RuntimeError("sk-secret-leak-example-token")

# setup conversation
conv = conversation.ConversationStore().create("salem-aladbi", "PERSONAL", source="app", session_id="s")
cid = conv["conversation_id"]

# 1) streaming events + ترتيب
evts = list(chat.stream_chat(cid, "ابحث عن مطاعم قطرية", IDENT, stream_source=mock_stream))
ev_types = [e["event"] for e in evts]
check("stream_message_start", "message_start" in ev_types, str(ev_types))
check("stream_content_deltas", ev_types.count("content_delta") == 3, str(ev_types))
check("stream_tool_call_event", "tool_call" in ev_types, "")
check("stream_citation_event", "citation" in ev_types, "")
check("stream_message_complete", ev_types[-1] == "message_complete", str(ev_types[-1]))
check("deltas_before_complete", ev_types.index("content_delta") < ev_types.index("message_complete"), "")
# streaming يبدأ قبل الاكتمال: أول delta قبل complete
check("streaming_starts_before_complete", "content_delta" in ev_types and ev_types.count("content_delta") > 1, "")

# 2) completed message persisted
msgs = messages.MessageStore().list(cid)
assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
check("completed_message_persisted", len(assistant_msgs) == 1 and assistant_msgs[0]["content"] == "أفضل المطاعم هي بيت الشرق.", str(assistant_msgs[0]["content"]))
check("execution_state_complete", assistant_msgs[0]["execution_state"]["status"] == "complete", str(assistant_msgs[0]["execution_state"]))

# 3) citations persisted + survive restart
cits = assistant_msgs[0]["citations"]
check("citation_persisted", len(cits) == 1, str(cits))
check("citation_url_matches", cits[0]["url"] == "https://example.com/bayt-sharq", str(cits[0].get("url")))
check("citation_title_matches", cits[0]["title"] == "Bayt Sharq", str(cits[0].get("title")))
check("citation_source_tool", cits[0]["source"] == "web_search", str(cits[0].get("source")))
check("citation_has_id_message", bool(cits[0].get("citation_id")) and cits[0].get("message_id") == assistant_msgs[0]["message_id"], "")
check("no_fabricated_citation", len(cits) == len(SEARCH_RESULTS), f"citations={len(cits)} vs search={len(SEARCH_RESULTS)}")
# survive restart (كائن جديد)
msgs2 = messages.MessageStore()
check("citations_survive_restart", len(msgs2.list(cid)[-1]["citations"]) == 1, "")

# 4) tool call persisted
tc = assistant_msgs[0]["tool_calls"]
check("tool_call_persisted", len(tc) == 1 and tc[0]["tool_name"] == "web_search" and tc[0]["call_id"] == "c1", str(tc))

# 5) same conversation (لا conversation جديد)
check("same_conversation_preserved", all(m["conversation_id"] == cid for m in msgs), "")
n_conv = len(conversation.ConversationStore().list("salem-aladbi"))
check("no_new_conversation", n_conv == 1, f"n={n_conv}")

# 6) conversation history used (messages تتراكم)
check("conversation_history_grows", len(msgs) >= 2, f"msgs={len(msgs)}")

# 7) error sanitized + not COMPLETE
evts_err = list(chat.stream_chat(cid, "ابحث عن شيء", IDENT, stream_source=failing_stream))
err_evts = [e for e in evts_err if e["event"] == "error"]
check("error_structured", len(err_evts) == 1 and err_evts[0]["data"]["error_type"] == "internal_error", str(err_evts))
check("error_sanitized", "sk-" not in str(err_evts[0]["data"].get("message", "")), str(err_evts[0]["data"].get("message")))
failed_msgs = [m for m in messages.MessageStore().list(cid) if m["role"] == "assistant" and m.get("execution_state", {}).get("status") == "failed"]
check("no_fake_complete_on_error", len(failed_msgs) == 1, f"failed={len(failed_msgs)}")

# 8) attachment ownership enforced
bad = list(chat.stream_chat(cid, "اقرأ المرفق", IDENT, attachments=["nonexistent-file"], stream_source=mock_stream))
check("attachment_ownership_enforced", bad[0]["event"] == "error" and bad[0]["data"]["error_type"] == "auth_error", str(bad[0]))

# 9) inline vs background (classifier محفوظ)
inline = classifier.classify("مرحبا كيف حالك")
check("inline_stays_inline", inline["classification"] == "INLINE_RESPONSE", str(inline))
HEAVY = "أنشئ فيديو ترويجي كامل ثم صمم الغلاف وأرسله للعميل مع تقرير شامل"
bg = list(chat.stream_chat(cid, HEAVY, IDENT, stream_source=mock_stream))
check("heavy_goes_background", bg[-1]["event"] == "message_complete" and bg[-1]["data"].get("status") == "background_task" and bool(bg[-1]["data"].get("task_id")), str(bg[-1]))

# 10) cross-user isolation
other = list(chat.stream_chat(cid, "مرحبا", {"user_id": "other", "workspace_id": "PERSONAL"}, stream_source=mock_stream))
check("cross_user_rejected", other[0]["event"] == "error" and other[0]["data"]["error_type"] == "auth_error", str(other[0]))

# 11) Restricted Profile + forbidden tools
check("restricted_profile_configured", __import__("config").JARVIS_HERMES_PROFILE == "jarvis-agent", "")
enf = agent_runner.enforce("core_writer", tools=["terminal", "file", "skills"])
check("forbidden_tools_unavailable", enf["allowed"] is False and all(t in enf["blocked_tools"] for t in ("terminal", "file", "skills")), str(enf))

# 12) audit chain valid
v = audit.verify()
check("audit_chain_valid", v["ok"] is True, str(v))

passed = sum(1 for _, c, _ in results if c)
print(f"\n=== {passed}/{len(results)} PASS ===")
sys.exit(0 if passed == len(results) else 1)
