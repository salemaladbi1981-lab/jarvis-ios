"""Chat streaming + search + citations + tools (UPG-3 P4 inline path).

stream_chat: SSE event generator + persistence. assistant message يُنشأ قبل التنفيذ
(execution_state=streaming) ويُثبّت COMPLETE/interrupted في النهاية — لا COMPLETE كاذب.
citations + tool_calls تُجمع من stream_source (المصادر الفعلية للأداة، لا اختراع).
"""
from __future__ import annotations
import json, time, uuid
import conversation, messages, files_api, audit, classifier, worker

EVENT_TYPES = ("message_start", "content_delta", "tool_call", "citation", "message_complete", "error")


def _evt(event: str, data: dict):
    return {"event": event, "data": data}


def _sse_frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _make_citation(message_id: str, item: dict, order: int) -> dict:
    return {
        "citation_id": f"cit-{uuid.uuid4().hex[:12]}",
        "message_id": message_id,
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "source": item.get("source", item.get("tool", "")),
        "snippet": item.get("snippet", ""),
        "order": order,
    }


def _error_type(e: Exception) -> str:
    name = type(e).__name__.lower()
    return "timeout" if "timeout" in name else "internal_error"


def _sanitize(msg: str) -> str:
    """يزيل أي شيء يشبه secret/token من رسالة الخطأ."""
    out = msg or ""
    for token in ("Bearer ", "sk-", "api_key", "token", "secret"):
        if token in out:
            return "internal_error"
    return out[:200]


def _finalize(message_id: str, content: str, citations: list, tool_calls: list, status: str, error=None):
    """يثبّت assistant message النهائي (content + citations + tool_calls + execution_state)."""
    d = messages.MessageStore()._load()
    m = d.get(message_id)
    if not m:
        return
    m["content"] = content
    m["citations"] = citations
    m["tool_calls"] = tool_calls
    m["execution_state"] = {"status": status, "error": error} if error else {"status": status}
    d[message_id] = m
    messages.MessageStore()._save(d)


def _verify_attachments(attachments, user_id, workspace_id) -> bool:
    for fid in attachments or []:
        f = files_api.get_file(fid, user_id, workspace_id)
        if not f:
            return False
    return True


def stream_chat(conversation_id: str, text: str, ident: dict, attachments=None, stream_source=None,
                client_msg_id=None):
    # Verify ownership before looking up a receipt, including on replay.
    if not conversation.ConversationStore().get(conversation_id, ident["user_id"], ident["workspace_id"]):
        yield _evt("error", {"error_type": "auth_error", "message": "conversation_not_found"})
        return
    if not client_msg_id:
        yield from _execute_chat(conversation_id, text, ident, attachments, stream_source)
        return
    import chat_requests
    scope, state, events = chat_requests.claim(ident, conversation_id, client_msg_id, text, attachments)
    if state == "complete":
        yield from events
        return
    if state != "new":
        error = {"running": "request_in_progress", "interrupted": "request_interrupted",
                 "conflict": "request_conflict"}[state]
        yield _evt("error", {"error_type": error, "message": error})
        return
    terminal = False
    try:
        for event in _execute_chat(conversation_id, text, ident, attachments, stream_source):
            events.append(event)
            terminal = event["event"] in ("message_complete", "error")
            chat_requests.record(scope, events, "complete" if terminal else "running")
            yield event
    finally:
        if not terminal:
            chat_requests.record(scope, events, "interrupted")


def _execute_chat(conversation_id: str, text: str, ident: dict, attachments=None, stream_source=None):
    """SSE generator + persistence. stream_source(text, ident, attachments) → iterable من dicts
    بنوع content_delta/tool_call/citation. قابل للحقن للاختبار."""
    user_id = ident["user_id"]
    workspace_id = ident["workspace_id"]

    # auth + conversation ownership
    conv = conversation.ConversationStore().get(conversation_id, user_id, workspace_id)
    if not conv:
        yield _evt("error", {"error_type": "auth_error", "message": "conversation_not_found"})
        return

    # attachments ownership
    if not _verify_attachments(attachments, user_id, workspace_id):
        yield _evt("error", {"error_type": "auth_error", "message": "attachment_not_owned"})
        return

    # classification (inline vs background)
    cls = classifier.classify(text, attachment_count=len(attachments or []))
    if cls["classification"] == "BACKGROUND_TASK":
        # handoff إلى P3 pipeline
        task = tasks_create(user_id, workspace_id, conversation_id, text, attachments)
        worker.enqueue(task["task_id"])
        conversation.ConversationStore().add_ref(conversation_id, "task_ids", task["task_id"])
        audit.log("chat_handoff", conversation_id=conversation_id, task_id=task["task_id"])
        yield _evt("message_complete", {"status": "background_task", "task_id": task["task_id"],
                                        "deep_link": f"jarvis://task/{task['task_id']}"})
        return

    # save user message
    messages.MessageStore().add(conversation_id, "user", text, user_id=user_id,
                                workspace_id=workspace_id, attachment_refs=attachments or [])
    # create assistant message (streaming)
    assistant = messages.MessageStore().add(conversation_id, "assistant", "", user_id=user_id,
                                            workspace_id=workspace_id,
                                            execution_state={"status": "streaming"})
    mid = assistant["message"]["message_id"]
    audit.log("chat_request", conversation_id=conversation_id, message_id=mid)

    yield _evt("message_start", {"message_id": mid, "conversation_id": conversation_id})

    content_parts, citations, tool_calls = [], [], []
    completed = False
    finalized = False
    try:
        source = stream_source(text, ident, attachments) if stream_source else hermes_stream_source(text, ident)
        audit.log("chat_stream_started", conversation_id=conversation_id, message_id=mid)
        for item in source:
            t = item.get("type")
            if t == "content_delta":
                content_parts.append(item["delta"])
                yield _evt("content_delta", {"delta": item["delta"]})
            elif t == "tool_call":
                tool_calls.append({"tool_name": item["tool_name"], "call_id": item.get("call_id", ""),
                                   "status": item.get("status", "running"), "ts": time.time()})
                audit.log("chat_tool_invoked", conversation_id=conversation_id, tool=item["tool_name"])
                yield _evt("tool_call", {"tool_name": item["tool_name"], "call_id": item.get("call_id", ""),
                                         "status": item.get("status", "running")})
            elif t == "citation":
                c = _make_citation(mid, item, len(citations) + 1)
                citations.append(c)
                yield _evt("citation", {"citation_id": c["citation_id"], "title": c["title"],
                                        "url": c["url"], "source": c["source"]})
        # complete
        content = "".join(content_parts)
        _finalize(mid, content, citations, tool_calls, "complete")
        completed = True
        finalized = True
        audit.log("chat_stream_completed", conversation_id=conversation_id, message_id=mid,
                  citations=len(citations), tool_calls=len(tool_calls))
        yield _evt("message_complete", {"message_id": mid, "status": "complete"})
    except Exception as e:
        _finalize(mid, "".join(content_parts), citations, tool_calls, "failed", error=_sanitize(str(e)))
        finalized = True
        audit.log("chat_stream_failed", conversation_id=conversation_id, message_id=mid, error=_sanitize(str(e)))
        yield _evt("error", {"error_type": _error_type(e), "message": _sanitize(str(e))})
    finally:
        if not finalized:
            _finalize(mid, "".join(content_parts), citations, tool_calls, "interrupted")


def tasks_create(user_id, workspace_id, conversation_id, text, attachments):
    import tasks as tasks_mod
    return tasks_mod.create_task(user_id, "", conversation_id, text, workspace_id=workspace_id,
                                 attachment_ids=attachments or [])


def hermes_stream_source(text, ident):
    """production stream source: يبثّ محتوى Hermes (jarvis-agent) كـ deltas.

    ملاحظة: الـcontent يُبثّ كقطعة واحدة في هذه النسخة (Hermes /v1/chat/completions
    لا يعيد stream نصيًا عبر هذا المسار)؛ citations/tool_calls تُملأ عند توفر مصدر منظم.
    """
    import brain_tools
    r = brain_tools.execute_brain_tool("jarvis_brain", {"query": text, **ident})
    if not r.get("ok"):
        raise RuntimeError(r.get("error", "provider_error"))
    yield {"type": "content_delta", "delta": r.get("answer", "")}
