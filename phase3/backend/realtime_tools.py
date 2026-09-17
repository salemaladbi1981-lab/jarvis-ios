"""Realtime Tool Orchestration — multi-account email tools (function calling).

Grounded Tool Contract (إلزامي):
- النموذج يجيب عن بيانات البريد حصراً من نتيجة الأداة (لا اختراع).
- كل رسالة تحمل account_id + message_id — ممنوع الاعتماد على message_id وحده.
- الإرسال لا يحدث إلا بعد تأكيد صريح، ومن الحساب المرتبط بالرسالة نفسها.
- success لا يُعلن إلا بعد provider API success + sent message ID حقيقي + account_id صحيح.

قابل لإعادة الاستخدام: إضافة Web/Search/Files لاحقاً = تعريف أداة + فرع تنفيذ هنا فقط.
"""
import email_accounts


EMAIL_TOOLS = [
    {
        "type": "function",
        "name": "email_summary",
        "description": "List the user's recent inbox emails across ALL linked accounts (or ONE account if account_id given). Each result carries account_id + account (display name) + id (message id). Use when the user asks about their email/inbox/important messages. If the user specifies a particular account, use that exact account_id from the list (do not guess).",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "max emails per account (1-20, default 8)"},
            "account_id": {"type": "string", "description": "optional — restrict to one account (e.g. 'personal', 'work'). Omit to search all."},
        }, "required": []},
    },
    {
        "type": "function",
        "name": "email_search",
        "description": "Search the user's email by sender/subject/period, across all accounts or one account.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "search query, e.g. 'from:someone' or 'subject:invoice' or 'newer_than:2d'"},
            "account_id": {"type": "string", "description": "optional — restrict to one account"},
        }, "required": ["query"]},
    },
    {
        "type": "function",
        "name": "email_read",
        "description": "Read the full body of ONE email by account_id + message_id (both taken from email_summary/email_search results). Both are required — never guess.",
        "parameters": {"type": "object", "properties": {
            "account_id": {"type": "string", "description": "the account the message came from"},
            "message_id": {"type": "string", "description": "the message id from summary/search results"},
        }, "required": ["account_id", "message_id"]},
    },
    {
        "type": "function",
        "name": "email_draft_reply",
        "description": "Prepare a draft reply to a specific email (account_id + message_id). Returns the draft WITHOUT sending. Then show the draft and ask the user to confirm before sending.",
        "parameters": {"type": "object", "properties": {
            "account_id": {"type": "string", "description": "the account that owns the message"},
            "message_id": {"type": "string"},
            "body": {"type": "string"},
        }, "required": ["account_id", "message_id", "body"]},
    },
    {
        "type": "function",
        "name": "email_send",
        "description": "Send the pending draft reply. MUST ONLY be called after the user explicitly confirms ('أرسل'). The send always goes from the account that owns the draft. account_id optional (only to verify). If the user's intended account is unclear, ASK which account — do not send.",
        "parameters": {"type": "object", "properties": {
            "confirmed": {"type": "boolean"},
            "account_id": {"type": "string", "description": "optional — the account to verify against the draft"},
        }, "required": ["confirmed"]},
    },
]


def account_list_hint(registry=None):
    """قائمة الحسابات الحقيقية المسجّلة — تُحقن في وصف الأدوات (لا hard-code)."""
    registry = registry or email_accounts.default_registry()
    accounts = registry.all_accounts()
    if not accounts:
        return "No accounts linked."
    return "Available accounts: " + ", ".join(f"{a.account_id} ({a.display_name})" for a in accounts) + "."


def build_email_tools(registry=None):
    """يبني الأدوات مع قائمة الحسابات الفعلية محقونة في الوصف (Dynamic Account Grounding)."""
    import copy
    registry = registry or email_accounts.default_registry()
    hint = account_list_hint(registry)
    rule = " Use ONLY one of these exact account_ids. NEVER invent or guess an account_id. A non-existent account_id returns account_not_found."
    tools = copy.deepcopy(EMAIL_TOOLS)
    for t in tools:
        if t["name"] in ("email_summary", "email_search"):
            t["description"] = t["description"] + " " + hint + rule
        elif t["name"] in ("email_read", "email_draft_reply"):
            t["parameters"]["properties"]["account_id"]["description"] = "account id from the list. " + hint + rule
        elif t["name"] == "email_send":
            p = t["parameters"]["properties"].get("account_id")
            if p:
                p["description"] = "optional, to verify against the draft. " + hint + rule
    return tools


def execute_email_tool(name, args, pending, registry=None):
    """تنفيذ أداة بريد. `pending` قاموس لكل جلسة يحمل المسودة المعلّقة (بوابة التأكيد)."""
    registry = registry or email_accounts.default_registry()
    try:
        if name == "email_summary":
            aid = args.get("account_id")
            if aid and not registry.get(aid):
                return {"ok": False, "error": "account_not_found"}
            limit = min(int(args.get("limit", 8)), 20)
            return {"ok": True, "emails": registry.summary(account_id=aid, limit=limit)}

        if name == "email_search":
            aid = args.get("account_id")
            if aid and not registry.get(aid):
                return {"ok": False, "error": "account_not_found"}
            return {"ok": True, "emails": registry.search(account_id=aid, query=args.get("query", ""))}

        if name == "email_read":
            account_id = args.get("account_id", "")
            mid = args.get("message_id", "")
            if not account_id:
                return {"ok": False, "error": "account_required"}
            if not registry.get(account_id):
                return {"ok": False, "error": "account_not_found"}
            if not mid:
                return {"ok": False, "error": "message_id_required"}
            m = registry.read(account_id, mid)
            if not m:
                return {"ok": False, "error": "message_not_found"}
            m = dict(m)
            m["account_id"] = account_id
            return {"ok": True, "message": m}

        if name == "email_draft_reply":
            account_id = args.get("account_id", "")
            mid = args.get("message_id", "")
            if not account_id:
                return {"ok": False, "error": "account_required"}
            if not registry.get(account_id):
                return {"ok": False, "error": "account_not_found"}
            if not mid:
                return {"ok": False, "error": "message_id_required"}
            h = registry.headers(account_id, mid)
            if not h or not h.get("from"):
                return {"ok": False, "error": "message_not_found"}
            to = h["from"]
            subject = h["subject"] if h["subject"].startswith("Re:") else ("Re: " + h["subject"])
            body = args.get("body", "")
            pending["draft"] = {"account_id": account_id, "message_id": mid,
                                "to": to, "subject": subject, "body": body}
            acct = registry.get(account_id)
            return {"ok": True, "account_id": account_id,
                    "account": acct.display_name if acct else account_id,
                    "draft": {"to": to, "subject": subject, "body": body},
                    "note": "اعرض المسودة واطلب تأكيداً صريحاً قبل الإرسال"}

        if name == "email_send":
            if not args.get("confirmed"):
                return {"ok": False, "error": "confirmation_required"}
            draft = pending.get("draft")
            if not draft:
                return {"ok": False, "error": "no_pending_draft"}
            requested = args.get("account_id")
            if requested and requested != draft["account_id"]:
                return {"ok": False, "error": "account_mismatch",
                        "draft_account": draft["account_id"],
                        "requested_account": requested}
            account_id = draft["account_id"]
            r = registry.send(account_id, draft["to"], draft["subject"], draft["body"])
            pending.pop("draft", None)
            return {"ok": True, "account_id": account_id, "sent_message_id": r.get("id")}

        return {"ok": False, "error": "unknown_tool"}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
