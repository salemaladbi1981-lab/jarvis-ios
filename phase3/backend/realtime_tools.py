"""Realtime Tool Orchestration — email tools (function calling).

Grounded Tool Contract:
- النموذج يجيب عن بيانات البريد حصراً من نتيجة الأداة (لا اختراع).
- empty/failure → نتيجة صريحة («لم أجد/تعذر الوصول») لا محتوى مولّد.
- كل رسالة مرتبطة بـ Gmail message id حقيقي.
- الإرسال لا يحدث إلا بعد تأكيد صريح مربوط بالمسودة المعلّقة نفسها.

قابل لإعادة الاستخدام: إضافة Web/Search/Files لاحقاً = إضافة تعريف أداة + فرع تنفيذ هنا فقط.
"""
import gmail_tools


EMAIL_TOOLS = [
    {
        "type": "function",
        "name": "email_summary",
        "description": "List the user's recent inbox emails (id, from, subject, snippet, unread). Use when the user asks about their email/inbox/important messages.",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "description": "max emails (1-20, default 8)"}}, "required": []},
    },
    {
        "type": "function",
        "name": "email_search",
        "description": "Search the user's email by sender/subject/period. Use when the user asks to find a specific email.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Gmail search query, e.g. 'from:someone' or 'subject:invoice' or 'newer_than:2d'"}}, "required": ["query"]},
    },
    {
        "type": "function",
        "name": "email_read",
        "description": "Read the full body of ONE email by its Gmail message id (taken from email_summary/email_search results).",
        "parameters": {"type": "object", "properties": {"message_id": {"type": "string"}}, "required": ["message_id"]},
    },
    {
        "type": "function",
        "name": "email_draft_reply",
        "description": "Prepare a draft reply to a specific email (by message id). Returns the draft (to/subject/body) WITHOUT sending. Then show the draft and ask the user to confirm before sending.",
        "parameters": {"type": "object", "properties": {"message_id": {"type": "string"}, "body": {"type": "string"}}, "required": ["message_id", "body"]},
    },
    {
        "type": "function",
        "name": "email_send",
        "description": "Send the pending draft reply. MUST ONLY be called after the user explicitly confirms (says 'أرسل'). Never call from a draft or intent alone.",
        "parameters": {"type": "object", "properties": {"confirmed": {"type": "boolean"}}, "required": ["confirmed"]},
    },
]


def execute_email_tool(name, args, pending):
    """تنفيذ أداة بريد. `pending` قاموس لكل جلسة يحمل المسودة المعلّقة (بوابة التأكيد)."""
    try:
        if name == "email_summary":
            return {"ok": True, "emails": gmail_tools.summary(limit=min(int(args.get("limit", 8)), 20))}
        if name == "email_search":
            return {"ok": True, "emails": gmail_tools.search(args.get("query", ""))}
        if name == "email_read":
            return {"ok": True, "message": gmail_tools.read_message(args.get("message_id", ""))}
        if name == "email_draft_reply":
            mid = args.get("message_id", "")
            h = gmail_tools.message_headers(mid)
            if not h.get("from"):
                return {"ok": False, "error": "message_not_found"}
            to = h["from"]
            subject = h["subject"] if h["subject"].startswith("Re:") else ("Re: " + h["subject"])
            body = args.get("body", "")
            pending["draft"] = {"to": to, "subject": subject, "body": body, "message_id": mid}
            return {"ok": True, "draft": {"to": to, "subject": subject, "body": body},
                    "note": "اعرض المسودة واطلب تأكيداً صريحاً قبل الإرسال"}
        if name == "email_send":
            if not args.get("confirmed"):
                return {"ok": False, "error": "confirmation_required"}
            draft = pending.get("draft")
            if not draft:
                return {"ok": False, "error": "no_pending_draft"}
            r = gmail_tools.send(draft["to"], draft["subject"], draft["body"])
            pending.pop("draft", None)
            return {"ok": True, "sent_message_id": r.get("id")}
        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
